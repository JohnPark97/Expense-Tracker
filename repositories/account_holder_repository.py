"""
Account Holder Repository
Handles data persistence for AccountHolder objects to Google Sheets.
"""

from typing import List, Optional
import pandas as pd

from models.account_holder_model import AccountHolder
from services.cached_sheets_service import CachedGoogleSheetsService


class AccountHolderRepository:
    """Repository for managing account holder data in Google Sheets."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize repository.
        
        Args:
            sheets_service: Cached Google Sheets service.
            spreadsheet_id: Google Sheets spreadsheet ID.
        """
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = "Account Holders"
        
        # Ensure the sheet exists
        self._ensure_account_holders_sheet()
    
    def _ensure_account_holders_sheet(self) -> bool:
        """Ensure the Account Holders sheet exists with proper headers.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Check if sheet exists
            sheet_names = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if self.sheet_name not in sheet_names:
                # Create the sheet
                if self.sheets_service.create_sheet(self.spreadsheet_id, self.sheet_name):
                    print(f"✅ Created '{self.sheet_name}' sheet")
                    
                    # Add headers
                    headers = ["ID", "Name"]
                    
                    # Write headers
                    batch_updates = [{
                        'range': 'A1:B1',
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
            print(f"Error ensuring account holders sheet: {e}")
            return False
    
    def get_all_account_holders(self) -> List[AccountHolder]:
        """Get all account holders from the sheet.
        
        Returns:
            List of AccountHolder objects.
        """
        try:
            # Get data from sheet
            range_name = f"'{self.sheet_name}'!A:B"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name, use_cache=True
            )
            
            if df.empty:
                print(f"No account holders found in '{self.sheet_name}' sheet")
                return []
            
            account_holders = []
            
            # Process each row
            for _, row in df.iterrows():
                try:
                    account_holder_id = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                    name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                    
                    if account_holder_id and name:
                        account_holder = AccountHolder(
                            id=account_holder_id,
                            name=name
                        )
                        account_holders.append(account_holder)
                        
                except Exception as e:
                    print(f"Error parsing account holder row: {e}")
                    continue
            
            print(f"📊 Loaded {len(account_holders)} account holders from sheet")
            return account_holders
            
        except Exception as e:
            print(f"Error getting account holders: {e}")
            return []
    
    def create_account_holder(self, account_holder: AccountHolder) -> bool:
        """Create a new account holder in the sheet.
        
        Args:
            account_holder: AccountHolder object to create.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current data to find next row
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:B", use_cache=True
            )
            
            next_row = len(df) + 2  # +1 for header, +1 for 1-based indexing
            
            # Prepare data
            row_data = [
                account_holder.id,
                account_holder.name
            ]
            
            # Write to sheet
            range_name = f"A{next_row}:B{next_row}"
            batch_updates = [{
                'range': range_name,
                'values': [row_data]
            }]
            
            success = self.sheets_service.batch_update_sheet_data(
                self.spreadsheet_id,
                self.sheet_name,
                batch_updates
            )
            
            if success:
                print(f"✅ Created account holder: {account_holder.name}")
                return True
            else:
                print(f"❌ Failed to create account holder: {account_holder.name}")
                return False
                
        except Exception as e:
            print(f"Error creating account holder: {e}")
            return False
    
    def update_account_holder(self, account_holder: AccountHolder) -> bool:
        """Update an existing account holder in the sheet.
        
        Args:
            account_holder: AccountHolder object with updated data.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current data to find the row
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:B", use_cache=True
            )
            
            # Find the row with matching ID
            for idx, row in df.iterrows():
                if str(row.iloc[0]) == account_holder.id:
                    sheet_row = idx + 2  # +1 for header, +1 for 1-based indexing
                    
                    # Prepare updated data
                    row_data = [
                        account_holder.id,
                        account_holder.name
                    ]
                    
                    # Write to sheet
                    range_name = f"A{sheet_row}:B{sheet_row}"
                    batch_updates = [{
                        'range': range_name,
                        'values': [row_data]
                    }]
                    
                    success = self.sheets_service.batch_update_sheet_data(
                        self.spreadsheet_id,
                        self.sheet_name,
                        batch_updates
                    )
                    
                    if success:
                        print(f"✅ Updated account holder: {account_holder.name}")
                        return True
                    else:
                        print(f"❌ Failed to update account holder: {account_holder.name}")
                        return False
            
            print(f"❌ Account holder not found: {account_holder.id}")
            return False
            
        except Exception as e:
            print(f"Error updating account holder: {e}")
            return False
    
    def delete_account_holder(self, account_holder_id: str) -> bool:
        """Delete an account holder from the sheet.
        
        Args:
            account_holder_id: ID of the account holder to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current data to find the row
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, f"'{self.sheet_name}'!A:B", use_cache=True
            )
            
            # Find the row with matching ID
            for idx, row in df.iterrows():
                if str(row.iloc[0]) == account_holder_id:
                    sheet_row = idx + 2  # +1 for header, +1 for 1-based indexing
                    
                    # Delete the row using the sheets service
                    success = self.sheets_service.delete_multiple_rows(
                        self.spreadsheet_id,
                        self.sheet_name,
                        [sheet_row]
                    )
                    
                    if success:
                        print(f"✅ Deleted account holder: {account_holder_id}")
                        return True
                    else:
                        print(f"❌ Failed to delete account holder: {account_holder_id}")
                        return False
            
            print(f"❌ Account holder not found: {account_holder_id}")
            return False
            
        except Exception as e:
            print(f"Error deleting account holder: {e}")
            return False
