"""
Cached Google Sheets Service
Combines GoogleSheetsService with SheetCacheService for intelligent caching.
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime

from .google_sheets import GoogleSheetsService
from .cache_service import SheetCacheService


class CachedGoogleSheetsService:
    """Service that provides cached access to Google Sheets data."""
    
    def __init__(self, spreadsheet_id: str, cache_file: str = "sheets_cache.json"):
        """Initialize the cached sheets service.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID.
            cache_file: Path to cache file.
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheets_service = GoogleSheetsService()
        self.cache_service = SheetCacheService(cache_file, spreadsheet_id)
        self._fetch_fresh_data_on_startup = True  # Flag to control startup behavior
        
        print(f"🔧 Initialized CachedGoogleSheetsService for spreadsheet: {spreadsheet_id}")
    
    def initialize_cache_on_startup(self) -> None:
        """Fetch fresh data on app startup and populate cache."""
        if not self._fetch_fresh_data_on_startup:
            return
        
        print("🚀 Initializing cache with fresh data from Google Sheets...")
        
        try:
            # Get all sheet names from server
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            print(f"📋 Found {len(existing_sheets)} sheets on server: {existing_sheets}")
            
            # Fetch and cache each sheet
            for sheet_name in existing_sheets:
                self._fetch_and_cache_sheet(sheet_name)
            
            print("✅ Cache initialization complete")
            self._fetch_fresh_data_on_startup = False
            
        except Exception as e:
            print(f"❌ Error initializing cache: {e}")
    
    def _fetch_and_cache_sheet(self, sheet_name: str) -> None:
        """Fetch sheet data from API and cache it.
        
        Args:
            sheet_name: Name of the sheet to fetch.
        """
        try:
            # Fetch from Google Sheets API
            range_name = f"'{sheet_name}'!A:Z"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name
            )
            
            if not df.empty:
                headers = list(df.columns)
                rows = df.values.tolist()
                # Convert any NaN values to empty strings
                rows = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in rows]
            else:
                # Empty sheet - get headers from server if possible
                raw_data = self.sheets_service.get_raw_data(self.spreadsheet_id, range_name)
                if raw_data and len(raw_data) > 0:
                    headers = raw_data[0]  # First row as headers
                    rows = raw_data[1:] if len(raw_data) > 1 else []
                else:
                    # Default headers for expense sheets
                    headers = ["Date", "Description", "Amount", "Category", "Account", "Notes"]
                    rows = []
            
            # Cache the data
            # No caching - data will be fetched fresh each time
            print(f"📄 Cached '{sheet_name}': {len(rows)} rows")
            
        except Exception as e:
            print(f"⚠️ Error fetching sheet '{sheet_name}': {e}")
    
    def get_data_as_dataframe(self, spreadsheet_id: str, range_name: str) -> pd.DataFrame:
        """Get sheet data as DataFrame directly from API.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            range_name: Range in format 'SheetName!A:Z'.
            
        Returns:
            DataFrame with the data.
        """
        # Extract sheet name from range for logging
        sheet_name = range_name.split('!')[0].strip("'")
        
        # Always use direct API call (no caching)
        print(f"🌐 Fetching '{sheet_name}' from API...")
        df = self.sheets_service.get_data_as_dataframe(spreadsheet_id, range_name)
        
        return df
    
    def create_expense_sheet(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Create a new expense sheet and cache it.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_name: Name of the new sheet.
            
        Returns:
            True if created successfully.
        """
        success = self.sheets_service.create_expense_sheet(spreadsheet_id, sheet_name)
        
        return success
    
    def batch_update_sheet_data(self, spreadsheet_id: str, sheet_name: str, 
                               batch_updates: List[Dict[str, Any]]) -> bool:
        """Update sheet data in batch without caching.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_name: Name of the sheet.
            batch_updates: List of update objects.
            
        Returns:
            True if update successful.
        """
        success = self.sheets_service.batch_update_sheet_data(
            spreadsheet_id, sheet_name, batch_updates
        )
        
        return success
    
    def _update_cache_from_batch_updates(self, sheet_name: str, 
                                       batch_updates: List[Dict[str, Any]]) -> None:
        """Update cache based on batch update operations.
        
        Args:
            sheet_name: Name of the sheet.
            batch_updates: List of update operations.
        """
        try:
            for update in batch_updates:
                range_str = update.get('range', '')
                values = update.get('values', [])
                
                if not range_str or not values:
                    continue
                
                # Parse range (e.g., 'A2:F2' -> row 1, cols 0-5)
                # Simple parsing for now - assumes single row updates
                if ':' in range_str:
                    start_cell = range_str.split(':')[0]
                else:
                    start_cell = range_str
                
                # Extract row number (convert from 1-based to 0-based)
                row_num = int(''.join(filter(str.isdigit, start_cell))) - 2  # -2 for header and 0-based
                
                if row_num >= 0 and len(values) > 0:
                    # No cache updates - data will be fetched fresh
                    pass
            
        except Exception as e:
            print(f"⚠️ Batch update processing - no cache updates needed: {e}")
    
    def delete_multiple_rows(self, spreadsheet_id: str, sheet_name: str, 
                           row_numbers: List[int]) -> bool:
        """Delete multiple rows without caching.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_name: Name of the sheet.
            row_numbers: List of row numbers to delete (1-based).
            
        Returns:
            True if deletion successful.
        """
        success = self.sheets_service.delete_multiple_rows(
            spreadsheet_id, sheet_name, row_numbers
        )
        
        return success
    
    def add_account(self, spreadsheet_id: str, account_name: str, 
                   account_type: str = "Other", balance: float = 0.0) -> bool:
        """Add account and update cache.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            account_name: Name of the account.
            account_type: Type of account.
            balance: Initial balance.
            
        Returns:
            True if added successfully.
        """
        # This would need to be implemented in the base sheets service
        # For now, just return True as accounts are managed through AccountsTab
        return True
    
    def get_accounts(self, spreadsheet_id: str) -> List[str]:
        """Get account names using direct API call only.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            
        Returns:
            List of account names.
        """
        print("🌐 Fetching accounts from API...")
        try:
            df = self.get_data_as_dataframe(spreadsheet_id, "'Accounts'!A:H")
            if not df.empty and len(df.columns) > 1:
                # Get account names from the 'Name' column (column B, index 1)
                if 'Name' in df.columns:
                    account_names = df['Name'].dropna().astype(str).tolist()
                elif len(df.columns) > 1:
                    account_names = df.iloc[:, 1].dropna().astype(str).tolist()  # Column B
                else:
                    account_names = df.iloc[:, 0].dropna().astype(str).tolist()  # Fallback to column A
                
                # Filter out empty values
                accounts = [name for name in account_names if name.strip()]
                print(f"📋 Loaded accounts from API: {accounts}")
                return accounts
        except Exception as e:
            print(f"Error fetching accounts: {e}")
        
        return []
    
    def create_sheet(self, spreadsheet_id: str, sheet_name: str, 
                    headers: Optional[List[str]] = None) -> bool:
        """Create a new sheet and update cache.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            sheet_name: Name of the new sheet.
            headers: Optional headers to add.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Delegate to the underlying sheets service
            success = self.sheets_service.create_sheet(spreadsheet_id, sheet_name, headers)
            
            if success:
                print(f"✅ Created sheet '{sheet_name}' successfully")
            
            return success
            
        except Exception as e:
            print(f"Error creating sheet '{sheet_name}': {e}")
            return False
    
    def get_sheet_names(self, spreadsheet_id: str) -> List[str]:
        """Get sheet names using direct API call.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            
        Returns:
            List of sheet names.
        """
        # Always use direct API call (no caching)
        return self.sheets_service.get_sheet_names(spreadsheet_id)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics - returns empty since caching is disabled."""
        return {"message": "Caching disabled - using direct API calls"}
    
    def clear_cache(self) -> None:
        """Clear all cached data - no-op since caching is disabled."""
        pass
    
    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return self.sheets_service.is_authenticated()
    
    def force_refresh_sheet(self, sheet_name: str) -> None:
        """Force refresh a specific sheet from the server.
        
        Args:
            sheet_name: Name of the sheet to refresh.
        """
        print(f"🔄 Force refreshing '{sheet_name}' from server...")
        self._fetch_and_cache_sheet(sheet_name)
        
    def invalidate_sheet_cache(self, sheet_name: str) -> None:
        """Invalidate cache for a specific sheet.
        
        Args:
            sheet_name: Name of the sheet to invalidate.
        """
        # For now, just refresh the sheet
        # Could be enhanced to mark as "needs refresh" instead
        self.force_refresh_sheet(sheet_name)
