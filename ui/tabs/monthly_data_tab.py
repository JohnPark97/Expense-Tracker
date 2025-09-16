"""
Monthly Data Tab (Refactored)
Tab for managing monthly expense data using the BaseEditableTable component.
"""

import pandas as pd
from datetime import datetime
import calendar
from typing import List, Dict, Any
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QGroupBox, QPushButton, QTableWidget, QHeaderView
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from services.cached_sheets_service import CachedGoogleSheetsService
from ui.components import BaseEditableTable, ColumnConfig


class MonthlyDataTab(BaseEditableTable):
    """Monthly expense data management tab using BaseEditableTable."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize monthly data tab.
        
        Args:
            sheets_service: Cached sheets service.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        # Store for later initialization
        self.cached_sheets_service = sheets_service
        self.cached_spreadsheet_id = spreadsheet_id
        
        self.current_sheet_name = ""
        
        # Define expense column configuration
        columns_config = [
            ColumnConfig(
                header="Date",
                component_type="text",
                required=True,
                tooltip="Date of expense (YYYY-MM-DD format)",
                validation=self.validate_date,
                default_value=datetime.now().strftime("%Y-%m-%d"),
                resize_mode="content"
            ),
            ColumnConfig(
                header="Description", 
                component_type="text",
                required=True,
                tooltip="Description of the expense",
                validation=lambda x: len(x.strip()) > 0,
                resize_mode="stretch"
            ),
            ColumnConfig(
                header="Amount",
                component_type="number",
                required=True,
                tooltip="Amount spent",
                validation=self.validate_amount,
                default_value="0.00",
                resize_mode="content"
            ),
            ColumnConfig(
                header="Category",
                component_type="dropdown",
                options_source="get_categories",
                tooltip="Category of expense",
                component_config={"editable": True},
                resize_mode="content"
            ),
            ColumnConfig(
                header="Account",
                component_type="dropdown",
                options_source="get_accounts",
                tooltip="Account used for this expense",
                component_config={"editable": True},
                resize_mode="content"
            ),
            ColumnConfig(
                header="Notes",
                component_type="text",
                tooltip="Additional notes (optional)",
                default_value="",
                resize_mode="content",
                width=150
            ),
        ]
        
        # We'll initialize the base class after setting up month/year controls
        self.setup_month_year_controls()
        
        # Initialize base table (will be updated when month/year changes)
        super().__init__(
            columns_config=columns_config,
            sheets_service=sheets_service,
            spreadsheet_id=spreadsheet_id,
            sheet_name="",  # Will be set dynamically
            title="📅 Monthly Expense Data",
            add_button_text="➕ Add New Expense"
        )
        
        # Set default values
        self.setup_default_values()
    
    def setup_month_year_controls(self):
        """Setup month and year selection controls."""
        # We need to override the base UI setup to add month/year controls
        self._month_year_setup_needed = True
    
    def setup_ui(self):
        """Setup the user interface with month/year controls."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(self.title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Month/Year Selection
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
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        # Now add the rest of the standard UI components manually
        # (we can't call super().setup_ui() because it would duplicate the layout)
        
        # Controls section
        controls_group2 = QGroupBox("Actions")
        controls_layout2 = QHBoxLayout()
        controls_group2.setLayout(controls_layout2)
        layout.addWidget(controls_group2)
        
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
        controls_layout2.addWidget(self.add_button)
        
        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_data)
        controls_layout2.addWidget(self.refresh_button)
        
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
        controls_layout2.addWidget(self.confirm_button)
        
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
        controls_layout2.addWidget(self.delete_button)
        
        controls_layout2.addStretch()
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Create table
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(False)  
        self.data_table.setSortingEnabled(False)  
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.data_table)
    
    def setup_default_values(self):
        """Setup default year and month values."""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        self.year_combo.setCurrentText(str(current_year))
        self.month_combo.setCurrentText(calendar.month_name[current_month])
        
        # Load data for current month
        self.on_date_changed()
    
    def on_date_changed(self):
        """Handle year/month selection changes."""
        try:
            year = self.year_combo.currentText()
            month = self.month_combo.currentText()
            
            if not year or not month:
                return
            
            # Generate sheet name
            sheet_name = f"{month} {year}"
            self.current_sheet_name = sheet_name
            self.sheet_name = sheet_name  # Update base class property
            
            self.status_label.setText(f"🔄 Loading data for {sheet_name}...")
            
            # Check if sheet exists
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if sheet_name in existing_sheets:
                self.load_data()
            else:
                self.status_label.setText(f"🔄 Creating new sheet '{sheet_name}'...")
                self.create_new_sheet(sheet_name)
                
        except Exception as e:
            self.status_label.setText(f"❌ Error changing date: {e}")
    
    def create_new_sheet(self, sheet_name: str):
        """Create a new expense sheet for the selected month."""
        try:
            success = self.sheets_service.create_expense_sheet(
                self.spreadsheet_id, sheet_name
            )
            
            if success:
                self.status_label.setText(f"✅ Created new sheet '{sheet_name}'")
                # Load the newly created sheet
                self.load_data()
            else:
                self.status_label.setText(f"❌ Failed to create sheet '{sheet_name}'")
                self.show_empty_table()
                
        except Exception as e:
            self.status_label.setText(f"❌ Error creating sheet: {e}")
            self.show_empty_table()
    
    def show_empty_table(self):
        """Show empty table for new or failed sheets."""
        self.data_table.setRowCount(0)
        self.server_row_count = 0
        self.pending_changes_rows.clear()
        self.changed_cells.clear()
        self.original_values.clear()
        self.update_confirm_button_visibility()
    
    def load_data(self):
        """Load expense data for the current sheet."""
        if not self.current_sheet_name:
            return
            
        try:
            self.status_label.setText("📂 Loading expense data...")
            
            # Get data using direct API call
            range_name = f"'{self.current_sheet_name}'!A:Z"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=False
            )
            
            if df.empty:
                self.show_empty_table()
                self.status_label.setText(f"📝 No expenses found for {self.current_sheet_name}")
                return
            
            # Populate table
            self.populate_table_with_data(df)
            
            # Show load status
            self.status_label.setText(
                f"✅ Loaded {len(df)} expenses for {self.current_sheet_name}"
            )
            
        except Exception as e:
            self.status_label.setText(f"❌ Error loading data: {e}")
            self.show_empty_table()
    
    def populate_table_with_data(self, df: pd.DataFrame):
        """Populate table with expense data."""
        # Temporarily disconnect signals
        self.data_table.itemChanged.disconnect()
        
        # Update server row count
        self.server_row_count = len(df)
        
        # Set table size  
        self.data_table.setRowCount(len(df))
        
        # Load dropdown options
        categories = self.get_categories()
        accounts = self.get_accounts()
        
        # Populate rows
        for row in range(len(df)):
            for col in range(min(len(df.columns), len(self.columns_config))):
                value = str(df.iloc[row, col]) if pd.notna(df.iloc[row, col]) else ""
                
                # Create component
                component = self.create_cell_component(row, col, value)
                
                # Special handling for dropdown columns
                if col == 3 and hasattr(component, 'addItems'):  # Category column
                    # Clear and repopulate options
                    component.clear()
                    component.addItems(categories)
                    component.setCurrentText(value)
                elif col == 4 and hasattr(component, 'addItems'):  # Account column
                    # Clear and repopulate options
                    component.clear()
                    component.addItems(accounts)
                    component.setCurrentText(value)
                
                # Set component in table
                if hasattr(component, 'currentText'):  # It's a widget
                    self.data_table.setCellWidget(row, col, component)
                else:  # It's a table item
                    self.data_table.setItem(row, col, component)
        
        # Column widths are now configured by BaseEditableTable based on ColumnConfig resize_mode
        
        # Store original values and clear changes
        self.store_original_values()
        self.pending_changes_rows.clear()
        self.changed_cells.clear()
        self.clear_all_highlighting()
        self.update_confirm_button_visibility()
        
        # Reconnect signals
        self.data_table.itemChanged.connect(self.on_table_item_changed)
    
    def validate_date(self, date_str: str) -> bool:
        """Validate date string."""
        if not date_str.strip():
            return False
            
        try:
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return True
        except ValueError:
            try:
                datetime.strptime(date_str.strip(), "%m/%d/%Y")
                return True
            except ValueError:
                self.status_label.setText("❌ Date must be in YYYY-MM-DD or MM/DD/YYYY format")
                return False
    
    def validate_amount(self, amount_str: str) -> bool:
        """Validate amount string."""
        if not amount_str.strip():
            return False
            
        try:
            amount = float(amount_str.strip())
            return amount >= 0
        except ValueError:
            self.status_label.setText("❌ Amount must be a valid number")
            return False
    
    def validate_before_add(self) -> bool:
        """Validate conditions before adding new expense."""
        if not self.current_sheet_name:
            self.status_label.setText("❌ Please select a month first")
            return False
            
        return True
    
    def save_changes_to_server(self) -> bool:
        """Save all pending changes to the server."""
        try:
            # Get current server data
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.current_sheet_name}'!A:Z", use_cache=False
            )
            current_server_rows = len(df)
            
            # Collect batch updates
            batch_updates = []
            
            for row in self.pending_changes_rows:
                # Get complete row data
                row_data = []
                for col in range(len(self.columns_config)):
                    value = self.get_cell_value(row, col).strip()
                    row_data.append(value)
                
                if row < current_server_rows:
                    # Update existing row
                    sheet_row = row + 2
                    range_str = f"A{sheet_row}:F{sheet_row}"
                else:
                    # Add new row
                    next_row = current_server_rows + len([r for r in self.pending_changes_rows if r >= current_server_rows]) + 1  
                    range_str = f"A{next_row}:F{next_row}"
                
                batch_updates.append({
                    'range': range_str,
                    'values': [row_data]
                })
            
            if not batch_updates:
                return True
            
            # Execute batch update
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id, self.current_sheet_name, batch_updates
            )
            
            return success
            
        except Exception as e:
            print(f"Error saving expenses: {e}")
            return False
    
    
    def get_categories(self) -> List[str]:
        """Get list of active categories for use in dropdowns.
        
        Returns:
            List of active category names from Categories sheet.
        """
        try:
            # Get categories data from the Categories sheet
            range_name = "'Categories'!A:E"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=False
            )
            
            if df.empty:
                return ["Food", "Transportation", "Shopping", "Bills", "Entertainment"]
            
            # Extract active categories (column 0 = name, column 4 = active status)
            active_categories = []
            for _, row in df.iterrows():
                category_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                is_active = str(row.iloc[4]).strip().upper() in ["YES", "Y", "TRUE", "1"] if len(row) > 4 and pd.notna(row.iloc[4]) else True
                
                if category_name and is_active:
                    active_categories.append(category_name)
            
            return active_categories if active_categories else ["Food", "Transportation", "Shopping", "Bills", "Entertainment"]
            
        except Exception as e:
            print(f"Error loading categories: {e}")
            return ["Food", "Transportation", "Shopping", "Bills", "Entertainment"]
    
