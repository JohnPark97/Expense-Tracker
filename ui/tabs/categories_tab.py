"""
Categories Tab (Example)
Example of how easy it is to create new tabs using the BaseEditableTable component.
This tab manages expense categories.
"""

import pandas as pd
from typing import List

from services.cached_sheets_service import CachedGoogleSheetsService  
from ui.components import BaseEditableTable, ColumnConfig, ReactiveDropdownManager


class CategoriesTab(BaseEditableTable):
    """Expense categories management tab - example of BaseEditableTable usage."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize categories tab.
        
        Args:
            sheets_service: Cached sheets service.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        # Define column configuration - this is all we need to define!
        columns_config = [
            ColumnConfig(
                header="Category Name",
                component_type="text", 
                required=True,
                tooltip="Name of the expense category (e.g., 'Food', 'Transportation')",
                validation=self.validate_category_name,
                resize_mode="content"
            ),
            ColumnConfig(
                header="Description",
                component_type="text",
                tooltip="Optional description of the category",
                resize_mode="stretch"
            )
        ]
        
        # Initialize base table - that's it!
        super().__init__(
            columns_config=columns_config,
            sheets_service=sheets_service,
            spreadsheet_id=spreadsheet_id,
            sheet_name="Categories",
            title="🏷️ Expense Categories",
            add_button_text="➕ Add Category"
        )
        
        # Ensure sheet exists
        self.ensure_categories_sheet()
    
    def validate_category_name(self, name: str) -> bool:
        """Validate category name for uniqueness."""
        if not name or not name.strip():
            return False
        
        # Check for duplicates
        name_lower = name.strip().lower()
        for row in range(self.data_table.rowCount()):
            if row != self.data_table.currentRow():
                existing = self.get_cell_value(row, 0).strip().lower()
                if existing == name_lower:
                    self.status_label.setText(f"❌ Category '{name}' already exists")
                    return False
        return True
    
    def ensure_categories_sheet(self):
        """Ensure Categories sheet exists."""
        try:
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            if self.sheet_name not in existing_sheets:
                self.status_label.setText(f"🔄 Creating {self.sheet_name} sheet...")
                
                # Create sheet with headers
                headers = [col.header for col in self.columns_config]
                success = self.sheets_service.sheets_service.create_sheet(
                    self.spreadsheet_id, self.sheet_name, headers
                )
                
                if success:
                    # Add some default categories
                    default_categories = [
                        ["Food & Dining", "Restaurants, groceries, meals"],
                        ["Transportation", "Gas, parking, public transit"], 
                        ["Shopping", "Clothes, electronics, misc purchases"],
                        ["Bills & Utilities", "Rent, electricity, internet, phone"],
                        ["Entertainment", "Movies, games, subscriptions"],
                        ["Healthcare", "Medical, pharmacy, insurance"]
                    ]
                    
                    for category_data in default_categories:
                        self.sheets_service.sheets_service.update_sheet_data(
                            self.spreadsheet_id, self.sheet_name, 
                            [category_data], f"A{len(default_categories) + 2}"
                        )
                    
                    self.status_label.setText(f"✅ {self.sheet_name} sheet created with default categories")
                else:
                    self.status_label.setText(f"❌ Failed to create {self.sheet_name} sheet")
        except Exception as e:
            self.status_label.setText(f"❌ Error creating sheet: {e}")
    
    def load_data(self):
        """Load categories data."""
        try:
            self.status_label.setText("📂 Loading categories...")
            
            range_name = f"'{self.sheet_name}'!A:B"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name
            )
            
            if df.empty:
                self.data_table.setRowCount(0)
                self.server_row_count = 0
                self.status_label.setText("📝 No categories found")
                return
            
            self.populate_table_with_data(df)
            
            self.status_label.setText(f"✅ Loaded {len(df)} categories")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error loading categories: {e}")
    
    def populate_table_with_data(self, df: pd.DataFrame):
        """Populate table with categories data."""
        # Temporarily disconnect signals
        self.data_table.itemChanged.disconnect()
        
        self.server_row_count = len(df)
        self.data_table.setRowCount(len(df))
        
        for row in range(len(df)):
            for col in range(min(len(df.columns), len(self.columns_config))):
                value = str(df.iloc[row, col]) if pd.notna(df.iloc[row, col]) else ""
                component = self.create_cell_component(row, col, value)
                
                if hasattr(component, 'currentText'):
                    self.data_table.setCellWidget(row, col, component)
                else:
                    self.data_table.setItem(row, col, component)
        
        # Reset state
        self.store_original_values()
        self.pending_changes_rows.clear()
        self.changed_cells.clear()
        self.clear_all_highlighting()
        self.update_confirm_button_visibility()
        
        # Reconnect signals
        self.data_table.itemChanged.connect(self.on_table_item_changed)
    
    def delete_selected_rows(self):
        """Override delete to notify category dropdowns."""
        # Call parent delete functionality
        super().delete_selected_rows()
        
        # Notify all category dropdowns of the change
        ReactiveDropdownManager.notify_categories_changed()
        print("📢 Categories deleted - notifying all category dropdowns")
    
    def save_changes_to_server(self) -> bool:
        """Save changes to server."""
        try:
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:E"
            )
            current_server_rows = len(df)
            
            batch_updates = []
            for row in self.pending_changes_rows:
                row_data = [self.get_cell_value(row, col) for col in range(len(self.columns_config))]
                
                if row < current_server_rows:
                    sheet_row = row + 2
                    range_str = f"A{sheet_row}:E{sheet_row}"
                else:
                    next_row = current_server_rows + len([r for r in self.pending_changes_rows if r >= current_server_rows]) + 1
                    range_str = f"A{next_row}:E{next_row}"
                
                batch_updates.append({'range': range_str, 'values': [row_data]})
            
            if batch_updates:
                success = self.sheets_service.batch_update_sheet_data(
                    self.spreadsheet_id, self.sheet_name, batch_updates
                )
                if success:
                    ReactiveDropdownManager.notify_categories_changed()  # Notify all category dropdowns
                    print(f"📢 Categories saved - notifying all category dropdowns")
                return success
            return True
            
        except Exception as e:
            print(f"Error saving categories: {e}")
            return False
    
    
    def get_active_categories(self) -> List[str]:
        """Get list of active category names."""
        active_categories = []
        for row in range(self.data_table.rowCount()):
            name = self.get_cell_value(row, 0).strip()
            is_active = self.get_cell_value(row, 4).strip().upper() in ["YES", "Y", "TRUE", "1"]
            
            if name and is_active:
                active_categories.append(name)
        
        return active_categories if active_categories else ["Food", "Transportation", "Shopping"]
