"""
Authentication Thread
Thread for handling Google authentication without blocking UI.
"""

from PySide6.QtCore import QThread, Signal

from services.google_sheets import GoogleSheetsService


class AuthThread(QThread):
    """Thread for handling Google authentication without blocking UI."""
    
    auth_success = Signal()
    auth_failed = Signal(str)
    progress_update = Signal(str)
    
    def __init__(self, sheets_service: GoogleSheetsService):
        super().__init__()
        self.sheets_service = sheets_service
    
    def run(self):
        """Run the authentication process."""
        try:
            self.progress_update.emit("Connecting to Google Sheets...")
            
            # Create a new service instance to force re-authentication
            self.sheets_service = GoogleSheetsService()
            
            if self.sheets_service.is_authenticated():
                self.progress_update.emit("Authentication successful!")
                self.auth_success.emit()
            else:
                self.auth_failed.emit("Failed to authenticate with Google Sheets")
                
        except Exception as e:
            self.auth_failed.emit(f"Authentication error: {str(e)}")
