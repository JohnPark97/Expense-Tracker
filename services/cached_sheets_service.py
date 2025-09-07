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
                    headers = ["Date", "Description", "Amount", "Category", "Payment Method", "Notes"]
                    rows = []
            
            # Cache the data
            self.cache_service.cache_sheet_data(sheet_name, headers, rows, save_immediately=False)
            print(f"📄 Cached '{sheet_name}': {len(rows)} rows")
            
        except Exception as e:
            print(f"⚠️ Error fetching sheet '{sheet_name}': {e}")
    
    def get_data_as_dataframe(self, spreadsheet_id: str, range_name: str, 
                             use_cache: bool = True) -> pd.DataFrame:
        """Get sheet data as DataFrame, using cache when available.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            range_name: Range in format 'SheetName!A:Z'.
            use_cache: Whether to use cached data.
            
        Returns:
            DataFrame with the data.
        """
        # Extract sheet name from range
        sheet_name = range_name.split('!')[0].strip("'")
        
        if use_cache and self.cache_service.is_sheet_cached(sheet_name):
            # Return cached data
            cached_data = self.cache_service.get_sheet_data(sheet_name)
            if cached_data:
                headers = cached_data["headers"]
                rows = cached_data["rows"]
                
                if rows:
                    # Fix column count mismatch by padding or trimming rows
                    normalized_rows = []
                    for row in rows:
                        if len(row) < len(headers):
                            # Pad row with empty strings
                            padded_row = row + [''] * (len(headers) - len(row))
                            normalized_rows.append(padded_row)
                        elif len(row) > len(headers):
                            # Trim row to match headers
                            trimmed_row = row[:len(headers)]
                            normalized_rows.append(trimmed_row)
                        else:
                            # Row length matches headers
                            normalized_rows.append(row)
                    
                    df = pd.DataFrame(normalized_rows, columns=headers)
                    print(f"📂 Using cached data for '{sheet_name}' ({len(normalized_rows)} rows, {len(headers)} columns)")
                else:
                    df = pd.DataFrame(columns=headers)
                    print(f"📂 Using cached data for '{sheet_name}' (0 rows, {len(headers)} columns)")
                
                return df
        
        # Fallback to API call
        print(f"🌐 Fetching '{sheet_name}' from API...")
        df = self.sheets_service.get_data_as_dataframe(spreadsheet_id, range_name)
        
        # Cache the fresh data
        if not df.empty:
            headers = list(df.columns)
            rows = df.values.tolist()
            rows = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in rows]
            self.cache_service.cache_sheet_data(sheet_name, headers, rows)
        
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
        
        if success:
            # Cache the new empty sheet
            headers = ["Date", "Description", "Amount", "Category", "Payment Method", "Notes"]
            self.cache_service.cache_sheet_data(sheet_name, headers, [])
            print(f"📝 Cached new sheet '{sheet_name}'")
        
        return success
    
    def batch_update_sheet_data(self, spreadsheet_id: str, sheet_name: str, 
                               batch_updates: List[Dict[str, Any]]) -> bool:
        """Update sheet data in batch and update cache.
        
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
        
        if success:
            # Update cache with the changes
            self._update_cache_from_batch_updates(sheet_name, batch_updates)
        
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
                    # Update the row in cache
                    self.cache_service.update_row_in_cache(sheet_name, row_num, values[0])
            
        except Exception as e:
            print(f"⚠️ Error updating cache from batch updates: {e}")
            # Fallback: refetch the entire sheet
            self._fetch_and_cache_sheet(sheet_name)
    
    def delete_multiple_rows(self, spreadsheet_id: str, sheet_name: str, 
                           row_numbers: List[int]) -> bool:
        """Delete multiple rows and update cache.
        
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
        
        if success:
            # Convert 1-based sheet row numbers to 0-based cache indices
            # Subtract 2: -1 for 1-based to 0-based, -1 for header row
            cache_indices = [row_num - 2 for row_num in row_numbers if row_num >= 2]
            cache_indices = [idx for idx in cache_indices if idx >= 0]
            
            if cache_indices:
                self.cache_service.delete_rows_from_cache(sheet_name, cache_indices)
        
        return success
    
    def add_payment_method(self, spreadsheet_id: str, method_name: str, 
                          description: str = "", active: bool = True) -> bool:
        """Add payment method and update cache.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            method_name: Name of the payment method.
            description: Description.
            active: Whether active.
            
        Returns:
            True if added successfully.
        """
        success = self.sheets_service.add_payment_method(
            spreadsheet_id, method_name, description, active
        )
        
        if success:
            # Add to cache
            new_row = [method_name, description, "Yes" if active else "No"]
            self.cache_service.add_row_to_cache("payment-methods", new_row)
        
        return success
    
    def get_payment_methods(self, spreadsheet_id: str, use_cache: bool = True) -> List[str]:
        """Get payment methods, using cache when available.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            use_cache: Whether to use cached data.
            
        Returns:
            List of payment method names.
        """
        if use_cache and self.cache_service.is_sheet_cached("payment-methods"):
            cached_data = self.cache_service.get_sheet_data("payment-methods")
            if cached_data:
                methods = []
                for row in cached_data.get("rows", []):
                    if len(row) >= 3 and row[0]:  # Has method name
                        # Check if active (default to active if not specified)
                        is_active = len(row) < 3 or row[2].upper() in ["YES", "Y", "TRUE", "1"]
                        if is_active:
                            methods.append(row[0])
                
                if methods:
                    print(f"📂 Using cached payment methods: {methods}")
                    return methods
        
        # Fallback to API
        print("🌐 Fetching payment methods from API...")
        methods = self.sheets_service.get_payment_methods(spreadsheet_id)
        
        # Cache the payment methods sheet for next time
        if methods:
            # Try to fetch full payment methods sheet to cache
            try:
                df = self.sheets_service.get_data_as_dataframe(
                    spreadsheet_id, "'Payment Methods'!A:C"
                )
                if not df.empty:
                    headers = list(df.columns)
                    rows = df.values.tolist()
                    rows = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in rows]
                    self.cache_service.cache_sheet_data("payment-methods", headers, rows)
            except:
                pass  # Ignore caching errors
        
        return methods
    
    def get_sheet_names(self, spreadsheet_id: str, use_cache: bool = True) -> List[str]:
        """Get sheet names, optionally from cache.
        
        Args:
            spreadsheet_id: The spreadsheet ID.
            use_cache: Whether to use cached names.
            
        Returns:
            List of sheet names.
        """
        if use_cache:
            cached_names = self.cache_service.get_cached_sheet_names()
            if cached_names:
                # Convert cache keys back to display names
                display_names = []
                for cache_key in cached_names:
                    if cache_key == "payment-methods":
                        display_names.append("Payment Methods")
                    else:
                        # Convert 'january-2025' back to 'January 2025'
                        parts = cache_key.split('-')
                        if len(parts) >= 2:
                            month = parts[0].capitalize()
                            year = parts[1]
                            display_names.append(f"{month} {year}")
                        else:
                            display_names.append(cache_key.replace('-', ' ').title())
                
                print(f"📂 Using cached sheet names: {display_names}")
                return display_names
        
        # Fallback to API
        return self.sheets_service.get_sheet_names(spreadsheet_id)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache_service.get_cache_stats()
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache_service.clear_cache()
        self._fetch_fresh_data_on_startup = True
    
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
