"""
Base Editable Table Component
A generic, reusable table component that handles common operations like add, delete, 
edit, confirm changes, highlighting, and server synchronization.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, 
    QTableWidgetItem, QComboBox, QHeaderView, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
import pandas as pd

from services.cached_sheets_service import CachedGoogleSheetsService


class ColumnConfig:
    """Configuration for a table column."""
    
    def __init__(self, 
                 header: str,
                 component_type: str = "text",
                 component_config: Optional[Dict[str, Any]] = None,
                 validation: Optional[Callable[[str], bool]] = None,
                 required: bool = False,
                 width: Optional[int] = None,
                 editable: bool = True,
                 default_value: Any = "",
                 options_source: Optional[str] = None,
                 options: Optional[List[str]] = None,
                 tooltip: Optional[str] = None,
                 resize_mode: str = "content"):
        """Initialize column configuration.
        
        Args:
            header: Column header text.
            component_type: Type of component ("text", "dropdown", "number", "date", "checkbox").
            component_config: Additional config for the component.
            validation: Validation function that takes string input and returns bool.
            required: Whether this field is required.
            width: Column width in pixels.
            editable: Whether this column can be edited.
            default_value: Default value for new rows.
            options_source: For dropdowns - method name to get options dynamically.
            options: For dropdowns - static list of options.
            tooltip: Tooltip text for the column.
            resize_mode: Column resize behavior ("content", "stretch", "fixed").
        """
        self.header = header
        self.component_type = component_type
        self.component_config = component_config or {}
        self.validation = validation
        self.required = required
        self.width = width
        self.editable = editable
        self.default_value = default_value
        self.options_source = options_source
        self.options = options or []
        self.tooltip = tooltip
        self.resize_mode = resize_mode


class BaseEditableTable(QWidget):
    """Base class for editable tables with common functionality."""
    
    # Signals
    data_changed = Signal()  # Emitted when data changes
    row_added = Signal(int)  # Emitted when row is added (row index)
    row_deleted = Signal(list)  # Emitted when rows are deleted (list of indices)
    
    def __init__(self, 
                 columns_config: List[ColumnConfig],
                 sheets_service: CachedGoogleSheetsService,
                 spreadsheet_id: str,
                 sheet_name: str,
                 title: str = "Data Table",
                 add_button_text: str = "➕ Add New Row"):
        """Initialize base editable table.
        
        Args:
            columns_config: List of column configurations.
            sheets_service: Service for Google Sheets operations.
            spreadsheet_id: Google Sheets spreadsheet ID.
            sheet_name: Name of the sheet.
            title: Title for the table group.
            add_button_text: Text for the add button.
        """
        super().__init__()
        
        # Core properties
        self.columns_config = columns_config
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.title = title
        self.add_button_text = add_button_text
        
        # State tracking
        self.current_data = []  # Current table data
        self.pending_changes_rows = set()  # Track rows with pending changes
        self.changed_cells = set()  # Track individual cells that have changed (row, col)
        self.original_values = {}  # Store original values for changed cells (row, col): value
        self.server_row_count = 0  # Track how many DATA rows came from server
        self._updating_highlights = False  # Flag to prevent recursion during highlighting
        
        # Create UI
        self.setup_ui()
        self.setup_table()
        self.load_data()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        if self.title:
            title_label = QLabel(self.title)
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)
        
        # Controls section
        controls_group = QGroupBox("Actions")
        controls_layout = QHBoxLayout()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Add button
        self.add_button = QPushButton(self.add_button_text)
        self.add_button.clicked.connect(self.add_new_row)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        controls_layout.addWidget(self.add_button)
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_button)
        
        # Confirm button (initially hidden)
        self.confirm_button = QPushButton("✅ Confirm Changes")
        self.confirm_button.clicked.connect(self.confirm_pending_changes)
        self.confirm_button.setVisible(False)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0056b3; }
        """)
        controls_layout.addWidget(self.confirm_button)
        
        # Delete button (initially hidden)
        self.delete_button = QPushButton("🗑️ Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.delete_button.setVisible(False)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c82333; }
        """)
        controls_layout.addWidget(self.delete_button)
        
        controls_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Table
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(False)  # Disabled to allow custom highlighting
        self.data_table.setSortingEnabled(False)  # Disable sorting to maintain data integrity
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.data_table)
    
    def setup_table(self):
        """Setup table structure based on column configuration."""
        # Set column count and headers
        self.data_table.setColumnCount(len(self.columns_config))
        headers = [col.header for col in self.columns_config]
        self.data_table.setHorizontalHeaderLabels(headers)
        
        # Configure column widths and resize behavior
        header = self.data_table.horizontalHeader()
        for i, col_config in enumerate(self.columns_config):
            if col_config.width:
                # Fixed width specified
                self.data_table.setColumnWidth(i, col_config.width)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            elif col_config.resize_mode == "stretch":
                # Stretch to fill available space
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            elif col_config.resize_mode == "content":
                # Auto-resize based on content
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            elif col_config.resize_mode == "interactive":
                # User can resize, but starts with content size
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            else:
                # Default to content-based sizing
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect signals
        self.data_table.itemChanged.connect(self.on_table_item_changed)
        self.data_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
    
    def create_cell_component(self, row: int, col: int, value: str = "") -> Union[QTableWidgetItem, QComboBox]:
        """Create appropriate component for a cell based on column configuration.
        
        Args:
            row: Row index.
            col: Column index.
            value: Initial value.
            
        Returns:
            Either a QTableWidgetItem or a widget component.
        """
        col_config = self.columns_config[col]
        
        if col_config.component_type == "dropdown":
            # Create dropdown
            combo = QComboBox()
            
            # Get options
            if col_config.options_source:
                # Get options from method
                options = getattr(self, col_config.options_source, lambda: [])()
            else:
                options = col_config.options
            
            combo.addItems(options)
            combo.setEditable(col_config.component_config.get("editable", True))
            combo.setCurrentText(value)
            
            # Connect signal
            combo.currentTextChanged.connect(
                lambda text, r=row, c=col: self.on_dropdown_changed(r, c, text)
            )
            
            # Set tooltip
            if col_config.tooltip:
                combo.setToolTip(col_config.tooltip)
            
            return combo
            
        elif col_config.component_type == "checkbox":
            # For checkboxes, we'll use a dropdown with Yes/No for simplicity
            combo = QComboBox()
            combo.addItems(["Yes", "No"])
            combo.setCurrentText(value if value in ["Yes", "No"] else "Yes")
            combo.currentTextChanged.connect(
                lambda text, r=row, c=col: self.on_dropdown_changed(r, c, text)
            )
            return combo
            
        else:  # text, number, date
            # Create table item
            item = QTableWidgetItem(value)
            
            # Set tooltip
            if col_config.tooltip:
                item.setToolTip(col_config.tooltip)
            
            # Make read-only if not editable
            if not col_config.editable:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            return item
    
    def add_new_row(self):
        """Add a new row to the table."""
        if not self.validate_before_add():
            return
            
        try:
            # Temporarily disconnect signals
            self.data_table.itemChanged.disconnect()
            
            # Get current date for default values
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Add new row
            new_row_index = self.data_table.rowCount()
            self.data_table.insertRow(new_row_index)
            
            # Create components for each column
            for col, col_config in enumerate(self.columns_config):
                # Get default value
                default_val = col_config.default_value
                if col_config.component_type == "date" and not default_val:
                    default_val = current_date
                
                # Create component
                component = self.create_cell_component(new_row_index, col, str(default_val))
                
                if isinstance(component, QComboBox):
                    self.data_table.setCellWidget(new_row_index, col, component)
                else:
                    self.data_table.setItem(new_row_index, col, component)
                
                # Store original value
                self.original_values[(new_row_index, col)] = str(default_val)
            
            # Mark this row as having pending changes
            self.pending_changes_rows.add(new_row_index)
            
            # Reconnect signals
            self.data_table.itemChanged.connect(self.on_table_item_changed)
            
            # Focus on first editable cell
            first_editable = self.get_first_editable_column()
            if first_editable >= 0:
                self.data_table.setCurrentCell(new_row_index, first_editable)
                if not isinstance(self.data_table.cellWidget(new_row_index, first_editable), QComboBox):
                    self.data_table.editItem(self.data_table.item(new_row_index, first_editable))
            
            # Update button visibility
            self.update_confirm_button_visibility()
            
            # Emit signal
            self.row_added.emit(new_row_index)
            
        except Exception as e:
            self.status_label.setText(f"❌ Error adding row: {str(e)}")
            # Reconnect signal in case of error
            if not self.data_table.receivers(self.data_table.itemChanged):
                self.data_table.itemChanged.connect(self.on_table_item_changed)
    
    def get_first_editable_column(self) -> int:
        """Get the index of the first editable column."""
        for i, col_config in enumerate(self.columns_config):
            if col_config.editable:
                return i
        return -1
    
    def validate_before_add(self) -> bool:
        """Validate conditions before adding a new row. Override in subclasses."""
        return True
    
    def is_new_row(self, row: int) -> bool:
        """Check if a row is a new row that hasn't been saved to the server yet."""
        return row >= self.server_row_count
    
    def delete_selected_rows(self):
        """Delete selected rows after confirmation."""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        # Get descriptions for confirmation
        descriptions = []
        for row in list(selected_rows)[:5]:  # Show first 5
            if self.data_table.item(row, 0):
                desc = self.data_table.item(row, 0).text()[:30]
                descriptions.append(f"Row {row + 1}: {desc}...")
        
        if len(selected_rows) > 5:
            descriptions.append(f"... and {len(selected_rows) - 5} more")
        
        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete {len(selected_rows)} row(s)?\n\n" + "\n".join(descriptions),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Perform deletion
        self._delete_rows_internal(selected_rows)
    
    def _delete_rows_internal(self, selected_rows: set):
        """Internal method to delete rows."""
        self.status_label.setText("🗑️ Deleting rows...")
        success_count = 0
        error_count = 0
        
        # Separate new rows from existing rows
        new_rows = []
        existing_rows = []
        
        for row in selected_rows:
            if self.is_new_row(row):
                new_rows.append(row)
            else:
                existing_rows.append(row)
        
        # Delete new rows locally
        for row in sorted(new_rows, reverse=True):
            try:
                self.data_table.removeRow(row)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error removing local row {row}: {e}")
        
        # Delete existing rows from server
        if existing_rows:
            try:
                # Convert to sheet row numbers (add 2 for 0-based + header)
                sheet_row_numbers = [row + 2 for row in existing_rows]
                
                success = self.sheets_service.delete_multiple_rows(
                    self.spreadsheet_id, self.sheet_name, sheet_row_numbers
                )
                
                if success:
                    success_count += len(existing_rows)
                    self.server_row_count -= len(existing_rows)
                else:
                    error_count += len(existing_rows)
                    
            except Exception as e:
                error_count += len(existing_rows)
                print(f"Error deleting server rows: {e}")
        
        # Update status
        row_text = "row" if success_count == 1 else "rows"
        if error_count == 0:
            self.status_label.setText(f"✅ Successfully deleted {success_count} {row_text}")
        else:
            self.status_label.setText(f"⚠️ Deleted {success_count}, failed {error_count}. Check connection.")
        
        # Refresh data to sync with server
        QTimer.singleShot(1000, self.refresh_data)
        
        # Update button visibility
        self.delete_button.setVisible(False)
        self.update_confirm_button_visibility()
        
        # Emit signal
        self.row_deleted.emit(list(selected_rows))
    
    def load_data(self):
        """Load data from the sheet."""
        # This method should be implemented by subclasses
        # For now, try a generic implementation
        try:
            print(f"🔄 Loading data for {self.sheet_name}...")
            df = self.get_data_from_service()
            if not df.empty:
                self.populate_table_with_data(df)
                print(f"✅ Loaded {len(df)} rows")
            else:
                print("📝 No data found")
                self.data_table.setRowCount(0)
        except Exception as e:
            print(f"❌ Error in generic load_data: {e}")
            # Subclasses should implement their own load_data method
    
    def refresh_data(self):
        """Refresh data from the server."""
        self.status_label.setText("🔄 Refreshing data...")
        self.load_data()
    
    def populate_table_with_data(self, df):
        """Populate table with DataFrame data."""
        try:
            print(f"🔄 Populating table with {len(df)} rows...")
            
            # Clear pending changes when loading fresh data
            self.pending_changes_rows.clear()
            self.changed_cells.clear()
            
            # Set table size
            self.data_table.setRowCount(len(df))
            
            # Get dynamic options for dropdowns
            categories = self.get_categories() if hasattr(self, 'get_categories') else []
            accounts = self.get_accounts() if hasattr(self, 'get_accounts') else []
            
            # Populate rows
            for row in range(len(df)):
                for col in range(min(len(df.columns), len(self.columns_config))):
                    value = str(df.iloc[row, col]) if pd.notna(df.iloc[row, col]) else ""
                    
                    # Create component for this cell
                    component = self.create_cell_component(row, col, value)
                    
                    # For dropdowns, populate options
                    col_config = self.columns_config[col]
                    if col_config.component_type == "dropdown" and hasattr(component, 'addItems'):
                        # Clear and add options
                        component.clear()
                        
                        # Get options from config or dynamic source
                        if col_config.options_source == "get_categories" and categories:
                            component.addItems(categories)
                        elif col_config.options_source == "get_accounts" and accounts:
                            component.addItems(accounts)
                        elif col_config.options:
                            component.addItems(col_config.options)
                        
                        # Set current value
                        component.setCurrentText(value)
                    
                    # Set component in table
                    if hasattr(component, 'currentText'):  # It's a widget
                        self.data_table.setCellWidget(row, col, component)
                    else:  # It's a table item
                        self.data_table.setItem(row, col, component)
            
            # Clear any highlighting from previous loads
            self.clear_all_highlighting()
            
            # Update button visibility
            self.update_button_visibility()
            
            print(f"✅ Table populated successfully with {len(df)} rows")
            
        except Exception as e:
            print(f"❌ Error populating table: {e}")
            raise
    
    # ... (continuing in next part due to length)
    
    def get_accounts(self) -> List[str]:
        """Get account names for dropdowns. Override in subclasses if needed."""
        try:
            return self.sheets_service.get_accounts(self.spreadsheet_id)
        except:
            return ["Cash"]
    
    def get_categories(self) -> List[str]:
        """Get categories for dropdowns. Override in subclasses if needed."""
        try:
            df = self.sheets_service.get_data_as_dataframe(self.spreadsheet_id, "'Categories'!A:B")
            if not df.empty and len(df.columns) > 0:
                # Get category names from the first column
                category_names = df.iloc[:, 0].dropna().astype(str).tolist()
                return [name for name in category_names if name.strip()]
        except:
            pass
        return ["Food", "Transportation", "Entertainment", "Other"]
    
    def update_button_visibility(self):
        """Update visibility of action buttons based on state."""
        has_changes = len(self.pending_changes_rows) > 0
        has_selection = len(self.data_table.selectionModel().selectedRows()) > 0
        
        # Show confirm button if there are pending changes
        self.confirm_button.setVisible(has_changes)
        
        # Show delete button if there's a selection
        self.delete_button.setVisible(has_selection)
        
        # Update confirm button text to show number of changes
        if has_changes:
            change_count = len(self.pending_changes_rows)
            self.confirm_button.setText(f"✅ Confirm Changes ({change_count})")
        else:
            self.confirm_button.setText("✅ Confirm Changes")
    
    def on_table_item_changed(self, item):
        """Handle table item changes."""
        if self._updating_highlights:
            return
            
        row = item.row()
        col = item.column()
        
        # Validate the change
        if not self.validate_cell_change(row, col, item.text()):
            return
        
        # Check if value actually changed
        if self.check_cell_changed(row, col):
            self.changed_cells.add((row, col))
            self.highlight_changed_cell(row, col)
            self.pending_changes_rows.add(row)
        else:
            # Value reverted to original
            self.changed_cells.discard((row, col))
            self.clear_cell_highlighting(row, col)
            
            # Check if row still has changes
            row_has_changes = any((row, c) in self.changed_cells for c in range(len(self.columns_config)))
            if not row_has_changes:
                self.pending_changes_rows.discard(row)
        
        self.update_confirm_button_visibility()
    
    def on_dropdown_changed(self, row: int, col: int, text: str):
        """Handle dropdown changes."""
        if self._updating_highlights:
            return
        
        # Same logic as table item changed
        if self.validate_cell_change(row, col, text):
            if self.check_cell_changed(row, col):
                self.changed_cells.add((row, col))
                self.highlight_changed_cell(row, col)
                self.pending_changes_rows.add(row)
            else:
                self.changed_cells.discard((row, col))
                self.clear_cell_highlighting(row, col)
                
                row_has_changes = any((row, c) in self.changed_cells for c in range(len(self.columns_config)))
                if not row_has_changes:
                    self.pending_changes_rows.discard(row)
            
            self.update_confirm_button_visibility()
    
    def validate_cell_change(self, row: int, col: int, value: str) -> bool:
        """Validate a cell change. Override in subclasses for custom validation."""
        col_config = self.columns_config[col]
        
        # Check required fields
        if col_config.required and not value.strip():
            self.status_label.setText(f"❌ {col_config.header} cannot be empty")
            return False
        
        # Custom validation
        if col_config.validation and not col_config.validation(value):
            self.status_label.setText(f"❌ Invalid value for {col_config.header}")
            return False
        
        return True
    
    def check_cell_changed(self, row: int, col: int) -> bool:
        """Check if a cell's value has changed from its original value."""
        original_value = self.original_values.get((row, col), "")
        current_value = self.get_cell_value(row, col)
        return current_value != original_value
    
    def get_cell_value(self, row: int, col: int) -> str:
        """Get the current value of a cell."""
        widget = self.data_table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        else:
            item = self.data_table.item(row, col)
            return item.text() if item else ""
    
    def highlight_changed_cell(self, row: int, col: int):
        """Apply highlighting to a changed cell."""
        self._updating_highlights = True
        try:
            widget = self.data_table.cellWidget(row, col)
            if isinstance(widget, QComboBox):
                # Style dropdown
                widget.setStyleSheet("""
                    QComboBox {
                        background-color: #ffeb82;
                        border: 1px solid #ffeaa7;
                        border-radius: 3px;
                        padding: 2px;
                    }
                    QComboBox:hover {
                        background-color: #ffe066;
                    }
                """)
            else:
                # Style table item
                item = self.data_table.item(row, col)
                if item:
                    yellow_color = QColor(255, 235, 130)
                    item.setBackground(yellow_color)
                    item.setData(Qt.ItemDataRole.BackgroundRole, yellow_color)
        finally:
            self._updating_highlights = False
    
    def clear_cell_highlighting(self, row: int, col: int):
        """Clear highlighting from a specific cell."""
        self._updating_highlights = True
        try:
            widget = self.data_table.cellWidget(row, col)
            if isinstance(widget, QComboBox):
                widget.setStyleSheet("")
            else:
                item = self.data_table.item(row, col)
                if item:
                    item.setBackground(QColor())
                    item.setData(Qt.ItemDataRole.BackgroundRole, QColor())
        finally:
            self._updating_highlights = False
    
    def on_selection_changed(self):
        """Handle table selection changes."""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if selected_rows:
            count = len(selected_rows)
            row_text = "row" if count == 1 else "rows"
            self.delete_button.setText(f"🗑️ Delete {count} {row_text}")
            self.delete_button.setVisible(True)
        else:
            self.delete_button.setVisible(False)
    
    def update_confirm_button_visibility(self):
        """Update confirm button visibility based on pending changes."""
        if self.pending_changes_rows:
            count = len(self.pending_changes_rows)
            row_text = "row" if count == 1 else "rows"
            self.confirm_button.setText(f"✅ Confirm Changes ({count} {row_text})")
            self.confirm_button.setVisible(True)
        else:
            self.confirm_button.setVisible(False)
    
    def confirm_pending_changes(self):
        """Confirm and save all pending changes."""
        if not self.pending_changes_rows:
            return
        
        self.status_label.setText("💾 Saving changes...")
        self.confirm_button.setEnabled(False)
        
        try:
            # Implement save logic - to be overridden by subclasses
            success = self.save_changes_to_server()
            
            if success:
                # Clear all tracking data
                self.pending_changes_rows.clear()
                self.changed_cells.clear()
                
                # Clear highlighting
                self.clear_all_highlighting()
                
                # Update original values
                self.store_original_values()
                
                # Update server row count
                self.server_row_count = self.data_table.rowCount()
                
                self.status_label.setText("✅ Changes saved successfully")
                QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))
            else:
                self.status_label.setText("❌ Failed to save changes")
                
        except Exception as e:
            self.status_label.setText(f"❌ Error saving: {str(e)}")
        
        self.confirm_button.setEnabled(True)
        self.update_confirm_button_visibility()
    
    def save_changes_to_server(self) -> bool:
        """Save changes to server. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement save_changes_to_server")
    
    def clear_all_highlighting(self):
        """Clear all cell highlighting."""
        self._updating_highlights = True
        try:
            for row in range(self.data_table.rowCount()):
                for col in range(len(self.columns_config)):
                    self.clear_cell_highlighting(row, col)
        finally:
            self._updating_highlights = False
    
    def store_original_values(self):
        """Store current values as original values."""
        self.original_values.clear()
        for row in range(self.data_table.rowCount()):
            for col in range(len(self.columns_config)):
                self.original_values[(row, col)] = self.get_cell_value(row, col)
