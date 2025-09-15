"""
Main Window for Expense Sheet Visualizer
Main application window with login interface and tabbed main interface.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QMessageBox, QStatusBar, 
    QProgressBar, QGroupBox, QTabWidget, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction
from typing import Optional

from services.cached_sheets_service import CachedGoogleSheetsService
from ui.tabs.overview_tab import OverviewTab
from ui.tabs.monthly_data_tab import MonthlyDataTab
from ui.tabs.categories_tab import CategoriesTab
from ui.tabs.accounts_tab import AccountsTab
from ui.threads.auth_thread import AuthThread


class MainWindow(QMainWindow):
    """Main application window - Simple Google Sheets login interface."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Expense Sheet Visualizer - Login")
        self.setGeometry(100, 100, 500, 400)
        self.setFixedSize(500, 400)  # Fixed size for login window
        
        # Initialize services
        self.sheets_service = None
        self.is_authenticated = False
        self.spreadsheet_id = "1FejagUIgweoIjiR-QnlNq90K7kpx42JwhW1TzyorET4"  # Default spreadsheet
        self.cache_initialized = False
        
        # UI state
        self.login_widget = None
        self.tabs_widget = None
        
        # Setup UI
        self.setup_login_ui()
        self.setup_status_bar()
        
        # Check if already authenticated
        self.check_existing_auth()
    
    def setup_login_ui(self):
        """Setup the simple login UI."""
        self.login_widget = QWidget()
        self.setCentralWidget(self.login_widget)
        
        main_layout = QVBoxLayout()
        self.login_widget.setLayout(main_layout)
        
        # Add some spacing at the top
        main_layout.addStretch()
        
        # Title
        title_label = QLabel("📊 Expense Sheet Visualizer")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2E86AB; margin: 20px;")
        main_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Connect to Google Sheets to get started")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        main_layout.addWidget(subtitle_label)
        
        # Login section
        login_group = QGroupBox("Authentication")
        login_layout = QVBoxLayout()
        login_group.setLayout(login_layout)
        
        # Status display
        self.auth_status_label = QLabel("🔴 Not connected to Google Sheets")
        self.auth_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_status_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        login_layout.addWidget(self.auth_status_label)
        
        # Login button
        self.login_button = QPushButton("🔐 Login to Google Sheets")
        self.login_button.setMinimumHeight(50)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:pressed {
                background-color: #2851a3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.login_button.clicked.connect(self.login_to_google_sheets)
        login_layout.addWidget(self.login_button)
        
        # Instructions
        instructions = QLabel("""
Instructions:
1. Click the login button above
2. Complete Google OAuth in your browser
3. Grant read/write access to your Google Sheets
4. Return to this application

✨ New Features:
• Automatically creates monthly expense sheets
• Organizes data by "Month Year" format
• Full read/write permissions for sheet management
        """)
        instructions.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                margin-top: 10px;
            }
        """)
        instructions.setWordWrap(True)
        login_layout.addWidget(instructions)
        
        main_layout.addWidget(login_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Add stretch at bottom
        main_layout.addStretch()
    
    def setup_tabs_ui(self):
        """Setup the main tabbed interface after authentication."""
        self.tabs_widget = QTabWidget()
        self.setCentralWidget(self.tabs_widget)
        
        # Resize window for main interface and remove size restrictions
        self.setFixedSize(16777215, 16777215)  # Remove fixed size limit
        self.resize(1200, 800)
        self.setWindowTitle("📊 Expense Sheet Visualizer")
        
        # Create and add tabs
        self.overview_tab = OverviewTab(self.sheets_service, self.spreadsheet_id)
        self.monthly_tab = MonthlyDataTab(self.sheets_service, self.spreadsheet_id)
        self.categories_tab = CategoriesTab(self.sheets_service, self.spreadsheet_id)
        self.accounts_tab = AccountsTab(self.sheets_service, self.spreadsheet_id)
        
        self.tabs_widget.addTab(self.overview_tab, "📊 Overview")
        self.tabs_widget.addTab(self.monthly_tab, "📅 Monthly Data")
        self.tabs_widget.addTab(self.accounts_tab, "🏦 Accounts")
        self.tabs_widget.addTab(self.categories_tab, "🏷️ Categories")
        
        # Set default tab
        self.tabs_widget.setCurrentIndex(0)
        
        # Setup cache management menu
        self.setup_cache_menu()
    
    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("Ready to connect")
        self.status_bar.addWidget(self.status_label)
    
    def check_existing_auth(self):
        """Check if user is already authenticated."""
        try:
            # Try to create cached service with existing token
            self.sheets_service = CachedGoogleSheetsService(
                spreadsheet_id=self.spreadsheet_id,
                cache_file="expense_sheets_cache.json"
            )
            if self.sheets_service.is_authenticated():
                self.on_auth_success()
            else:
                self.on_auth_needed()
        except Exception:
            self.on_auth_needed()
    
    def login_to_google_sheets(self):
        """Handle login button click."""
        self.show_loading("Connecting to Google Sheets...")
        
        # Start authentication in background thread
        self.auth_thread = AuthThread(self.sheets_service)
        self.auth_thread.auth_success.connect(self.on_auth_success)
        self.auth_thread.auth_failed.connect(self.on_auth_failed)
        self.auth_thread.progress_update.connect(self.on_progress_update)
        self.auth_thread.finished.connect(self.hide_loading)
        self.auth_thread.start()
    
    def show_loading(self, message: str = "Loading..."):
        """Show loading state."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText(message)
        self.login_button.setEnabled(False)
        self.login_button.setText("🔄 Connecting...")
    
    def hide_loading(self):
        """Hide loading state."""
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        if not self.is_authenticated:
            self.login_button.setText("🔐 Login to Google Sheets")
    
    def on_progress_update(self, message: str):
        """Handle progress updates."""
        self.status_label.setText(message)
    
    def on_auth_success(self):
        """Handle successful authentication."""
        self.is_authenticated = True
        
        # If we came from auth thread, we need to recreate the cached service
        if hasattr(self, 'auth_thread') and self.auth_thread.sheets_service:
            # Create cached service wrapper around authenticated service
            self.sheets_service = CachedGoogleSheetsService(
                spreadsheet_id=self.spreadsheet_id,
                cache_file="expense_sheets_cache.json"
            )
            # The service should already be authenticated since auth_thread succeeded
        
        # Switch to main tabbed interface
        self.setup_tabs_ui()
        
        # Initialize cache in background
        self.status_label.setText("🔄 Loading data and initializing cache...")
        QTimer.singleShot(100, self.initialize_cache_async)
    
    def on_auth_failed(self, error_message: str):
        """Handle authentication failure."""
        self.is_authenticated = False
        
        # Update UI
        self.auth_status_label.setText("❌ Failed to connect to Google Sheets")
        self.auth_status_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        
        self.status_label.setText("❌ Authentication failed")
        
        # Show error message
        QMessageBox.critical(self, "Authentication Failed", f"Failed to connect to Google Sheets:\n\n{error_message}")
    
    def on_auth_needed(self):
        """Handle case when authentication is needed."""
        self.is_authenticated = False
        self.auth_status_label.setText("🔴 Not connected to Google Sheets")
        self.status_label.setText("Ready to connect - Click login button")
    
    def initialize_cache_async(self):
        """Initialize cache in background to avoid blocking UI."""
        if not self.cache_initialized and self.sheets_service:
            try:
                # Initialize cache (fetches fresh data from server)
                self.sheets_service.initialize_cache_on_startup()
                self.cache_initialized = True
                
                # Update UI
                stats = self.sheets_service.get_cache_stats()
                cache_info = f"✅ Data loaded from cache ({stats['sheet_count']} sheets, {stats['total_rows']} rows)"
                self.status_label.setText(cache_info)
                
                # Clear status message after 5 seconds
                QTimer.singleShot(5000, lambda: self.status_label.setText("Ready"))
                
            except Exception as e:
                print(f"❌ Error initializing cache: {e}")
                self.status_label.setText(f"⚠️ Cache initialization failed: {str(e)}")
                QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))
    
    def setup_cache_menu(self):
        """Setup cache management menu."""
        menubar = self.menuBar()
        
        # Cache menu
        cache_menu = menubar.addMenu("📂 Cache")
        
        # View cache stats
        stats_action = QAction("📈 View Cache Stats", self)
        stats_action.triggered.connect(self.show_cache_stats)
        cache_menu.addAction(stats_action)
        
        cache_menu.addSeparator()
        
        # Refresh cache
        refresh_action = QAction("🔄 Refresh All Data", self)
        refresh_action.triggered.connect(self.refresh_cache)
        cache_menu.addAction(refresh_action)
        
        # Clear cache
        clear_action = QAction("🧹 Clear Cache", self)
        clear_action.triggered.connect(self.clear_cache)
        cache_menu.addAction(clear_action)
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("📜 About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_cache_stats(self):
        """Show cache statistics dialog."""
        if not self.sheets_service:
            QMessageBox.warning(self, "No Service", "No sheets service available.")
            return
            
        try:
            stats = self.sheets_service.get_cache_stats()
            
            message = f"""
Cache Statistics:

📁 File: {stats['cache_file']}
📈 Size: {stats['file_size_kb']} KB
🕰 Last Updated: {stats['last_updated']}
📋 Sheets: {stats['sheet_count']}
📝 Total Rows: {stats['total_rows']}

Sheet Details:"""
            
            for sheet_name, sheet_info in stats.get('sheets', {}).items():
                message += f"\n  • {sheet_name}: {sheet_info['row_count']} rows"
            
            QMessageBox.information(self, "Cache Statistics", message)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error getting cache stats: {e}")
    
    def clear_cache(self):
        """Clear all cached data."""
        if not self.sheets_service:
            QMessageBox.warning(self, "No Service", "No sheets service available.")
            return
            
        reply = QMessageBox.question(
            self, "Clear Cache", 
            "Clear all cached data? This will refetch data from Google Sheets on next access.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.sheets_service.clear_cache()
                self.cache_initialized = False
                QMessageBox.information(self, "Cache Cleared", "Cache cleared successfully!")
                
                # Re-initialize cache
                self.status_label.setText("🔄 Reinitializing cache...")
                QTimer.singleShot(500, self.initialize_cache_async)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error clearing cache: {e}")
    
    def refresh_cache(self):
        """Refresh all cached data from server."""
        if not self.sheets_service:
            QMessageBox.warning(self, "No Service", "No sheets service available.")
            return
            
        reply = QMessageBox.question(
            self, "Refresh Cache", 
            "Refresh all data from Google Sheets? This will update the cache with latest server data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.status_label.setText("🔄 Refreshing all data from server...")
                
                # Clear cache first
                self.sheets_service.clear_cache()
                self.cache_initialized = False
                
                # Re-initialize with fresh data
                QTimer.singleShot(100, self.initialize_cache_async)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error refreshing cache: {e}")
                self.status_label.setText("Ready")
    
    def show_about(self):
        """Show about dialog."""
        message = f"""
📋 Expense Sheet Visualizer

A modern desktop application for managing expense data with Google Sheets.

Features:
• Real-time synchronization with Google Sheets
• Intelligent caching for improved performance  
• Multiple sheet management
• Account management and tracking
• Batch operations and conflict resolution

Cache Status: {'Initialized' if self.cache_initialized else 'Not initialized'}
Authentication: {'Connected' if self.is_authenticated else 'Not connected'}
        """
        
        QMessageBox.about(self, "About Expense Sheet Visualizer", message)
    
    def closeEvent(self, event):
        """Handle application closing."""
        # Clean up any running threads
        if hasattr(self, 'auth_thread') and self.auth_thread.isRunning():
            self.auth_thread.quit()
            self.auth_thread.wait()
        
        event.accept()
