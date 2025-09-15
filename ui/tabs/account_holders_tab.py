"""
Account Holders Tab
Tab for managing account holders using the BaseEditableTable component.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QMessageBox, QInputDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal

from models.account_holder_model import AccountHolder, create_default_account_holder
from services.account_holder_service import AccountHolderService, AccountHolderChangeEvent
from repositories.account_holder_repository import AccountHolderRepository
from services.cached_sheets_service import CachedGoogleSheetsService
from ui.components import BaseEditableTable, ColumnConfig


class AccountHoldersTab(BaseEditableTable):
    """Account holder management tab using BaseEditableTable."""
    
    # Custom signals
    account_holder_changed = Signal(str, str)  # holder_id, change_type
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize account holders tab.
        
        Args:
            sheets_service: Cached sheets service.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        self.spreadsheet_id = spreadsheet_id
        
        # Initialize services
        self.account_holder_repo = AccountHolderRepository(sheets_service, spreadsheet_id)
        self.account_holder_service = AccountHolderService(self.account_holder_repo)
        
        # Subscribe to change events
        self.account_holder_service.subscribe_to_changes(self._on_account_holder_change)
        
        # Define column configuration
        columns_config = [
            ColumnConfig(
                header="Name",
                component_type="text",
                required=True,
                tooltip="Full name of the account holder (e.g., 'John Doe', 'Jane Smith')",
                validation=self.validate_name,
                resize_mode="stretch",
                width=300
            ),
            ColumnConfig(
                header="ID",
                component_type="text",
                required=False,
                tooltip="Unique identifier (auto-generated if empty)",
                default_value="",
                resize_mode="content",
                width=200,
                editable=False  # Make ID read-only
            )
        ]
        
        # Initialize base table
        super().__init__(
            columns_config=columns_config,
            sheets_service=sheets_service,
            spreadsheet_id=spreadsheet_id,
            sheet_name="Account Holders",
            title="👤 Account Holder Management",
            add_button_text="➕ Add Account Holder"
        )
        
        # Add custom management buttons
        self._add_management_buttons()
    
    def _add_management_buttons(self):
        """Add custom buttons for account holder management."""
        try:
            # Create button layout
            button_layout = QHBoxLayout()
            
            # Summary button
            summary_btn = QPushButton("📊 Summary")
            summary_btn.clicked.connect(self._show_summary)
            summary_btn.setToolTip("View account holder summary")
            
            # Default holder button  
            default_btn = QPushButton("👤 Create Default")
            default_btn.clicked.connect(self._create_default_holder)
            default_btn.setToolTip("Create a default account holder")
            
            button_layout.addWidget(summary_btn)
            button_layout.addWidget(default_btn)
            button_layout.addStretch()
            
            # Add to main layout
            main_layout = self.layout()
            if main_layout:
                main_layout.addLayout(button_layout)
        
        except Exception as e:
            print(f"Error adding management buttons: {e}")
    
    def validate_name(self, name: str) -> bool:
        """Validate account holder name.
        
        Args:
            name: Name to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not name or not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Account holder name cannot be empty.")
            return False
        
        if len(name.strip()) < 2:
            QMessageBox.warning(self, "Invalid Name", "Account holder name must be at least 2 characters long.")
            return False
        
        return True
    
    def load_data(self):
        """Load account holder data from service and populate table."""
        try:
            print("🔄 Loading account holders data...")
            self.status_label.setText("🔄 Loading account holders...")
            
            # Get data from service
            df = self.get_data_from_service()
            
            if df.empty:
                print("📝 No account holders found, showing empty table")
                self.status_label.setText("📝 No account holders found")
                self.data_table.setRowCount(0)
                return
            
            # Populate table with data
            self.populate_table_with_data(df)
            
            print(f"✅ Loaded {len(df)} account holders successfully")
            self.status_label.setText(f"✅ Loaded {len(df)} account holders")
            
        except Exception as e:
            print(f"❌ Error loading account holders data: {e}")
            self.status_label.setText(f"❌ Error loading data: {e}")
            self.data_table.setRowCount(0)
    
    def get_data_from_service(self) -> pd.DataFrame:
        """Get account holder data from service.
        
        Returns:
            DataFrame with account holder data.
        """
        try:
            # Get account holders from service
            account_holders = self.account_holder_service.get_all_account_holders()
            
            if not account_holders:
                # Return empty DataFrame with proper columns
                columns = [config.header for config in self.columns_config]
                return pd.DataFrame(columns=columns)
            
            # Convert account holders to DataFrame rows
            rows = []
            for holder in account_holders:
                row = [
                    holder.name,
                    holder.id
                ]
                rows.append(row)
            
            # Create DataFrame
            columns = [config.header for config in self.columns_config]
            df = pd.DataFrame(rows, columns=columns)
            
            print(f"📊 Loaded {len(df)} account holders from service")
            return df
            
        except Exception as e:
            print(f"Error getting account holder data from service: {e}")
            # Return empty DataFrame
            columns = [config.header for config in self.columns_config]
            return pd.DataFrame(columns=columns)
    
    def save_data_to_service(self, data: List[List[str]]) -> bool:
        """Save account holder data using service.
        
        Args:
            data: List of row data to save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            print(f"💾 Saving {len(data)} account holders using service...")
            
            # Get existing account holders for comparison
            existing_holders = {holder.id: holder for holder in self.account_holder_service.get_all_account_holders()}
            existing_by_name = {holder.name: holder for holder in existing_holders.values()}
            
            success_count = 0
            
            for i, row in enumerate(data):
                try:
                    # Skip empty rows
                    if not row or not any(cell.strip() for cell in row if cell):
                        continue
                    
                    # Parse row data
                    name = row[0].strip() if len(row) > 0 else ""
                    holder_id = row[1].strip() if len(row) > 1 else ""
                    
                    if not name:
                        continue
                    
                    # Check if this is an update or create
                    existing_holder = None
                    if holder_id:
                        existing_holder = existing_holders.get(holder_id)
                    else:
                        existing_holder = existing_by_name.get(name)
                    
                    if existing_holder:
                        # Update existing account holder
                        existing_holder.name = name
                        
                        if self.account_holder_service.update_account_holder(existing_holder):
                            success_count += 1
                    else:
                        # Create new account holder
                        if not holder_id:
                            # Generate ID if not provided
                            holder_id = f"holder_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"
                        
                        account_holder = AccountHolder(
                            id=holder_id,
                            name=name
                        )
                        
                        if self.account_holder_service.create_account_holder(account_holder):
                            success_count += 1
                
                except Exception as e:
                    print(f"Error processing account holder row {i}: {e}")
                    continue
            
            print(f"✅ Successfully saved {success_count}/{len(data)} account holders")
            return success_count > 0
            
        except Exception as e:
            print(f"Error saving account holders using service: {e}")
            return False
    
    def save_changes_to_server(self) -> bool:
        """Save all pending changes to the server using service."""
        try:
            print(f"💾 Saving {len(self.pending_changes_rows)} account holder changes...")
            
            # Collect all changed row data
            changed_data = []
            for row in self.pending_changes_rows:
                row_data = []
                for col in range(len(self.columns_config)):
                    value = self.get_cell_value(row, col).strip()
                    row_data.append(value)
                
                # Skip empty rows
                if any(cell for cell in row_data if cell):
                    changed_data.append(row_data)
            
            if not changed_data:
                print("No valid data to save")
                return True
            
            # Use the existing save_data_to_service method
            success = self.save_data_to_service(changed_data)
            
            if success:
                # Clear pending changes and refresh the table
                self.pending_changes_rows.clear()
                self.changed_cells.clear()
                self.clear_all_highlighting()
                self.load_data()  # Refresh data from service
            
            return success
            
        except Exception as e:
            print(f"Error in save_changes_to_server: {e}")
            return False
    
    def _show_summary(self):
        """Show account holder summary dialog."""
        try:
            summary = self.account_holder_service.get_account_holder_summary()
            
            summary_text = f"""
Account Holder Summary
═════════════════════

📊 Total Account Holders: {summary['total_count']}

👥 Account Holders:
"""
            
            for name in summary['names']:
                summary_text += f"• {name}\n"
            
            if not summary['names']:
                summary_text += "• No account holders found\n"
            
            QMessageBox.information(self, "Account Holder Summary", summary_text)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get summary: {e}")
    
    def _create_default_holder(self):
        """Create a default account holder."""
        try:
            name, ok = QInputDialog.getText(
                self,
                "Create Default Account Holder",
                "Enter name for the default account holder:",
                text="Default User"
            )
            
            if ok and name.strip():
                holder = create_default_account_holder(name.strip())
                
                if self.account_holder_service.create_account_holder(holder):
                    QMessageBox.information(
                        self,
                        "Success", 
                        f"Created default account holder: {name}\n\nRefresh the table to see the new account holder."
                    )
                    # Refresh data
                    self.load_data()
                else:
                    QMessageBox.warning(self, "Failed", "Failed to create default account holder.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create default account holder: {e}")
    
    def _on_account_holder_change(self, event: AccountHolderChangeEvent):
        """Handle account holder change events.
        
        Args:
            event: Account holder change event.
        """
        try:
            # Emit custom signal
            self.account_holder_changed.emit(
                event.account_holder.id,
                event.change_type
            )
            
            # Update UI if needed
            print(f"👤 Account holder {event.change_type}: {event.account_holder.name}")
        
        except Exception as e:
            print(f"Error handling account holder change event: {e}")
    
    def closeEvent(self, event):
        """Handle tab close event."""
        try:
            # Unsubscribe from events
            self.account_holder_service.unsubscribe_from_changes(self._on_account_holder_change)
        except:
            pass
        
        super().closeEvent(event)
