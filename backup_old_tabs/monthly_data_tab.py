"""
Monthly Data Tab
Tab for managing monthly expense data with year/month dropdowns and table.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from datetime import datetime
import calendar
import pandas as pd

from services.google_sheets import GoogleSheetsService


class MonthlyDataTab(QWidget):
    """Monthly data tab with year/month dropdowns and table."""
    
    def __init__(self, sheets_service: GoogleSheetsService, spreadsheet_id: str):
        super().__init__()
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.current_sheet_name = ""
        self.pending_changes_rows = set()  # Track rows with pending changes
        self.changed_cells = set()  # Track individual cells that have changed (row, col)
        self.original_values = {}  # Store original values for changed cells (row, col): value
        self.payment_methods = []  # Cache for payment methods
        self._updating_highlights = False  # Flag to prevent recursion during highlighting
        self.server_row_count = 0  # Track how many DATA rows came from server (excludes headers, for new row detection)
        self.setup_ui()
        self.setup_default_values()
    
    def setup_ui(self):
        """Setup the monthly data tab UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("📅 Monthly Data")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Controls section
        controls_group = QGroupBox("Select Month")
        controls_layout = QHBoxLayout()
        controls_group.setLayout(controls_layout)
        
        # Year dropdown
        controls_layout.addWidget(QLabel("Year:"))
        self.year_combo = QComboBox()
        current_year = datetime.now().year
        years = [str(year) for year in range(current_year - 5, current_year + 2)]
        self.year_combo.addItems(years)
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentTextChanged.connect(self.on_date_changed)
        controls_layout.addWidget(self.year_combo)
        
        # Month dropdown
        controls_layout.addWidget(QLabel("Month:"))
        self.month_combo = QComboBox()
        months = [calendar.month_name[i] for i in range(1, 13)]
        self.month_combo.addItems(months)
        current_month = datetime.now().month
        self.month_combo.setCurrentText(calendar.month_name[current_month])
        self.month_combo.currentTextChanged.connect(self.on_date_changed)
        controls_layout.addWidget(self.month_combo)
        
        # Status label
        self.sheet_status_label = QLabel("Ready")
        self.sheet_status_label.setStyleSheet("color: #666; font-style: italic;")
        controls_layout.addWidget(self.sheet_status_label)
        
        # Add stretch
        controls_layout.addStretch()
        
        layout.addWidget(controls_group)
        
        # Table controls
        table_controls_layout = QHBoxLayout()
        
        self.add_row_button = QPushButton("➕ Add New Expense")
        self.add_row_button.clicked.connect(self.add_new_expense_row)
        self.add_row_button.setStyleSheet("""
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
        table_controls_layout.addWidget(self.add_row_button)
        
        self.refresh_button = QPushButton("🔄 Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_current_sheet)
        table_controls_layout.addWidget(self.refresh_button)
        
        self.confirm_button = QPushButton("✅ Confirm Changes")
        self.confirm_button.clicked.connect(self.confirm_pending_changes)
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
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.confirm_button.setVisible(False)  # Hidden by default
        table_controls_layout.addWidget(self.confirm_button)
        
        self.delete_button = QPushButton("🗑️ Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_expenses)
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
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.delete_button.setVisible(False)  # Hidden by default
        table_controls_layout.addWidget(self.delete_button)
        
        table_controls_layout.addStretch()
        layout.addLayout(table_controls_layout)
        
        # Table
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(False)  # Disabled to allow custom highlighting
        self.data_table.setSortingEnabled(False)  # Disable sorting to maintain data integrity
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Connect to signals for real-time updates
        self.data_table.itemChanged.connect(self.on_table_item_changed)
        
        # Connect to selection changed signal for delete button visibility
        self.data_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        layout.addWidget(self.data_table)
        
        # Initialize with placeholder
        self.show_placeholder_table()
    
    def setup_default_values(self):
        """Setup default month/year and check for existing sheet."""
        self.on_date_changed()
    
    def show_placeholder_table(self):
        """Show placeholder content in the table."""
        self.data_table.setRowCount(3)
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["Date", "Description", "Amount", "Category"])
        
        # Add placeholder rows
        placeholder_data = [
            ["Select month", "to load data", "from Google", "Sheets"],
            ["", "", "", ""],
            ["🔄", "Choose year and month", "above to get started", "📊"]
        ]
        
        for row, row_data in enumerate(placeholder_data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if row == 0:
                    item.setBackground(QColor(220, 220, 220))  # Light gray color
                self.data_table.setItem(row, col, item)
        
        # Auto-resize columns
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    def get_sheet_name(self) -> str:
        """Get the sheet name based on current month/year selection."""
        month = self.month_combo.currentText()
        year = self.year_combo.currentText()
        return f"{month} {year}"
    
    def on_date_changed(self):
        """Handle year/month dropdown changes."""
        sheet_name = self.get_sheet_name()
        self.current_sheet_name = sheet_name
        
        self.sheet_status_label.setText(f"📋 Current sheet: {sheet_name}")
        
        # Check if sheet exists
        self.check_and_create_sheet(sheet_name)
    
    def check_and_create_sheet(self, sheet_name: str):
        """Check if sheet exists, create if it doesn't."""
        try:
            # Get list of existing sheets
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if sheet_name in existing_sheets:
                self.sheet_status_label.setText(f"✅ Sheet '{sheet_name}' found")
                self.load_sheet_data(sheet_name)
            else:
                self.sheet_status_label.setText(f"🔄 Creating new sheet '{sheet_name}'...")
                self.create_new_sheet(sheet_name)
                
        except Exception as e:
            self.sheet_status_label.setText(f"❌ Error: {str(e)}")
            self.show_placeholder_table()
    
    def create_new_sheet(self, sheet_name: str):
        """Create a new expense sheet with default headers."""
        try:
            # Create the new sheet with default expense headers
            success = self.sheets_service.create_expense_sheet(
                self.spreadsheet_id, sheet_name
            )
            
            if success:
                self.sheet_status_label.setText(f"✅ Created new sheet '{sheet_name}'")
                # Load the newly created sheet (will show headers only)
                self.load_sheet_data(sheet_name)
            else:
                self.sheet_status_label.setText(f"❌ Failed to create sheet '{sheet_name}'")
                self.show_empty_table_for_new_sheet()
                
        except Exception as e:
            self.sheet_status_label.setText(f"❌ Error creating sheet: {str(e)}")
            self.show_empty_table_for_new_sheet()
    
    def load_sheet_data(self, sheet_name: str):
        """Load data from the specified sheet."""
        try:
            # Try to load data from the sheet
            range_name = f"'{sheet_name}'!A:Z"  # Use quotes for sheet names with spaces
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name
            )
            
            if df.empty:
                self.show_empty_table_for_new_sheet()
                self.sheet_status_label.setText(f"📄 Sheet '{sheet_name}' is empty")
                return
            
            # Populate table with data
            self.populate_table_with_data(df)
            
            # Show cache status along with row count
            cache_indicator = self._get_cache_status_indicator(sheet_name)
            self.sheet_status_label.setText(f"✅ Loaded {len(df)} rows from '{sheet_name}' {cache_indicator}")
            
        except Exception as e:
            self.sheet_status_label.setText(f"❌ Error loading sheet: {str(e)}")
            self.show_empty_table_for_new_sheet()
    
    def populate_table_with_data(self, df):
        """Populate the table with DataFrame data."""
        # Load payment methods first
        self.load_payment_methods()
        
        # Temporarily disconnect the signal to avoid triggering updates during population
        self.data_table.itemChanged.disconnect()
        
        # Update server row count - this is how many DATA rows exist on the server
        # (headers are excluded since get_data_as_dataframe uses has_header=True by default)
        self.server_row_count = len(df)
        
        self.data_table.setRowCount(len(df))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(list(df.columns))
        
        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = str(df.iloc[row, col]) if df.iloc[row, col] is not None else ""
                
                # Special handling for Payment Method column (column 4)
                if col == 4:  # Payment Method column
                    payment_combo = QComboBox()
                    payment_combo.addItems(self.payment_methods)
                    payment_combo.setEditable(True)  # Allow custom entries
                    payment_combo.setCurrentText(value)
                    payment_combo.currentTextChanged.connect(
                        lambda text, r=row: self.on_payment_method_changed(r, text)
                    )
                    self.data_table.setCellWidget(row, col, payment_combo)
                else:
                    # Regular text item for other columns
                    item = QTableWidgetItem(value)
                    # Make cells editable with helpful tooltips
                    item.setToolTip(f"Click to edit {list(df.columns)[col].lower()}")
                    self.data_table.setItem(row, col, item)
        
        # Clear pending changes (these are from server data)
        self.pending_changes_rows.clear()
        
        # Clear cell highlighting and store original values
        self.clear_cell_highlighting()
        self.store_original_values()
        
        # Update confirm button visibility
        self.update_confirm_button_visibility()
        
        # Reconnect the signal
        self.data_table.itemChanged.connect(self.on_table_item_changed)
        
        # Configure column resize behavior - expand from left to right
        header = self.data_table.horizontalHeader()
        # Set different resize modes for each column to expand left to right
        if self.data_table.columnCount() >= 6:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date - fit content
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Description - expand
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Amount - fit content
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Category - expand
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Payment Method - fit content
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Notes - expand
    
    def show_empty_table_for_new_sheet(self):
        """Show an empty table template for a new sheet."""
        # Load payment methods first
        self.load_payment_methods()
        
        # Temporarily disconnect the signal
        self.data_table.itemChanged.disconnect()
        
        # New sheet has 0 rows from server
        self.server_row_count = 0
        
        # Set up typical expense tracking columns (matching the service default headers)
        self.data_table.setRowCount(0)  # Start with no rows - user can add them
        self.data_table.setColumnCount(6)
        self.data_table.setHorizontalHeaderLabels([
            "Date", "Description", "Amount", "Category", "Payment Method", "Notes"
        ])
        
        # Clear pending changes
        self.pending_changes_rows.clear()
        
        # Clear cell highlighting and original values
        self.clear_cell_highlighting()
        self.original_values.clear()
        
        # Update confirm button visibility
        self.update_confirm_button_visibility()
        
        # Reconnect the signal
        self.data_table.itemChanged.connect(self.on_table_item_changed)
        
        # Configure column resize behavior - expand from left to right
        header = self.data_table.horizontalHeader()
        # Set different resize modes for each column to expand left to right
        if self.data_table.columnCount() >= 6:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date - fit content
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          # Description - expand
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Amount - fit content
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Category - expand
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Payment Method - fit content
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Notes - expand
    
    def load_payment_methods(self):
        """Load payment methods from Google Sheets for dropdown."""
        try:
            self.payment_methods = self.sheets_service.get_payment_methods(self.spreadsheet_id)
            if not self.payment_methods:
                # If no payment methods found, provide defaults
                self.payment_methods = ["Cash", "Credit Card", "Debit Card", "Bank Transfer"]
        except Exception as e:
            print(f"Error loading payment methods: {e}")
            # Fallback to defaults
            self.payment_methods = ["Cash", "Credit Card", "Debit Card", "Bank Transfer"]
    
    def update_confirm_button_visibility(self):
        """Show/hide confirm button based on pending changes."""
        if self.pending_changes_rows:
            self.confirm_button.setVisible(True)
            count = len(self.pending_changes_rows)
            row_text = "row" if count == 1 else "rows"
            self.confirm_button.setText(f"✅ Confirm Changes ({count} {row_text})")
            self.sheet_status_label.setText(f"⏳ {count} {row_text} with pending changes. Click Confirm to save.")
        else:
            self.confirm_button.setVisible(False)
            # Only set to "Ready" if status isn't showing a recent success/error message
            if (hasattr(self, 'current_sheet_name') and self.current_sheet_name and 
                not self.sheet_status_label.text().startswith("✅") and 
                not self.sheet_status_label.text().startswith("⚠️")):
                self.sheet_status_label.setText("Ready")
    
    def store_original_values(self):
        """Store original values for change tracking."""
        self.original_values.clear()
        for row in range(self.data_table.rowCount()):
            for col in range(self.data_table.columnCount()):
                if col == 4:  # Payment Method column - get from dropdown
                    widget = self.data_table.cellWidget(row, col)
                    if isinstance(widget, QComboBox):
                        value = widget.currentText()
                    else:
                        value = ""
                else:
                    # Regular text item
                    item = self.data_table.item(row, col)
                    value = item.text() if item else ""
                
                self.original_values[(row, col)] = value
    
    def highlight_changed_cell(self, row: int, col: int):
        """Apply eye-friendly highlighting to a changed cell."""
        # Prevent recursion during highlight updates
        self._updating_highlights = True
        try:
            if col == 4:  # Payment Method column - dropdown widget
                widget = self.data_table.cellWidget(row, col)
                if isinstance(widget, QComboBox):
                    # Apply yellow background color to dropdown to match other cells
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
                        QComboBox:drop-down {
                            background-color: #ffeb82;
                        }
                    """)
            else:
                # Regular text item
                item = self.data_table.item(row, col)
                if item:
                    print(f"Setting background color for item {item.text()} in row {row} and column {col}")
                    # Try multiple approaches to ensure background sticks
                    yellow_color = QColor(255, 235, 130)  # More visible yellow
                    
                    # Method 1: Standard setBackground
                    item.setBackground(yellow_color)
                    
                    # Method 2: Via data role
                    item.setData(Qt.ItemDataRole.BackgroundRole, yellow_color)
                    
                    # Method 3: Force refresh the item
                    self.data_table.update(self.data_table.indexFromItem(item))
                    
                    # Method 4: Set a custom property for identification
                    item.setData(Qt.ItemDataRole.UserRole, "changed_cell")
                    
                    print(f"Background color set for item {item.text()} in row {row} and column {col}")
                    print(f"Item background after setting: {item.background().color().name()}")
        finally:
            self._updating_highlights = False
    
    def clear_cell_highlighting(self):
        """Clear highlighting from all cells."""
        # Prevent recursion during highlight clearing
        self._updating_highlights = True
        try:
            self.changed_cells.clear()
            
            for row in range(self.data_table.rowCount()):
                for col in range(self.data_table.columnCount()):
                    if col == 4:  # Payment Method column - dropdown widget
                        widget = self.data_table.cellWidget(row, col)
                        if isinstance(widget, QComboBox):
                            # Clear custom stylesheet
                            widget.setStyleSheet("")
                    else:
                        # Regular text item
                        item = self.data_table.item(row, col)
                        if item:
                            # Clear background color using both methods
                            item.setBackground(QColor())
                            item.setData(Qt.ItemDataRole.BackgroundRole, QColor())
        finally:
            self._updating_highlights = False
    
    def check_cell_changed(self, row: int, col: int) -> bool:
        """Check if a cell's value has changed from its original value."""
        original_value = self.original_values.get((row, col), "")
        
        if col == 4:  # Payment Method column - get from dropdown
            widget = self.data_table.cellWidget(row, col)
            current_value = widget.currentText() if isinstance(widget, QComboBox) else ""
        else:
            # Regular text item
            item = self.data_table.item(row, col)
            current_value = item.text() if item else ""
        
        return current_value != original_value
    
    def is_new_row(self, row: int) -> bool:
        """Check if a row is a new row that hasn't been saved to the server yet.
        
        Args:
            row: The row index to check (0-based, data rows only).
            
        Returns:
            True if the row is new (added locally), False if it exists on the server.
        """
        # A row is "new" if its index is >= the number of data rows that came from the server
        # Note: server_row_count excludes header rows since we use has_header=True
        # Qt table rows are 0-indexed and contain only data (headers are separate)
        return row >= self.server_row_count
    
    def on_table_item_changed(self, item):
        """Handle table item changes and track for confirmation."""
        if not self.current_sheet_name or self._updating_highlights:
            return  # Skip if no sheet or we're updating highlights to prevent recursion
        
        row = item.row()
        column = item.column()
        new_value = item.text()
        
        # Skip Payment Method column (handled by dropdown)
        if column == 4:  # Payment Method column
            return
        
        # Basic validation for required fields
        if column == 0 and not new_value.strip():  # Date column
            self.sheet_status_label.setText("❌ Date cannot be empty")
            return
        
        if column == 1 and not new_value.strip():  # Description column  
            self.sheet_status_label.setText("❌ Description cannot be empty")
            return
        
        # Check if cell value actually changed from original
        if self.check_cell_changed(row, column):
            # Track the changed cell
            self.changed_cells.add((row, column))
            # Apply highlighting to the changed cell
            self.highlight_changed_cell(row, column)
            # Mark this row as having pending changes
            self.pending_changes_rows.add(row)
        else:
            # Cell was reverted to original value
            self.changed_cells.discard((row, column))
            # Clear highlighting (prevent recursion)
            self._updating_highlights = True
            try:
                item.setBackground(QColor())  # Clear background for regular items
                item.setData(Qt.ItemDataRole.BackgroundRole, QColor())  # Clear data role too
            finally:
                self._updating_highlights = False
            # Check if row still has other changes
            row_has_changes = any((row, col) in self.changed_cells for col in range(self.data_table.columnCount()))
            if not row_has_changes:
                self.pending_changes_rows.discard(row)
        
        # Update confirm button visibility
        self.update_confirm_button_visibility()
    
    def confirm_pending_changes(self):
        """Confirm and save all pending changes to the server in a single batch operation."""
        if not self.pending_changes_rows:
            return
        
        self.sheet_status_label.setText("💾 Saving changes to Google Sheets...")
        self.confirm_button.setEnabled(False)  # Disable during save
        
        try:
            # Store count before clearing for reporting
            changes_count = len(self.pending_changes_rows)
            
            # Batch all changes into a single update
            success = self.save_all_pending_changes_batch()
            
            if success:
                success_count = changes_count
                error_count = 0
            else:
                success_count = 0
                error_count = changes_count
                
        except Exception as e:
            print(f"Error saving batch changes: {e}")
            success_count = 0
            error_count = len(self.pending_changes_rows)
        
        # Update UI based on results
        self.confirm_button.setEnabled(True)
        
        if error_count == 0:
            # Complete success - clear everything IMMEDIATELY
            
            # CRITICAL: Disconnect signals to prevent re-triggering during cleanup
            self.data_table.itemChanged.disconnect()
            
            # Update server row count - all current DATA rows are now saved to server
            # (Qt table rowCount() only counts data rows, headers are separate)
            self.server_row_count = self.data_table.rowCount()
            
            # Clear all tracking data in one go
            self.pending_changes_rows.clear()
            self.changed_cells.clear()
            
            # Clear visual highlighting (prevent recursion)
            self._updating_highlights = True
            try:
                for row in range(self.data_table.rowCount()):
                    for col in range(self.data_table.columnCount()):
                        if col == 4:  # Payment Method column - dropdown widget
                            widget = self.data_table.cellWidget(row, col)
                            if isinstance(widget, QComboBox):
                                widget.setStyleSheet("")
                        else:
                            # Regular text item
                            item = self.data_table.item(row, col)
                            if item:
                                item.setBackground(QColor())
                                item.setData(Qt.ItemDataRole.BackgroundRole, QColor())
            finally:
                self._updating_highlights = False
            
            # Store new values as original values (refresh baseline) WITHOUT triggering signals
            self.original_values.clear()
            for row in range(self.data_table.rowCount()):
                for col in range(self.data_table.columnCount()):
                    if col == 4:  # Payment Method column - get from dropdown
                        widget = self.data_table.cellWidget(row, col)
                        if isinstance(widget, QComboBox):
                            value = widget.currentText()
                        else:
                            value = ""
                    else:
                        # Regular text item
                        item = self.data_table.item(row, col)
                        value = item.text() if item else ""
                    
                    self.original_values[(row, col)] = value
            
            # CRITICAL: Reconnect signals AFTER all cleanup is done
            self.data_table.itemChanged.connect(self.on_table_item_changed)
            
            # Update button visibility AFTER all cleanup is done
            self.update_confirm_button_visibility()
            
            # Set success message
            self.sheet_status_label.setText(f"✅ Successfully saved {success_count} changes")
            QTimer.singleShot(3000, lambda: self.sheet_status_label.setText("Ready"))
            
            return  # Early return to avoid running cleanup logic again
            
        else:
            self.sheet_status_label.setText(f"⚠️ Saved {success_count}, failed {error_count}. Try again for failed rows.")
            
            # For partial failures, only clear highlighting for successfully saved rows
            # The pending_changes_rows and changed_cells for failed rows are preserved
            successfully_saved_cells = set()
            for row in range(self.data_table.rowCount()):
                if row not in self.pending_changes_rows:  # Row was successfully saved
                    for col in range(self.data_table.columnCount()):
                        successfully_saved_cells.add((row, col))
            
            # Clear highlighting only for successfully saved cells (prevent recursion)
            self._updating_highlights = True
            try:
                for row, col in successfully_saved_cells:
                    if col == 4:  # Payment Method column - dropdown widget
                        widget = self.data_table.cellWidget(row, col)
                        if isinstance(widget, QComboBox):
                            widget.setStyleSheet("")
                    else:
                        # Regular text item
                        item = self.data_table.item(row, col)
                        if item:
                            # TODO: This is currently not working but it's not critical
                            item.setBackground(QColor())
                            item.setData(Qt.ItemDataRole.BackgroundRole, QColor())
                    
                    # Remove from changed_cells if it was there
                    self.changed_cells.discard((row, col))
            finally:
                self._updating_highlights = False
            
            # Update original values for successfully saved rows
            self.store_original_values()
            
            # Update confirm button visibility for partial failures
            self.update_confirm_button_visibility()
    
    def save_all_pending_changes_batch(self) -> bool:
        """Save all pending changes in a single batch operation."""
        try:
            # Get current server data to determine which rows are new
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.current_sheet_name}'!A:Z"
            )
            # server_row_count = number of data rows on server (excluding header row)
            server_row_count = len(df)
            
            # Collect all changes into batch updates
            batch_updates = []
            
            for row in sorted(self.pending_changes_rows):
                # Collect row data
                row_data = []
                for col in range(self.data_table.columnCount()):
                    if col == 4:  # Payment Method column - get from dropdown
                        widget = self.data_table.cellWidget(row, col)
                        if isinstance(widget, QComboBox):
                            value = widget.currentText().strip()
                        else:
                            value = ""
                    else:
                        # Regular text item
                        item = self.data_table.item(row, col)
                        value = item.text().strip() if item else ""
                    
                    row_data.append(value)
                
                # Validate required fields
                if not row_data[0].strip() or not row_data[1].strip():  # Date and Description
                    print(f"Skipping row {row}: missing required fields")
                    continue
                
                # Determine target row in sheet
                if row >= server_row_count:  # New row
                    target_row = server_row_count + 2 + (row - server_row_count)  # +2 for header
                else:  # Existing row
                    target_row = row + 2  # +2 for header
                
                batch_updates.append({
                    'range': f"A{target_row}:F{target_row}",  # Assuming 6 columns (A-F)
                    'values': [row_data]
                })
            
            if not batch_updates:
                return False
            
            # Make single batch update
            return self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id,
                self.current_sheet_name,
                batch_updates
            )
            
        except Exception as e:
            print(f"Error in batch save: {e}")
            return False
    
    
    def add_new_expense_row(self):
        """Add a new expense row locally."""
        if not self.current_sheet_name:
            QMessageBox.warning(self, "No Sheet Selected", "Please select a month first.")
            return
        
        try:
            # Load payment methods if not already loaded
            if not self.payment_methods:
                self.load_payment_methods()
            
            # Temporarily disconnect the signal
            self.data_table.itemChanged.disconnect()
            
            # Get current date in YYYY-MM-DD format
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Add new row locally
            new_row_index = self.data_table.rowCount()
            self.data_table.insertRow(new_row_index)
            
            # Create and populate row items
            # Date - auto-populated
            date_item = QTableWidgetItem(current_date)
            date_item.setToolTip("Date of expense")
            self.data_table.setItem(new_row_index, 0, date_item)
            
            # Description - empty for user input
            desc_item = QTableWidgetItem("")
            desc_item.setToolTip("Enter expense description (required)")
            self.data_table.setItem(new_row_index, 1, desc_item)
            
            # Amount - default to 0.00
            amount_item = QTableWidgetItem("0.00")
            amount_item.setToolTip("Enter amount")
            self.data_table.setItem(new_row_index, 2, amount_item)
            
            # Category - empty for user input
            category_item = QTableWidgetItem("")
            category_item.setToolTip("Enter category")
            self.data_table.setItem(new_row_index, 3, category_item)
            
            # Payment Method - create dropdown
            payment_combo = QComboBox()
            payment_combo.addItems(self.payment_methods)
            payment_combo.setEditable(True)  # Allow custom entries
            payment_combo.setCurrentText("")  # Start empty
            payment_combo.currentTextChanged.connect(
                lambda text, row=new_row_index: self.on_payment_method_changed(row, text)
            )
            self.data_table.setCellWidget(new_row_index, 4, payment_combo)
            
            # Notes - empty for user input
            notes_item = QTableWidgetItem("")
            notes_item.setToolTip("Enter notes (optional)")
            self.data_table.setItem(new_row_index, 5, notes_item)
            
            # Mark this row as having pending changes
            self.pending_changes_rows.add(new_row_index)
            
            # Store initial values as "original" for the new row
            for col in range(self.data_table.columnCount()):
                if col == 4:  # Payment Method column
                    self.original_values[(new_row_index, col)] = ""  # Empty initially
                else:
                    item = self.data_table.item(new_row_index, col)
                    self.original_values[(new_row_index, col)] = item.text() if item else ""
            
            # Reconnect the signal
            self.data_table.itemChanged.connect(self.on_table_item_changed)
            
            # Focus on description field for immediate editing
            self.data_table.setCurrentCell(new_row_index, 1)
            self.data_table.editItem(self.data_table.item(new_row_index, 1))
            
            # Update confirm button visibility
            self.update_confirm_button_visibility()
            
        except Exception as e:
            self.sheet_status_label.setText(f"❌ Error adding row: {str(e)}")
            # Reconnect signal in case of error
            if not self.data_table.itemChanged.isSignalConnected():
                self.data_table.itemChanged.connect(self.on_table_item_changed)
    
    def on_payment_method_changed(self, row: int, payment_method: str):
        """Handle payment method dropdown changes."""
        column = 4  # Payment Method column
        
        # Check if payment method value actually changed from original
        if self.check_cell_changed(row, column):
            # Track the changed cell
            self.changed_cells.add((row, column))
            # Apply highlighting to the changed cell
            self.highlight_changed_cell(row, column)
            # Mark this row as having pending changes
            self.pending_changes_rows.add(row)
        else:
            # Payment method was reverted to original value
            self.changed_cells.discard((row, column))
            # Clear highlighting
            widget = self.data_table.cellWidget(row, column)
            if isinstance(widget, QComboBox):
                widget.setStyleSheet("")  # Clear custom stylesheet
            # Check if row still has other changes
            row_has_changes = any((row, col) in self.changed_cells for col in range(self.data_table.columnCount()))
            if not row_has_changes:
                self.pending_changes_rows.discard(row)
        
        # Update confirm button visibility
        self.update_confirm_button_visibility()
    
    def refresh_current_sheet(self):
        """Refresh the current sheet data."""
        # Clear pending changes when refreshing
        self.pending_changes_rows.clear()
        
        # Clear cell highlighting
        self.clear_cell_highlighting()
        
        # Update confirm button visibility
        self.update_confirm_button_visibility()
        
        if self.current_sheet_name:
            self.load_sheet_data(self.current_sheet_name)
        else:
            self.on_date_changed()
    
    def on_selection_changed(self):
        """Handle table selection changes and update delete button visibility."""
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
    
    def delete_selected_expenses(self):
        """Delete selected expense rows after confirmation."""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        if not self.current_sheet_name:
            QMessageBox.warning(self, "No Sheet Selected", "Please select a month first.")
            return
        
        # Get expense descriptions for confirmation
        expense_descriptions = []
        for row in sorted(selected_rows):
            desc_item = self.data_table.item(row, 1)  # Description column
            date_item = self.data_table.item(row, 0)  # Date column
            if desc_item and date_item:
                desc = desc_item.text() or "(no description)"
                date = date_item.text() or "(no date)"
                expense_descriptions.append(f"{date}: {desc}")
        
        # Confirmation dialog
        count = len(selected_rows)
        row_text = "row" if count == 1 else "rows"
        expense_text = "expense" if count == 1 else "expenses"
        
        expenses_list = "\n".join([f"• {desc}" for desc in expense_descriptions[:5]])  # Show first 5
        if len(expense_descriptions) > 5:
            expenses_list += f"\n... and {len(expense_descriptions) - 5} more"
        
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {count} {expense_text}?\n\n{expenses_list}\n\n"
            f"This action cannot be undone and will remove the expenses from the '{self.current_sheet_name}' sheet.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Remove any pending changes for rows being deleted
        for row in selected_rows:
            self.pending_changes_rows.discard(row)
        
        # Delete from server
        self.sheet_status_label.setText("🗑️ Deleting expenses...")
        success_count = 0
        error_count = 0
        
        # Separate new rows from existing rows for different deletion strategies
        new_rows = []
        existing_rows = []
        
        for row in selected_rows:
            if self.is_new_row(row):
                new_rows.append(row)
            else:
                existing_rows.append(row)
        
        # Delete new rows locally (just remove from table)
        for row in sorted(new_rows, reverse=True):  # Reverse order to preserve indices
            try:
                self.data_table.removeRow(row)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error removing local row {row}: {e}")
        
        # Delete existing rows from Google Sheets (this will cause rows below to move up)
        if existing_rows:
            try:
                # Convert table row indices to sheet row numbers (add 2 for 0-based + header)
                sheet_row_numbers = [row + 2 for row in existing_rows]
                
                # Use batch delete to remove all rows at once
                success = self.sheets_service.delete_multiple_rows(
                    self.spreadsheet_id,
                    self.current_sheet_name,
                    sheet_row_numbers
                )
                
                if success:
                    success_count += len(existing_rows)
                    # Update server row count since we deleted rows from server
                    self.server_row_count -= len(existing_rows)
                else:
                    error_count += len(existing_rows)
                    
            except Exception as e:
                error_count += len(existing_rows)
                print(f"Error deleting server rows: {e}")
        
        # Update status and refresh table
        if error_count == 0:
            self.sheet_status_label.setText(f"✅ Successfully deleted {success_count} {expense_text}")
        else:
            self.sheet_status_label.setText(f"⚠️ Deleted {success_count}, failed {error_count}. Check server connection.")
        
        # Refresh table to sync with server (this will show rows moved up)
        self.load_sheet_data(self.current_sheet_name)
        
        # Hide delete button
        self.delete_button.setVisible(False)
        # Update confirm button visibility (in case pending changes were affected)
        self.update_confirm_button_visibility()
    
    def _get_cache_status_indicator(self, sheet_name: str) -> str:
        """Get cache status indicator for display in status label.
        
        Args:
            sheet_name: Name of the sheet to check.
            
        Returns:
            String indicator showing cache status.
        """
        try:
            # Check if we have a cached service with cache info
            if hasattr(self.sheets_service, 'cache_service'):
                if self.sheets_service.cache_service.is_sheet_cached(sheet_name):
                    return "📂"  # Cached
                else:
                    return "🌐"  # From server
            else:
                return "🌐"  # Regular service (no cache)
        except:
            return ""  # No indicator on error
