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
from services.account_service import AccountService, BalanceChangeEvent
from repositories.account_repository import AccountRepository, TransactionRepository
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
        
        # Add custom account management buttons
        self._add_account_management_buttons()
        
        # Force clear cache on first load if needed (for clean start)
        self._clear_cached_accounts_if_requested()
    
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
            
            # Clear all button
            clear_btn = QPushButton("🗑️ Clear All Accounts")
            clear_btn.clicked.connect(self._show_clear_accounts_dialog)
            clear_btn.setToolTip("Remove all accounts from the sheet")
            
            button_layout.addWidget(adjust_balance_btn)
            button_layout.addWidget(summary_btn)
            button_layout.addWidget(migrate_btn)
            button_layout.addWidget(clear_btn)
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
    
    def load_data(self):
        """Load account data directly from the Google Sheets 'Accounts' sheet."""
        try:
            self.status_label.setText("📂 Loading accounts from sheet...")
            
            # Get data directly from Google Sheets using cached service
            range_name = f"'{self.sheet_name}'!A:H"  # All columns in Accounts sheet
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=True
            )
            
            if df.empty:
                # Empty sheet - show empty table
                self.data_table.setRowCount(0)
                self.server_row_count = 0
                self.status_label.setText("📝 No accounts in sheet - add some!")
                return
            
            # Convert sheet data to match our UI columns
            ui_data = []
            for _, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row.get('Name', '')) or row.get('Name', '').strip() == '':
                    continue
                    
                ui_row = [
                    str(row.get('Name', '')),
                    str(row.get('Account Type', 'Other Account')),
                    str(row.get('Current Balance', '0.00')),
                    str(row.get('Currency', 'CAD')),
                    str(row.get('Notes', ''))
                ]
                ui_data.append(ui_row)
            
            # Create DataFrame with UI column names
            columns = [config.header for config in self.columns_config]
            ui_df = pd.DataFrame(ui_data, columns=columns)
            
            if ui_df.empty:
                self.data_table.setRowCount(0)
                self.server_row_count = 0
                self.status_label.setText("📝 No valid accounts in sheet - add some!")
                return
            
            # Populate table with data using base implementation
            self.populate_table_with_data(ui_df)
            
            # Show status with cache indicator
            cache_indicator = "🏠" if self.sheets_service.cache_service.is_sheet_cached(self.sheet_name) else "🌐"
            self.status_label.setText(f"✅ Loaded {len(ui_df)} accounts from sheet {cache_indicator}")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error loading accounts: {e}")
            print(f"Error loading account data from sheet: {e}")
            # Show empty table on error
            self.data_table.setRowCount(0)
            self.server_row_count = 0
    
    def save_changes_to_server(self) -> bool:
        """Save all pending changes directly to the Google Sheets 'Accounts' sheet."""
        try:
            print(f"💾 Saving {len(self.pending_changes_rows)} account changes to sheet...")
            
            # Get all current data from table
            all_data = []
            for row in range(self.data_table.rowCount()):
                row_data = []
                for col in range(len(self.columns_config)):
                    value = self.get_cell_value(row, col).strip()
                    row_data.append(value)
                
                # Only include rows with data
                if any(cell for cell in row_data if cell):
                    all_data.append(row_data)
            
            if not all_data:
                print("No valid data to save")
                return True
            
            # Convert UI data back to sheet format
            sheet_data = []
            for ui_row in all_data:
                # Map UI columns to sheet columns
                sheet_row = [
                    ui_row[0],  # Account Name -> Name
                    ui_row[1],  # Account Type -> Account Type  
                    ui_row[2],  # Current Balance -> Current Balance
                    ui_row[3],  # Currency -> Currency
                    ui_row[4],  # Notes -> Notes
                    "",         # ID (will be auto-generated if new)
                    "",         # Created At
                    ""          # Updated At
                ]
                sheet_data.append(sheet_row)
            
            # Prepare sheet headers
            sheet_headers = ["Name", "Account Type", "Current Balance", "Currency", "Notes", "ID", "Created At", "Updated At"]
            
            # Create batch update
            batch_updates = [{
                'range': f"'{self.sheet_name}'!A1:H{len(sheet_data)+1}",
                'values': [sheet_headers] + sheet_data
            }]
            
            # Save to sheet
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id, batch_updates
            )
            
            if success:
                # Clear pending changes and refresh
                self.pending_changes_rows.clear()
                self.clear_all_highlighting()
                print(f"✅ Successfully saved {len(sheet_data)} accounts to sheet")
                
                # Refresh data from sheet
                self.load_data()
            else:
                print("❌ Failed to save accounts to sheet")
            
            return success
            
        except Exception as e:
            print(f"Error saving accounts to sheet: {e}")
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
    
    def _show_clear_accounts_dialog(self):
        """Show dialog to clear all accounts from the sheet."""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                "Clear All Accounts",
                "⚠️ WARNING: This will permanently delete ALL accounts from the Google Sheets.\n\n" +
                "This action cannot be undone!\n\n" +
                "Are you sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default to No for safety
            )
            
            if reply == QMessageBox.Yes:
                # Show additional confirmation
                final_reply = QMessageBox.question(
                    self,
                    "Final Confirmation",
                    "🚨 FINAL WARNING: You are about to delete ALL account data!\n\n" +
                    "Click YES only if you are absolutely certain.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if final_reply == QMessageBox.Yes:
                    success = self._clear_accounts_from_sheet()
                    
                    if success:
                        QMessageBox.information(
                            self,
                            "Accounts Cleared",
                            "✅ All accounts have been removed from the sheet.\n\nThe table will now refresh."
                        )
                        # Refresh data to show empty sheet
                        self.load_data()
                    else:
                        QMessageBox.warning(self, "Clear Failed", "❌ Failed to clear accounts from sheet.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear accounts: {e}")
    
    def _clear_accounts_from_sheet(self) -> bool:
        """Clear all accounts from the Google Sheets 'Accounts' sheet.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            print("🗑️ Clearing all accounts from sheet...")
            
            # Just write headers only (no data rows)
            sheet_headers = ["Name", "Account Type", "Current Balance", "Currency", "Notes", "ID", "Created At", "Updated At"]
            
            # Create batch update with only headers
            batch_updates = [{
                'range': f"'{self.sheet_name}'!A1:H1",
                'values': [sheet_headers]
            }]
            
            # Clear the sheet by writing only headers
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id, batch_updates
            )
            
            if success:
                print("✅ Successfully cleared all accounts from sheet")
                
                # Clear the cache for this sheet to force refresh
                if hasattr(self.sheets_service, 'cache_service'):
                    cache_service = self.sheets_service.cache_service
                    if hasattr(cache_service, '_cache') and 'data' in cache_service._cache:
                        sheet_key = self.sheet_name.lower().replace(' ', '-')
                        if sheet_key in cache_service._cache['data']:
                            # Clear the cached data
                            cache_service._cache['data'][sheet_key]['rows'] = []
                            cache_service._cache['data'][sheet_key]['row_count'] = 0
                            cache_service._save_cache()
                            print(f"🧹 Cleared cache for '{self.sheet_name}' sheet")
            else:
                print("❌ Failed to clear accounts from sheet")
            
            return success
            
        except Exception as e:
            print(f"Error clearing accounts from sheet: {e}")
            return False
    
    def _clear_cached_accounts_if_requested(self):
        """Clear cached accounts data to force fresh load from server.
        
        Call this method to immediately clear any cached default accounts
        and force the UI to show only what's actually in the Google Sheet.
        """
        try:
            # Clear the cache for Accounts sheet
            if hasattr(self.sheets_service, 'cache_service'):
                cache_service = self.sheets_service.cache_service
                if hasattr(cache_service, '_cache') and 'data' in cache_service._cache:
                    sheet_key = "accounts"  # Cache key for Accounts sheet
                    if sheet_key in cache_service._cache['data']:
                        print(f"🧹 Clearing cached data for '{self.sheet_name}' sheet to force fresh load...")
                        # Remove this sheet from cache entirely
                        del cache_service._cache['data'][sheet_key]
                        cache_service._save_cache()
                        print(f"✅ Cleared cache for '{self.sheet_name}' - will fetch fresh data from server")
        except Exception as e:
            print(f"Error clearing cached accounts: {e}")
    
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
    
    def closeEvent(self, event):
        """Handle tab close event."""
        try:
            # Unsubscribe from events
            self.account_service.unsubscribe_from_balance_changes(self._on_balance_change)
        except:
            pass
        
        super().closeEvent(event)
