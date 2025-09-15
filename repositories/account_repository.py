"""
Account Repository
Data persistence layer for account management.
"""

import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from models.account_model import Account, Transaction, AccountSnapshot, AccountGroup
from models.account_model import AccountType, TransactionType
from services.cached_sheets_service import CachedGoogleSheetsService


class AccountRepository:
    """Repository for account data persistence."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize account repository.
        
        Args:
            sheets_service: Cached sheets service for data operations.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = "Accounts"
        
        # Ensure accounts sheet exists
        self._ensure_accounts_sheet()
    
    def _ensure_accounts_sheet(self) -> bool:
        """Ensure the accounts sheet exists with proper structure."""
        try:
            # Check if sheet exists
            sheet_names = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if self.sheet_name not in sheet_names:
                # Create accounts sheet
                success = self.sheets_service.create_sheet(
                    self.spreadsheet_id,
                    self.sheet_name
                )
                
                if success:
                    # Add headers
                    headers = [
                        "ID",
                        "Name", 
                        "Account Type",
                        "Current Balance",
                        "Currency",
                        "Created At",
                        "Updated At",
                        "Notes"
                    ]
                    
                    # Write headers
                    batch_updates = [{
                        'range': 'A1:H1',
                        'values': [headers]
                    }]
                    self.sheets_service.batch_update_sheet_data(
                        self.spreadsheet_id,
                        self.sheet_name,
                        batch_updates
                    )
                    
                    print(f"✅ Created '{self.sheet_name}' sheet with headers")
                    return True
                else:
                    print(f"❌ Failed to create '{self.sheet_name}' sheet")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error ensuring accounts sheet: {e}")
            return False
    
    def get_all_accounts(self, include_inactive: bool = False) -> List[Account]:
        """Get all accounts from the sheet.
        
        Args:
            include_inactive: Whether to include inactive accounts.
            
        Returns:
            List of Account objects.
        """
        try:
            # Get data from sheet
            range_name = f"'{self.sheet_name}'!A:H"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=True
            )
            
            if df.empty:
                print(f"No accounts found in '{self.sheet_name}' sheet")
                return []
            
            accounts = []
            for _, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('ID', '')) or row.get('ID', '').strip() == '':
                        continue
                    
                    # Convert row to account
                    account_data = {
                        'id': str(row['ID']),
                        'name': str(row['Name']),
                        'account_type': str(row['Account Type']),
                        'current_balance': float(row.get('Current Balance', 0)),
                        'currency': str(row.get('Currency', 'CAD')),
                        'is_active': True,  # Default to active
                        'created_at': str(row.get('Created At', '')),
                        'updated_at': str(row.get('Updated At', '')),
                        'notes': str(row['Notes']) if pd.notna(row.get('Notes')) else None
                    }
                    
                    account = Account.from_dict(account_data)
                    
                    # Filter inactive accounts if requested
                    if include_inactive or account.is_active:
                        accounts.append(account)
                        
                except Exception as e:
                    print(f"Error converting row to account: {e}")
                    continue
            
            print(f"📊 Loaded {len(accounts)} accounts from sheet")
            return accounts
            
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []
    
    def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID.
        
        Args:
            account_id: Account ID to find.
            
        Returns:
            Account object if found, None otherwise.
        """
        accounts = self.get_all_accounts(include_inactive=True)
        for account in accounts:
            if account.id == account_id:
                return account
        return None
    
    def create_account(self, account: Account) -> bool:
        """Create a new account.
        
        Args:
            account: Account object to create.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Convert account to row data
            row_data = [
                account.id,
                account.name,
                account.account_type.value,
                account.current_balance,
                account.currency.value,
                account.created_at.isoformat() if account.created_at else '',
                account.updated_at.isoformat() if account.updated_at else '',
                account.notes or ''
            ]
            
            # Get current data to find next row
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:H", use_cache=True
            )
            
            next_row = len(df) + 2  # +1 for header, +1 for 1-based indexing
            
            # Write data
            batch_updates = [{
                'range': f'A{next_row}:H{next_row}',
                'values': [row_data]
            }]
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id,
                self.sheet_name,
                batch_updates
            )
            
            if success:
                print(f"✅ Created account: {account.name}")
                return True
            else:
                print(f"❌ Failed to create account: {account.name}")
                return False
                
        except Exception as e:
            print(f"Error creating account: {e}")
            return False
    
    def update_account(self, account: Account) -> bool:
        """Update an existing account.
        
        Args:
            account: Account object with updated data.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current data
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:H", use_cache=True
            )
            
            if df.empty:
                print(f"No data in '{self.sheet_name}' sheet to update")
                return False
            
            # Find the row to update
            row_index = None
            for idx, row in df.iterrows():
                if str(row.get('ID', '')) == account.id:
                    row_index = idx + 2  # +1 for header, +1 for 1-based indexing
                    break
            
            if row_index is None:
                print(f"Account {account.id} not found for update")
                return False
            
            # Update timestamp
            account.updated_at = datetime.now()
            
            # Convert to row data
            row_data = [
                account.id,
                account.name,
                account.account_type.value,
                account.current_balance,
                account.currency.value,
                account.created_at.isoformat() if account.created_at else '',
                account.updated_at.isoformat(),
                account.notes or ''
            ]
            
            batch_updates = [{
                'range': f'A{row_index}:H{row_index}',
                'values': [row_data]
            }]
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id,
                self.sheet_name,
                batch_updates
            )
            
            if success:
                print(f"✅ Updated account: {account.name}")
                return True
            else:
                print(f"❌ Failed to update account: {account.name}")
                return False
                
        except Exception as e:
            print(f"Error updating account: {e}")
            return False
    
    def delete_account(self, account_id: str) -> bool:
        """Delete an account (soft delete by marking inactive).
        
        Args:
            account_id: ID of account to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                print(f"Account {account_id} not found for deletion")
                return False
            
            # Soft delete by marking inactive
            account.is_active = False
            account.updated_at = datetime.now()
            
            return self.update_account(account)
            
        except Exception as e:
            print(f"Error deleting account: {e}")
            return False
    
    def get_accounts_by_type(self, account_type: AccountType, 
                           include_inactive: bool = False) -> List[Account]:
        """Get accounts filtered by type.
        
        Args:
            account_type: Account type to filter by.
            include_inactive: Whether to include inactive accounts.
            
        Returns:
            List of accounts of the specified type.
        """
        all_accounts = self.get_all_accounts(include_inactive=include_inactive)
        return [acc for acc in all_accounts if acc.account_type == account_type]
    
    def update_account_balance(self, account_id: str, new_balance: float, 
                             notes: Optional[str] = None) -> bool:
        """Update account balance.
        
        Args:
            account_id: Account ID to update.
            new_balance: New balance amount.
            notes: Optional notes about the balance change.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                print(f"Account {account_id} not found for balance update")
                return False
            
            # Update balance
            account.current_balance = new_balance
            if notes:
                account.notes = notes
            
            return self.update_account(account)
            
        except Exception as e:
            print(f"Error updating account balance: {e}")
            return False


class TransactionRepository:
    """Repository for transaction data persistence."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize transaction repository.
        
        Args:
            sheets_service: Cached sheets service for data operations.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = "Transactions"
        
        # Ensure transactions sheet exists
        self._ensure_transactions_sheet()
    
    def _ensure_transactions_sheet(self) -> bool:
        """Ensure the transactions sheet exists with proper structure."""
        try:
            # Check if sheet exists
            sheet_names = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if self.sheet_name not in sheet_names:
                # Create transactions sheet
                success = self.sheets_service.create_sheet(
                    self.spreadsheet_id,
                    self.sheet_name
                )
                
                if success:
                    # Add headers
                    headers = [
                        "ID",
                        "Date",
                        "Description",
                        "Amount",
                        "Transaction Type",
                        "Category",
                        "Account ID",
                        "To Account ID",
                        "Payment Method",
                        "Notes",
                        "Tags",
                        "Reference ID",
                        "Created At"
                    ]
                    
                    # Write headers
                    batch_updates = [{
                        'range': 'A1:M1',
                        'values': [headers]
                    }]
                    self.sheets_service.batch_update_sheet_data(
                        self.spreadsheet_id,
                        self.sheet_name,
                        batch_updates
                    )
                    
                    print(f"✅ Created '{self.sheet_name}' sheet with headers")
                    return True
                else:
                    print(f"❌ Failed to create '{self.sheet_name}' sheet")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error ensuring transactions sheet: {e}")
            return False
    
    def create_transaction(self, transaction: Transaction) -> bool:
        """Create a new transaction.
        
        Args:
            transaction: Transaction object to create.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Convert transaction to row data
            row_data = [
                transaction.id,
                transaction.date.isoformat() if transaction.date else '',
                transaction.description,
                transaction.amount,
                transaction.transaction_type.value,
                transaction.category,
                transaction.account_id,
                transaction.to_account_id or '',
                transaction.payment_method or '',
                transaction.notes or '',
                ','.join(transaction.tags) if transaction.tags else '',
                transaction.reference_id or '',
                transaction.created_at.isoformat() if transaction.created_at else ''
            ]
            
            # Get current data to find next row
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:M", use_cache=True
            )
            
            next_row = len(df) + 2  # +1 for header, +1 for 1-based indexing
            
            # Write data
            batch_updates = [{
                'range': f'A{next_row}:M{next_row}',
                'values': [row_data]
            }]
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id,
                self.sheet_name,
                batch_updates
            )
            
            if success:
                print(f"✅ Created transaction: {transaction.description}")
                return True
            else:
                print(f"❌ Failed to create transaction: {transaction.description}")
                return False
                
        except Exception as e:
            print(f"Error creating transaction: {e}")
            return False
    
    def get_transactions_by_account(self, account_id: str, 
                                   limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions for a specific account.
        
        Args:
            account_id: Account ID to filter by.
            limit: Optional limit on number of transactions.
            
        Returns:
            List of Transaction objects.
        """
        try:
            # Get all transactions data
            range_name = f"'{self.sheet_name}'!A:M"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=True
            )
            
            if df.empty:
                return []
            
            transactions = []
            for _, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('ID', '')) or row.get('ID', '').strip() == '':
                        continue
                    
                    # Filter by account
                    if str(row.get('Account ID', '')) != account_id:
                        continue
                    
                    # Convert to transaction
                    transaction_data = {
                        'id': str(row['ID']),
                        'date': str(row.get('Date', '')),
                        'description': str(row.get('Description', '')),
                        'amount': float(row.get('Amount', 0)),
                        'transaction_type': str(row.get('Transaction Type', 'expense')),
                        'category': str(row.get('Category', '')),
                        'account_id': str(row.get('Account ID', '')),
                        'to_account_id': str(row['To Account ID']) if pd.notna(row.get('To Account ID')) else None,
                        'payment_method': str(row['Payment Method']) if pd.notna(row.get('Payment Method')) else None,
                        'notes': str(row['Notes']) if pd.notna(row.get('Notes')) else None,
                        'tags': str(row.get('Tags', '')),
                        'reference_id': str(row['Reference ID']) if pd.notna(row.get('Reference ID')) else None,
                        'created_at': str(row.get('Created At', ''))
                    }
                    
                    transaction = Transaction.from_dict(transaction_data)
                    transactions.append(transaction)
                        
                except Exception as e:
                    print(f"Error converting row to transaction: {e}")
                    continue
            
            # Sort by date (most recent first)
            transactions.sort(key=lambda t: t.date, reverse=True)
            
            # Apply limit if specified
            if limit:
                transactions = transactions[:limit]
            
            return transactions
            
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
