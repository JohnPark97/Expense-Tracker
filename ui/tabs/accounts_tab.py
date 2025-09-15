"""
Accounts Tab
Account management interface using BaseEditableTable component.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QMessageBox, QInputDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal

from models.account_model import Account, AccountType, Currency, get_account_type_display_name
from models.account_holder_model import AccountHolder
from services.account_service import AccountService, BalanceChangeEvent
from services.account_holder_service import AccountHolderService
from repositories.account_repository import AccountRepository, TransactionRepository
from repositories.account_holder_repository import AccountHolderRepository
from services.cached_sheets_service import CachedGoogleSheetsService
from ui.components import BaseEditableTable, ColumnConfig


class AccountsTab(BaseEditableTable):
    """Account management tab using BaseEditableTable."""
    
    # Custom signals
    account_balance_changed = Signal(str, float, float)  # account_id, old_balance, new_balance
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize accounts tab.
        
        Args:
            sheets_service: Cached sheets service.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        self.spreadsheet_id = spreadsheet_id
        
        # Initialize services
        self.account_repo = AccountRepository(sheets_service, spreadsheet_id)
        self.transaction_repo = TransactionRepository(sheets_service, spreadsheet_id)
        self.account_service = AccountService(self.account_repo, self.transaction_repo)
        
        # Initialize account holder services
        self.account_holder_repo = AccountHolderRepository(sheets_service, spreadsheet_id)
        self.account_holder_service = AccountHolderService(self.account_holder_repo)
        
        # Subscribe to balance change events
        self.account_service.subscribe_to_balance_changes(self._on_balance_change)
        
        # Define column configuration
        columns_config = [
            ColumnConfig(
                header="Account Name",
                component_type="text",
                required=True,
                tooltip="Name of the account (e.g., 'TD Chequing', 'Emergency Fund')",
                validation=self.validate_account_name,
                resize_mode="content",
                width=250
            ),
            ColumnConfig(
                header="Account Type",
                component_type="dropdown",
                required=True,
                options=[get_account_type_display_name(t) for t in AccountType],
                tooltip="Type of account (Chequing, Savings, Credit Card, etc.)",
                default_value=get_account_type_display_name(AccountType.CHEQUING),
                resize_mode="content",
                width=180
            ),
            ColumnConfig(
                header="Current Balance",
                component_type="text",
                required=True,
                tooltip="Current balance in the account (enter positive numbers)",
                validation=self.validate_balance,
                default_value="0.00",
                resize_mode="content",
                width=150
            ),
            ColumnConfig(
                header="Currency",
                component_type="dropdown",
                options=[c.value for c in Currency],
                default_value=Currency.CAD.value,
                tooltip="Account currency",
                resize_mode="content",
                width=100
            ),
            ColumnConfig(
                header="Notes",
                component_type="text",
                tooltip="Optional notes about this account",
                default_value="",
                resize_mode="content",
                width=200
            ),
            ColumnConfig(
                header="Account Holder",
                component_type="dropdown",
                options_source="get_account_holders",
                tooltip="Person who owns/manages this account",
                default_value="",
                resize_mode="stretch"
            )
        ]
        
        # Initialize base table
        super().__init__(
            columns_config=columns_config,
            sheets_service=sheets_service,
            spreadsheet_id=spreadsheet_id,
            sheet_name="Accounts",
            title="🏦 Account Management",
            add_button_text="➕ Add Account"
        )
        
        # Initialize default accounts if none exist
        self._initialize_accounts()
        
        # Add custom account management buttons
        self._add_account_management_buttons()
    
    def load_data(self):
        """Load account data from service and populate table."""
        try:
            print("🔄 Loading accounts data...")
            self.status_label.setText("🔄 Loading accounts...")
            
            # Get data from service
            df = self.get_data_from_service()
            
            if df.empty:
                print("📝 No accounts found, showing empty table")
                self.status_label.setText("📝 No accounts found")
                self.data_table.setRowCount(0)
                return
            
            # Populate table with data
            self.populate_table_with_data(df)
            
            print(f"✅ Loaded {len(df)} accounts successfully")
            self.status_label.setText(f"✅ Loaded {len(df)} accounts")
            
        except Exception as e:
            print(f"❌ Error loading accounts data: {e}")
            self.status_label.setText(f"❌ Error loading data: {e}")
            self.data_table.setRowCount(0)
    
    def _initialize_accounts(self):
        """Initialize default accounts if none exist."""
        try:
            self.account_service.initialize_default_accounts()
        except Exception as e:
            print(f"Error initializing accounts: {e}")
    
    def _add_account_management_buttons(self):
        """Add custom buttons for account management."""
        try:
            # Create button layout
            button_layout = QHBoxLayout()
            
            # Balance adjustment button
            adjust_balance_btn = QPushButton("💰 Adjust Balance")
            adjust_balance_btn.clicked.connect(self._show_balance_adjustment_dialog)
            adjust_balance_btn.setToolTip("Manually adjust account balance")
            
            # Account summary button
            summary_btn = QPushButton("📊 Account Summary")
            summary_btn.clicked.connect(self._show_account_summary)
            summary_btn.setToolTip("View account summary and statistics")
            
            # Migration button
            migrate_btn = QPushButton("🔄 Migrate Payment Methods")
            migrate_btn.clicked.connect(self._show_migration_dialog)
            migrate_btn.setToolTip("Convert existing payment methods to accounts")
            
            button_layout.addWidget(adjust_balance_btn)
            button_layout.addWidget(summary_btn)
            button_layout.addWidget(migrate_btn)
            button_layout.addStretch()
            
            # Add to main layout
            main_layout = self.layout()
            if main_layout:
                main_layout.addLayout(button_layout)
        
        except Exception as e:
            print(f"Error adding account management buttons: {e}")
    
    def validate_account_name(self, name: str) -> bool:
        """Validate account name.
        
        Args:
            name: Account name to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not name or not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Account name cannot be empty.")
            return False
        
        if len(name.strip()) < 2:
            QMessageBox.warning(self, "Invalid Name", "Account name must be at least 2 characters long.")
            return False
        
        return True
    
    def validate_balance(self, balance_str: str) -> bool:
        """Validate balance amount.
        
        Args:
            balance_str: Balance as string to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            balance = float(balance_str.replace('$', '').replace(',', ''))
            return True
        except ValueError:
            QMessageBox.warning(self, "Invalid Balance", "Please enter a valid number for the balance.")
            return False
    
    def get_data_from_service(self) -> pd.DataFrame:
        """Get account data from account service instead of sheets directly.
        
        Returns:
            DataFrame with account data.
        """
        try:
            # Get accounts from service
            accounts = self.account_service.get_all_accounts(include_inactive=True)
            
            if not accounts:
                # Return empty DataFrame with proper columns
                columns = [config.header for config in self.columns_config]
                return pd.DataFrame(columns=columns)
            
            # Convert accounts to DataFrame rows
            rows = []
            for account in accounts:
                # Get account holder name
                account_holder_name = ""
                if account.account_holder_id:
                    holder = self.account_holder_service.get_account_holder_by_id(account.account_holder_id)
                    if holder:
                        account_holder_name = holder.name
                
                row = [
                    account.name,
                    get_account_type_display_name(account.account_type),
                    f"{account.current_balance:.2f}",
                    account.currency.value,
                    account.notes or "",
                    account_holder_name
                ]
                rows.append(row)
            
            # Create DataFrame
            columns = [config.header for config in self.columns_config]
            df = pd.DataFrame(rows, columns=columns)
            
            print(f"📊 Loaded {len(df)} accounts from service")
            return df
            
        except Exception as e:
            print(f"Error getting account data from service: {e}")
            # Fallback to parent method
            return super().get_data_from_service()
    
    def save_data_to_service(self, data: List[List[str]]) -> bool:
        """Save account data using account service.
        
        Args:
            data: List of row data to save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            print(f"💾 Saving {len(data)} accounts using account service...")
            
            # Get existing accounts for comparison
            existing_accounts = {acc.id: acc for acc in self.account_service.get_all_accounts(include_inactive=True)}
            existing_by_name = {acc.name: acc for acc in existing_accounts.values()}
            
            success_count = 0
            
            for i, row in enumerate(data):
                try:
                    # Skip empty rows
                    if not row or not any(cell.strip() for cell in row if cell):
                        continue
                    
                    # Parse row data
                    account_name = row[0].strip() if len(row) > 0 else ""
                    account_type_display = row[1].strip() if len(row) > 1 else ""
                    balance_str = row[2].strip() if len(row) > 2 else "0.00"
                    currency_str = row[3].strip() if len(row) > 3 else "CAD"
                    notes = row[4].strip() if len(row) > 4 else ""
                    account_holder_name = row[5].strip() if len(row) > 5 else ""
                    
                    if not account_name:
                        continue
                    
                    # Convert display names back to enum values
                    account_type = None
                    for at in AccountType:
                        if get_account_type_display_name(at) == account_type_display:
                            account_type = at
                            break
                    
                    if not account_type:
                        account_type = AccountType.OTHER
                    
                    # Parse balance
                    balance = float(balance_str.replace('$', '').replace(',', ''))
                    
                    # Parse currency
                    currency = Currency.CAD
                    try:
                        currency = Currency(currency_str)
                    except ValueError:
                        pass
                    
                    # Find account holder ID by name
                    account_holder_id = None
                    if account_holder_name:
                        holder = self.account_holder_service.get_account_holder_by_name(account_holder_name)
                        if holder:
                            account_holder_id = holder.id
                    
                    # Check if this is an update or create
                    existing_account = existing_by_name.get(account_name)
                    
                    if existing_account:
                        # Update existing account
                        existing_account.name = account_name
                        existing_account.account_type = account_type
                        existing_account.current_balance = balance
                        existing_account.currency = currency
                        existing_account.notes = notes if notes else None
                        existing_account.account_holder_id = account_holder_id
                        
                        if self.account_service.update_account(existing_account):
                            success_count += 1
                    else:
                        # Create new account
                        account = Account(
                            id=f"acc_{account_name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}",
                            name=account_name,
                            account_type=account_type,
                            current_balance=balance,
                            currency=currency,
                            is_active=True,  # Default to active
                            notes=notes if notes else None,
                            account_holder_id=account_holder_id
                        )
                        
                        if self.account_service.create_account(account):
                            success_count += 1
                
                except Exception as e:
                    print(f"Error processing account row {i}: {e}")
                    continue
            
            print(f"✅ Successfully saved {success_count}/{len(data)} accounts")
            return success_count > 0
            
        except Exception as e:
            print(f"Error saving accounts using service: {e}")
            # Fallback to parent method
            return super().save_data_to_service(data)
    
    def save_changes_to_server(self) -> bool:
        """Save all pending changes to the server using account service."""
        try:
            print(f"💾 Saving {len(self.pending_changes_rows)} account changes...")
            
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
                self.clear_all_highlighting()
                self.load_data()  # Refresh data from service
            
            return success
            
        except Exception as e:
            print(f"Error in save_changes_to_server: {e}")
            return False
    
    def _show_balance_adjustment_dialog(self):
        """Show dialog to manually adjust account balance."""
        try:
            # Get selected account
            selected_rows = self.table_widget.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, "No Selection", "Please select an account to adjust balance.")
                return
            
            row = selected_rows[0].row()
            if row >= self.table_widget.rowCount():
                return
            
            # Get account name and current balance
            account_name = self.table_widget.item(row, 0).text() if self.table_widget.item(row, 0) else ""
            current_balance_str = self.table_widget.item(row, 2).text() if self.table_widget.item(row, 2) else "0.00"
            
            try:
                current_balance = float(current_balance_str.replace('$', '').replace(',', ''))
            except ValueError:
                current_balance = 0.0
            
            # Show input dialog
            new_balance, ok = QInputDialog.getDouble(
                self,
                "Adjust Balance",
                f"Enter new balance for '{account_name}':\nCurrent: ${current_balance:.2f}",
                value=current_balance,
                decimals=2
            )
            
            if ok and new_balance != current_balance:
                # Update balance in table
                self.table_widget.setItem(row, 2, self.create_table_item(f"{new_balance:.2f}"))
                
                # Mark as changed
                self.track_cell_change(row, 2)
                self.update_button_visibility()
                
                QMessageBox.information(
                    self,
                    "Balance Updated", 
                    f"Balance updated from ${current_balance:.2f} to ${new_balance:.2f}\n\nClick 'Confirm Changes' to save."
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to adjust balance: {e}")
    
    def _show_account_summary(self):
        """Show account summary dialog."""
        try:
            summary = self.account_service.get_account_summary()
            
            summary_text = f"""
Account Summary
═══════════════

📊 Overview:
• Total Accounts: {summary['total_accounts']}
• Total Balance: ${summary['total_balance']:.2f}
• Liquid Balance: ${summary['liquid_balance']:.2f}
• Net Worth: ${summary['net_worth']:.2f}

💰 By Account Type:
"""
            
            for account_type, count in summary['accounts_by_type'].items():
                balance = summary['balances_by_type'][account_type]
                summary_text += f"• {account_type.title()}: {count} accounts, ${balance:.2f}\n"
            
            QMessageBox.information(self, "Account Summary", summary_text)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get account summary: {e}")
    
    def _show_migration_dialog(self):
        """Show dialog to migrate payment methods to accounts."""
        try:
            # Get existing payment methods
            payment_methods = self.sheets_service.get_payment_methods(self.spreadsheet_id)
            
            if not payment_methods:
                QMessageBox.information(self, "No Payment Methods", "No payment methods found to migrate.")
                return
            
            # Show confirmation
            reply = QMessageBox.question(
                self,
                "Migrate Payment Methods",
                f"Found {len(payment_methods)} payment methods:\n\n" +
                "\n".join(f"• {pm}" for pm in payment_methods) +
                "\n\nDo you want to create accounts for these payment methods?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.account_service.migrate_payment_methods_to_accounts(payment_methods)
                
                if success:
                    QMessageBox.information(
                        self,
                        "Migration Completed",
                        "Payment methods have been migrated to accounts.\n\nRefresh the table to see the new accounts."
                    )
                    # Refresh data
                    self.load_data()
                else:
                    QMessageBox.warning(self, "Migration Failed", "Failed to migrate some payment methods.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to migrate payment methods: {e}")
    
    def _on_balance_change(self, event: BalanceChangeEvent):
        """Handle balance change events.
        
        Args:
            event: Balance change event.
        """
        try:
            # Emit custom signal
            self.account_balance_changed.emit(
                event.account.id,
                event.old_balance,
                event.new_balance
            )
            
            # Update UI if needed
            print(f"💰 Balance changed for {event.account.name}: ${event.old_balance:.2f} → ${event.new_balance:.2f}")
        
        except Exception as e:
            print(f"Error handling balance change event: {e}")
    
    def get_account_holders(self) -> List[str]:
        """Get account holder names for dropdown."""
        try:
            # Initialize default account holder if none exist
            self.account_holder_service.initialize_default_account_holder()
            
            # Get all account holder names
            return self.account_holder_service.get_account_holder_names()
        except Exception as e:
            print(f"Error getting account holders: {e}")
            return ["Default User"]
    
    def closeEvent(self, event):
        """Handle tab close event."""
        try:
            # Unsubscribe from events
            self.account_service.unsubscribe_from_balance_changes(self._on_balance_change)
        except:
            pass
        
        super().closeEvent(event)
