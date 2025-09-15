"""
Google Sheets Service
Handles authentication and data retrieval from Google Sheets API.
"""

import os.path
from typing import Optional, List, Dict, Any
import pandas as pd

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsService:
    """Service class for Google Sheets API operations."""
    
    def __init__(self, scopes: Optional[List[str]] = None):
        """Initialize the Google Sheets service.
        
        Args:
            scopes: List of OAuth2 scopes. Defaults to full read/write access.
        """
        self.scopes = scopes or ["https://www.googleapis.com/auth/spreadsheets"]
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with Google Sheets API.
        
        Returns:
            True if authentication successful, False otherwise.
        """
        try:
            creds = None
            token_file = "token.json"
            credentials_file = "credentials.json"
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, self.scopes)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(credentials_file):
                        raise FileNotFoundError(
                            f"Credentials file '{credentials_file}' not found. "
                            "Please download it from Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_file, "w") as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build("sheets", "v4", credentials=creds)
            return True
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def get_spreadsheet_info(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """Get spreadsheet metadata.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            
        Returns:
            Spreadsheet metadata or None if error.
        """
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            return result
        except HttpError as err:
            print(f"Error getting spreadsheet info: {err}")
            return None
    
    def get_sheet_names(self, spreadsheet_id: str) -> List[str]:
        """Get list of sheet names in the spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            
        Returns:
            List of sheet names.
        """
        try:
            spreadsheet = self.get_spreadsheet_info(spreadsheet_id)
            if spreadsheet:
                sheets = spreadsheet.get("sheets", [])
                return [sheet["properties"]["title"] for sheet in sheets]
            return []
        except Exception as e:
            print(f"Error getting sheet names: {e}")
            return []
    
    def get_raw_data(self, spreadsheet_id: str, range_name: str) -> List[List[str]]:
        """Fetch raw data from Google Sheets.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range_name: The A1 notation range to retrieve.
            
        Returns:
            List of rows, where each row is a list of cell values.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get("values", [])
        
        except HttpError as err:
            print(f"HTTP Error: {err}")
            return []
        except Exception as err:
            print(f"Error fetching data: {err}")
            return []
    
    def get_data_as_dataframe(self, spreadsheet_id: str, range_name: str, 
                            has_header: bool = True) -> pd.DataFrame:
        """Fetch data from Google Sheets and return as pandas DataFrame.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range_name: The A1 notation range to retrieve.
            has_header: Whether the first row contains column headers.
            
        Returns:
            pandas DataFrame with the data.
        """
        try:
            values = self.get_raw_data(spreadsheet_id, range_name)
            
            if not values:
                return pd.DataFrame()
            
            if has_header and len(values) > 1:
                # First row as column headers
                headers = values[0]
                rows = values[1:]
                
                # Normalize row lengths to match headers
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
            elif has_header and len(values) == 1:
                # Only header row
                df = pd.DataFrame(columns=values[0])
            else:
                # No header or header disabled
                df = pd.DataFrame(values)
            
            return df
        
        except Exception as e:
            print(f"Error creating DataFrame: {e}")
            return pd.DataFrame()
    
    def create_sheet(self, spreadsheet_id: str, sheet_name: str, 
                    headers: Optional[List[str]] = None) -> bool:
        """Create a new sheet in the spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the new sheet to create.
            headers: Optional list of column headers to add.
            
        Returns:
            True if sheet created successfully, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            # Create the sheet
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
            
            body = {
                'requests': requests
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print(f"Sheet '{sheet_name}' created successfully")
            
            # Add headers if provided
            if headers:
                self.add_sheet_headers(spreadsheet_id, sheet_name, headers)
            
            return True
            
        except HttpError as err:
            if err.resp.status == 400 and 'already exists' in str(err):
                print(f"Sheet '{sheet_name}' already exists")
                return False
            print(f"HTTP Error creating sheet: {err}")
            return False
        except Exception as err:
            print(f"Error creating sheet: {err}")
            return False
    
    def add_sheet_headers(self, spreadsheet_id: str, sheet_name: str, 
                         headers: List[str]) -> bool:
        """Add headers to a sheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.
            headers: List of column headers.
            
        Returns:
            True if headers added successfully, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            range_name = f"'{sheet_name}'!A1"
            
            body = {
                'values': [headers]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Headers added to sheet '{sheet_name}'")
            return True
            
        except Exception as err:
            print(f"Error adding headers: {err}")
            return False
    
    def update_sheet_data(self, spreadsheet_id: str, sheet_name: str, 
                         data: List[List[str]], start_cell: str = "A2") -> bool:
        """Update data in a sheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.
            data: 2D list of data to write.
            start_cell: Starting cell (e.g., 'A2').
            
        Returns:
            True if data updated successfully, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            range_name = f"'{sheet_name}'!{start_cell}"
            
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Data updated in sheet '{sheet_name}'")
            return True
            
        except Exception as err:
            print(f"Error updating sheet data: {err}")
            return False
    
    def batch_update_sheet_data(self, spreadsheet_id: str, sheet_name: str, 
                               batch_updates: List[Dict[str, Any]]) -> bool:
        """Update multiple ranges in a sheet in a single batch operation.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.
            batch_updates: List of update objects with 'range' and 'values' keys.
                          Example: [{'range': 'A2:F2', 'values': [['data1', 'data2', ...]]}]
            
        Returns:
            True if batch update successful, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            # Prepare the batch update request
            value_range_body = []
            for update in batch_updates:
                range_name = f"'{sheet_name}'!{update['range']}"
                value_range_body.append({
                    'range': range_name,
                    'values': update['values']
                })
            
            batch_update_body = {
                'valueInputOption': 'RAW',
                'data': value_range_body
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_update_body
            ).execute()
            
            updated_cells = result.get('totalUpdatedCells', 0)
            print(f"Batch update completed - {updated_cells} cells updated in sheet '{sheet_name}'")
            return True
            
        except Exception as err:
            print(f"Error in batch update: {err}")
            return False
    
    def create_expense_sheet(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Create a new expense tracking sheet with default headers and payment method validation.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the new expense sheet.
            
        Returns:
            True if sheet created successfully, False otherwise.
        """
        default_headers = ["Date", "Description", "Amount", "Category", "Payment Method", "Notes"]
        success = self.create_sheet(spreadsheet_id, sheet_name, default_headers)
        
        if success:
            # Set up payment method dropdown validation
            self.setup_payment_method_validation(spreadsheet_id, sheet_name)
            
        return success
    
    def create_payment_methods_sheet(self, spreadsheet_id: str) -> bool:
        """Create a dedicated sheet for managing payment methods.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            
        Returns:
            True if sheet created successfully, False otherwise.
        """
        sheet_name = "Payment Methods"
        headers = ["Payment Method", "Description", "Active"]
        
        # Create the sheet
        success = self.create_sheet(spreadsheet_id, sheet_name, headers)
        
        if success:
            # Add default payment methods
            default_methods = [
                ["Cash", "Physical cash payments", "Yes"],
                ["Debit Card", "Bank debit card transactions", "Yes"],
                ["Credit Card", "Credit card payments", "Yes"],
                ["Bank Transfer", "Direct bank transfers", "Yes"],
                ["Mobile Payment", "Apps like Venmo, PayPal, etc.", "Yes"],
                ["Check", "Paper check payments", "Yes"]
            ]
            
            self.update_sheet_data(spreadsheet_id, sheet_name, default_methods, "A2")
            print(f"Added default payment methods to '{sheet_name}' sheet")
            
        return success
    
    def get_payment_methods(self, spreadsheet_id: str) -> List[str]:
        """Get list of active payment methods.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            
        Returns:
            List of active payment method names.
        """
        try:
            # Try to get data from Payment Methods sheet
            df = self.get_data_as_dataframe(spreadsheet_id, "'Payment Methods'!A:C")
            
            if df.empty:
                # If Payment Methods sheet doesn't exist or is empty, return defaults
                return ["Cash", "Debit Card", "Credit Card", "Bank Transfer", "Mobile Payment", "Check"]
            
            # Filter for active payment methods
            if "Active" in df.columns and "Payment Method" in df.columns:
                active_methods = df[df["Active"].str.upper() == "YES"]["Payment Method"].tolist()
                return [str(method) for method in active_methods if pd.notna(method)]
            elif "Payment Method" in df.columns:
                # If no Active column, return all methods
                return [str(method) for method in df["Payment Method"].tolist() if pd.notna(method)]
            else:
                return ["Cash", "Debit Card", "Credit Card", "Bank Transfer"]
                
        except Exception as e:
            print(f"Error getting payment methods: {e}")
            return ["Cash", "Debit Card", "Credit Card", "Bank Transfer"]
    
    def add_payment_method(self, spreadsheet_id: str, method_name: str, 
                          description: str = "", active: bool = True) -> bool:
        """Add a new payment method.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            method_name: Name of the payment method.
            description: Optional description.
            active: Whether the method is active.
            
        Returns:
            True if method added successfully, False otherwise.
        """
        try:
            # Ensure Payment Methods sheet exists
            existing_sheets = self.get_sheet_names(spreadsheet_id)
            if "Payment Methods" not in existing_sheets:
                self.create_payment_methods_sheet(spreadsheet_id)
            
            # Get current data to find next row
            df = self.get_data_as_dataframe(spreadsheet_id, "'Payment Methods'!A:C")
            next_row = len(df) + 2  # +1 for header, +1 for next empty row
            
            # Add new method
            new_row = [[method_name, description, "Yes" if active else "No"]]
            range_name = f"'Payment Methods'!A{next_row}"
            
            body = {'values': new_row}
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"Added payment method: {method_name}")
            return True
            
        except Exception as e:
            print(f"Error adding payment method: {e}")
            return False
    
    def setup_payment_method_validation(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Set up data validation for payment method column using Payment Methods sheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the expense sheet to add validation to.
            
        Returns:
            True if validation set up successfully, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            # Ensure Payment Methods sheet exists
            existing_sheets = self.get_sheet_names(spreadsheet_id)
            if "Payment Methods" not in existing_sheets:
                self.create_payment_methods_sheet(spreadsheet_id)
            
            # Get the sheet ID for the expense sheet
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            target_sheet_id = None
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    target_sheet_id = sheet['properties']['sheetId']
                    break
            
            if target_sheet_id is None:
                print(f"Could not find sheet ID for '{sheet_name}'")
                return False
            
            # Create data validation rule for Payment Method column (column E, index 4)
            validation_rule = {
                'setDataValidation': {
                    'range': {
                        'sheetId': target_sheet_id,
                        'startRowIndex': 1,  # Start from row 2 (skip header)
                        'endRowIndex': 1000,  # Apply to first 1000 rows
                        'startColumnIndex': 4,  # Column E (Payment Method)
                        'endColumnIndex': 5
                    },
                    'rule': {
                        'condition': {
                            'type': 'ONE_OF_RANGE',
                            'values': [{
                                'userEnteredValue': "'Payment Methods'!A2:A1000"  # Reference Payment Methods sheet
                            }]
                        },
                        'inputMessage': 'Select a payment method from the dropdown',
                        'showCustomUi': True,
                        'strict': False  # Allow custom values if needed
                    }
                }
            }
            
            # Apply the validation
            body = {'requests': [validation_rule]}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print(f"Set up payment method validation for sheet '{sheet_name}'")
            return True
            
        except Exception as e:
            print(f"Error setting up payment method validation: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if service is properly authenticated.
        
        Returns:
            True if authenticated, False otherwise.
        """
        return self.service is not None and self.credentials is not None
    
    def delete_rows(self, spreadsheet_id: str, sheet_name: str, 
                   start_row: int, num_rows: int = 1) -> bool:
        """Delete rows from a sheet, causing rows below to move up.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.
            start_row: Starting row number (1-based, includes header).
            num_rows: Number of rows to delete.
            
        Returns:
            True if rows deleted successfully, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            # Get the sheet ID
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                print(f"Could not find sheet ID for '{sheet_name}'")
                return False
            
            # Create delete request
            delete_request = {
                'deleteDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': start_row - 1,  # Convert to 0-based
                        'endIndex': start_row - 1 + num_rows  # Exclusive end
                    }
                }
            }
            
            # Execute the delete
            body = {'requests': [delete_request]}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print(f"Deleted {num_rows} row(s) starting at row {start_row} in sheet '{sheet_name}'")
            return True
            
        except Exception as e:
            print(f"Error deleting rows: {e}")
            return False
    
    def delete_multiple_rows(self, spreadsheet_id: str, sheet_name: str, 
                           row_numbers: List[int]) -> bool:
        """Delete multiple rows efficiently in a single batch operation.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            sheet_name: Name of the sheet.
            row_numbers: List of row numbers to delete (1-based, includes header).
            
        Returns:
            True if all rows deleted successfully, False otherwise.
        """
        try:
            if not self.service:
                raise Exception("Not authenticated with Google Sheets API")
            
            if not row_numbers:
                return True  # Nothing to delete
            
            # Get the sheet ID
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                print(f"Could not find sheet ID for '{sheet_name}'")
                return False
            
            # Sort rows in descending order to delete from bottom up
            # This prevents row indices from shifting during deletion
            sorted_rows = sorted(row_numbers, reverse=True)
            
            # Create delete requests for each row
            requests = []
            for row_num in sorted_rows:
                delete_request = {
                    'deleteDimension': {
                        'range': {
                            'sheetId': sheet_id,
                            'dimension': 'ROWS',
                            'startIndex': row_num - 1,  # Convert to 0-based
                            'endIndex': row_num  # Exclusive end (delete 1 row)
                        }
                    }
                }
                requests.append(delete_request)
            
            # Execute all deletes in a single batch
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            print(f"Deleted {len(row_numbers)} rows in sheet '{sheet_name}': {sorted_rows}")
            return True
            
        except Exception as e:
            print(f"Error deleting multiple rows: {e}")
            return False


# Convenience function for backward compatibility
def get_expense_data(spreadsheet_id: str = "1FejagUIgweoIjiR-QnlNq90K7kpx42JwhW1TzyorET4",
                    range_name: str = "Sheet1!A2:E") -> pd.DataFrame:
    """Legacy function to get expense data.
    
    Args:
        spreadsheet_id: The spreadsheet ID.
        range_name: The range to fetch.
        
    Returns:
        DataFrame with expense data.
    """
    service = GoogleSheetsService()
    return service.get_data_as_dataframe(spreadsheet_id, range_name)
