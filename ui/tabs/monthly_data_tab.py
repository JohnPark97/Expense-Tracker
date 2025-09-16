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
from ui.components import DataChangeNotifier
from ui.components import show_info, show_success, show_warning, show_error, show_loading


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
        
        # Listen for category changes to refresh visible dropdowns
        try:
            self._notifier = DataChangeNotifier()
            self._notifier.categories_changed.connect(self.refresh_category_dropdowns)
        except Exception:
            pass

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
            
            show_loading(f"Loading data for {sheet_name}...")
            
            # Check if sheet exists
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if sheet_name in existing_sheets:
                self.load_data()
            else:
                show_loading(f"Creating new sheet '{sheet_name}'...")
                self.create_new_sheet(sheet_name)
                
        except Exception as e:
            show_error(f"Error changing date: {e}")
    
    def create_new_sheet(self, sheet_name: str):
        """Create a new expense sheet for the selected month."""
        try:
            success = self.sheets_service.create_expense_sheet(
                self.spreadsheet_id, sheet_name
            )
            
            if success:
                show_success(f"Created new sheet '{sheet_name}'")
                # Load the newly created sheet
                self.load_data()
            else:
                show_error(f"Failed to create sheet '{sheet_name}'")
                self.show_empty_table()
                
        except Exception as e:
            show_error(f"Error creating sheet: {e}")
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
            show_loading("Loading expense data...")
            
            # Get data using direct API call
            range_name = f"'{self.current_sheet_name}'!A:Z"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name
            )
            
            if df.empty:
                self.show_empty_table()
                show_info(f"No expenses found for {self.current_sheet_name}")
                return
            
            # Populate table
            self.populate_table_with_data(df)
            
            # Show load status
            show_success(f"Loaded {len(df)} expenses for {self.current_sheet_name}")
            
        except Exception as e:
            show_error(f"Error loading data: {e}")
            self.show_empty_table()
    
    def showEvent(self, event):
        """Handle when tab becomes visible - refresh dropdowns."""
        super().showEvent(event)
        # Small delay to ensure tab is fully loaded
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.refresh_account_dropdowns)
    
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
    
    def refresh_account_dropdowns(self):
        """Refresh account dropdown options in all visible dropdowns."""
        try:
            print("🔄 Refreshing account dropdowns in monthly data tab...")
            
            # Get updated account list
            accounts = self.get_accounts()
            print(f"📋 Available accounts: {accounts}")
            
            # Update all account dropdown widgets (column 4)
            updated_count = 0
            for row in range(self.data_table.rowCount()):
                widget = self.data_table.cellWidget(row, 4)  # Account column
                if widget and hasattr(widget, 'addItems'):
                    current_value = widget.currentText()
                    widget.clear()
                    widget.addItems(accounts)
                    # Try to restore previous selection
                    if current_value in accounts:
                        widget.setCurrentText(current_value)
                    else:
                        # If previous selection no longer exists, select first item if available
                        if accounts and len(accounts) > 0:
                            widget.setCurrentIndex(0)
                    updated_count += 1
            
            print(f"✅ Refreshed {updated_count} account dropdowns in monthly data tab")
            
            # Also update the status to show user the refresh happened
            show_success("Account options updated")
            
        except Exception as e:
            print(f"❌ Error refreshing account dropdowns: {e}")

    def refresh_category_dropdowns(self):
        """Refresh category dropdown options in all visible dropdowns."""
        try:
            print("🔄 Refreshing category dropdowns in monthly data tab...")
            # Get updated category list
            categories = self.get_categories()

            # Update all category dropdown widgets (column 3)
            updated_count = 0
            for row in range(self.data_table.rowCount()):
                widget = self.data_table.cellWidget(row, 3)  # Category column
                if widget and hasattr(widget, 'addItems'):
                    current_value = widget.currentText()
                    widget.clear()
                    widget.addItems(categories)
                    # Try to restore previous selection
                    if current_value in categories:
                        widget.setCurrentText(current_value)
                    else:
                        if categories:
                            widget.setCurrentIndex(0)
                    updated_count += 1

            print(f"✅ Refreshed {updated_count} category dropdowns in monthly data tab")

            show_success("Category options updated")

        except Exception as e:
            print(f"❌ Error refreshing category dropdowns: {e}")
    
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
                show_error("Date must be in YYYY-MM-DD or MM/DD/YYYY format")
                return False
    
    def validate_amount(self, amount_str: str) -> bool:
        """Validate amount string."""
        if not amount_str.strip():
            return False
            
        try:
            amount = float(amount_str.strip())
            return amount >= 0
        except ValueError:
            show_error("Amount must be a valid number")
            return False
    
    def validate_before_add(self) -> bool:
        """Validate conditions before adding new expense."""
        if not self.current_sheet_name:
            show_error("Please select a month first")
            return False
            
        return True
    
    def save_changes_to_server(self) -> bool:
        """Save all pending changes to the server."""
        try:
            # Get current server data
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.current_sheet_name}'!A:Z"
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
            # Get categories data from the Categories sheet (matches CategoriesTab structure)
            range_name = "'Categories'!A:B"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name
            )
            
            if df.empty:
                return ["Food", "Transportation", "Shopping", "Bills", "Entertainment"]
            
            # Extract category names from first column (Category Name)
            active_categories = []
            for _, row in df.iterrows():
                category_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                
                if category_name:
                    active_categories.append(category_name)

            
            print(f"📋 Loaded {len(active_categories)} categories: {active_categories}")
            return active_categories if active_categories else ["Food", "Transportation", "Shopping", "Bills", "Entertainment"]
            
        except Exception as e:
            print(f"Error loading categories: {e}")
            return ["Food", "Transportation", "Shopping", "Bills", "Entertainment"]
    
    def get_accounts(self) -> List[str]:
        """Get list of active account names for dropdowns.
        
        Returns:
            List of active account names from cached sheets service.
        """
        try:
            # Get accounts from direct API call
            accounts = self.sheets_service.get_accounts(self.spreadsheet_id)
            return accounts if accounts else ["Cash Wallet", "Primary Chequing"]
        except Exception as e:
            print(f"Error loading accounts: {e}")
            return ["Cash Wallet", "Primary Chequing"]
    
    def add_new_row(self):
        """Override to ensure new rows get fresh account dropdown options."""
        # Call parent to add the row (which will call get_accounts for fresh options)
        super().add_new_row()
        
        # Additional refresh to make sure all dropdowns are updated
        self.refresh_account_dropdowns()
    
