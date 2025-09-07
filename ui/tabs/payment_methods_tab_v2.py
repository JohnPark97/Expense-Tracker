"""
Payment Methods Tab (Refactored)
Tab for managing payment methods using the BaseEditableTable component.
"""

import pandas as pd
from typing import List, Dict, Any

from services.cached_sheets_service import CachedGoogleSheetsService
from ui.components import BaseEditableTable, ColumnConfig


class PaymentMethodsTab(BaseEditableTable):
    """Payment methods management tab using BaseEditableTable."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize payment methods tab.
        
        Args:
            sheets_service: Cached sheets service.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        # Define column configuration
        columns_config = [
            ColumnConfig(
                header="Payment Method",
                component_type="text",
                required=True,
                tooltip="Name of the payment method (e.g., 'Credit Card', 'Cash')",
                validation=self.validate_payment_method_name
            ),
            ColumnConfig(
                header="Description", 
                component_type="text",
                tooltip="Optional description of the payment method",
                default_value=""
            ),
            ColumnConfig(
                header="Active",
                component_type="dropdown",
                options=["Yes", "No"],
                tooltip="Whether this payment method is active and available for selection",
                default_value="Yes"
            )
        ]
        
        # Initialize base table
        super().__init__(
            columns_config=columns_config,
            sheets_service=sheets_service,
            spreadsheet_id=spreadsheet_id,
            sheet_name="Payment Methods",
            title="💳 Payment Methods Management",
            add_button_text="➕ Add Payment Method"
        )
        
        # Ensure the sheet exists
        self.ensure_payment_methods_sheet()
    
    def validate_payment_method_name(self, name: str) -> bool:
        """Validate payment method name.
        
        Args:
            name: Payment method name to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not name or not name.strip():
            return False
        
        # Check for duplicates (case-insensitive)
        name_lower = name.strip().lower()
        for row in range(self.data_table.rowCount()):
            if row != self.data_table.currentRow():  # Skip current row
                existing_name = self.get_cell_value(row, 0).strip().lower()
                if existing_name == name_lower:
                    self.status_label.setText(f"❌ Payment method '{name}' already exists")
                    return False
        
        return True
    
    def validate_before_add(self) -> bool:
        """Validate conditions before adding a new payment method."""
        # Check if we're authenticated
        if not self.sheets_service.is_authenticated():
            self.status_label.setText("❌ Not authenticated with Google Sheets")
            return False
        
        return True
    
    def ensure_payment_methods_sheet(self):
        """Ensure the Payment Methods sheet exists."""
        try:
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            if "Payment Methods" not in existing_sheets:
                self.status_label.setText("🔄 Creating Payment Methods sheet...")
                success = self.sheets_service.sheets_service.create_payment_methods_sheet(
                    self.spreadsheet_id
                )
                if success:
                    self.status_label.setText("✅ Payment Methods sheet created")
                else:
                    self.status_label.setText("❌ Failed to create Payment Methods sheet")
                    return
        except Exception as e:
            self.status_label.setText(f"❌ Error checking sheets: {e}")
    
    def load_data(self):
        """Load payment methods data from the sheet."""
        try:
            self.status_label.setText("📂 Loading payment methods...")
            
            # Get data using the cached service
            range_name = f"'{self.sheet_name}'!A:C"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=True
            )
            
            if df.empty:
                # Empty sheet - just set up headers
                self.data_table.setRowCount(0)
                self.server_row_count = 0
                self.status_label.setText("📝 No payment methods found - add some!")
                return
            
            # Populate table with data
            self.populate_table_with_data(df)
            
            # Show cache status
            cache_indicator = self._get_cache_status_indicator()
            self.status_label.setText(
                f"✅ Loaded {len(df)} payment methods {cache_indicator}"
            )
            
        except Exception as e:
            self.status_label.setText(f"❌ Error loading data: {e}")
            print(f"Error loading payment methods: {e}")
    
    def populate_table_with_data(self, df: pd.DataFrame):
        """Populate the table with DataFrame data."""
        # Temporarily disconnect signals
        self.data_table.itemChanged.disconnect()
        
        # Update server row count
        self.server_row_count = len(df)
        
        # Set table size
        self.data_table.setRowCount(len(df))
        
        # Populate rows
        for row in range(len(df)):
            for col in range(min(len(df.columns), len(self.columns_config))):
                value = str(df.iloc[row, col]) if pd.notna(df.iloc[row, col]) else ""
                
                # Create component
                component = self.create_cell_component(row, col, value)
                
                if hasattr(component, 'currentText'):  # It's a widget like QComboBox
                    self.data_table.setCellWidget(row, col, component)
                else:  # It's a QTableWidgetItem
                    self.data_table.setItem(row, col, component)
        
        # Store original values
        self.store_original_values()
        
        # Clear any existing changes
        self.pending_changes_rows.clear()
        self.changed_cells.clear()
        self.clear_all_highlighting()
        
        # Update button visibility
        self.update_confirm_button_visibility()
        
        # Reconnect signals
        self.data_table.itemChanged.connect(self.on_table_item_changed)
    
    def save_changes_to_server(self) -> bool:
        """Save all pending changes to the server in a batch operation."""
        try:
            # Get current server data to determine which rows are new
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:C", use_cache=False
            )
            current_server_rows = len(df)
            
            # Collect all changes into batch updates
            batch_updates = []
            
            for row in self.pending_changes_rows:
                # Get row data
                row_data = []
                for col in range(len(self.columns_config)):
                    value = self.get_cell_value(row, col).strip()
                    row_data.append(value)
                
                if row < current_server_rows:
                    # Existing row - update
                    sheet_row = row + 2  # +2 for 1-based indexing and header
                    range_str = f"A{sheet_row}:C{sheet_row}"
                    batch_updates.append({
                        'range': range_str,
                        'values': [row_data]
                    })
                else:
                    # New row - append
                    next_row = current_server_rows + len([r for r in self.pending_changes_rows if r >= current_server_rows]) + 1
                    range_str = f"A{next_row}:C{next_row}"
                    batch_updates.append({
                        'range': range_str,
                        'values': [row_data]
                    })
            
            if not batch_updates:
                return True
            
            # Execute batch update
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id, self.sheet_name, batch_updates
            )
            
            return success
            
        except Exception as e:
            print(f"Error saving payment methods: {e}")
            return False
    
    def _get_cache_status_indicator(self) -> str:
        """Get cache status indicator."""
        try:
            if hasattr(self.sheets_service, 'cache_service'):
                if self.sheets_service.cache_service.is_sheet_cached("payment-methods"):
                    return "📂"  # From cache
                else:
                    return "🌐"  # From server
            else:
                return "🌐"  # No cache
        except:
            return ""
    
    def get_active_payment_methods(self) -> List[str]:
        """Get list of active payment methods for use in dropdowns.
        
        Returns:
            List of active payment method names.
        """
        active_methods = []
        
        for row in range(self.data_table.rowCount()):
            method_name = self.get_cell_value(row, 0).strip()
            is_active = self.get_cell_value(row, 2).strip().upper() in ["YES", "Y", "TRUE", "1"]
            
            if method_name and is_active:
                active_methods.append(method_name)
        
        return active_methods if active_methods else ["Cash", "Credit Card", "Debit Card"]
