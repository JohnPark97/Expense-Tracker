"""
Overview Tab (Updated)
Main dashboard with previews of key visualizations and progressive disclosure.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QGridLayout, QGroupBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from typing import Optional

from services.cached_sheets_service import CachedGoogleSheetsService
from services.analytics_service import AnalyticsService
from ui.components.visualization_container import VisualizationContainer
from ui.components.base_chart import ChartMode


class OverviewTab(QWidget):
    """Overview dashboard with visualization previews and progressive disclosure."""
    
    def __init__(self, sheets_service: Optional[CachedGoogleSheetsService] = None, spreadsheet_id: str = ""):
        super().__init__()
        
        # Services
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.analytics_service = None
        
        # UI state
        self.visualization_containers = {}
        self.is_initialized = False
        
        self.setup_ui()
        
        # Initialize with services if provided, otherwise show placeholder
        if sheets_service and spreadsheet_id:
            self.initialize_with_services(sheets_service, spreadsheet_id)
        else:
            self.show_placeholder()
    
    def setup_ui(self):
        """Setup the overview dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Header
        self.create_header(layout)
        
        # Main content area (will contain visualizations or placeholder)
        self.main_content = QWidget()
        layout.addWidget(self.main_content)
    
    def create_header(self, layout: QVBoxLayout):
        """Create the dashboard header."""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("📊 Expense Analytics Dashboard")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Refresh button (will be shown when initialized)
        self.refresh_button = QPushButton("🔄 Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_all_data)
        self.refresh_button.setVisible(False)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976d2; }
        """)
        header_layout.addWidget(self.refresh_button)
        
        layout.addWidget(header_widget)
        
        # Subtitle/status
        self.status_label = QLabel("Loading analytics...")
        self.status_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(self.status_label)
    
    def show_placeholder(self):
        """Show placeholder when services are not available."""
        placeholder_layout = QVBoxLayout(self.main_content)
        
        placeholder = QLabel("""
        🔑 Please authenticate with Google Sheets to see your expense analytics.
        
        Once connected, this dashboard will show:
        • Monthly spending trends
        • Category breakdowns  
        • Payment method analysis
        • Interactive charts with drill-down capabilities
        """)
        placeholder.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                padding: 40px;
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 10px;
                margin: 20px;
            }
        """)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        placeholder_layout.addWidget(placeholder)
        
        self.status_label.setText("Authentication required")
    
    def initialize_with_services(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Initialize the dashboard with Google Sheets services."""
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.analytics_service = AnalyticsService(sheets_service, spreadsheet_id)
        
        self.status_label.setText("Initializing analytics...")
        
        # Initialize asynchronously to prevent UI blocking
        QTimer.singleShot(100, self.setup_dashboard)
    
    def setup_dashboard(self):
        """Setup the main dashboard with visualization previews."""
        try:
            # Clear existing content
            if self.main_content.layout():
                self.clear_layout(self.main_content.layout())
            
            # Create scroll area for dashboard
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            dashboard_widget = QWidget()
            dashboard_layout = QGridLayout(dashboard_widget)
            dashboard_layout.setSpacing(20)
            
            # Create visualization previews
            self.create_visualization_previews(dashboard_layout)
            
            scroll_area.setWidget(dashboard_widget)
            
            # Add scroll area to main content
            main_layout = QVBoxLayout(self.main_content)
            main_layout.addWidget(scroll_area)
            
            self.status_label.setText("Dashboard ready - Click on any chart to explore in detail")
            self.refresh_button.setVisible(True)
            self.is_initialized = True
            
        except Exception as e:
            self.show_error(f"Error setting up dashboard: {e}")
    
    def create_visualization_previews(self, layout: QGridLayout):
        """Create preview visualizations for the dashboard."""
        # Row 0: Monthly Spending Overview
        monthly_spending_container = VisualizationContainer(
            self.analytics_service,
            visualization_type="monthly_spending",
            initial_mode=ChartMode.PREVIEW
        )
        monthly_spending_container.mode_changed.connect(self.on_visualization_mode_changed)
        self.visualization_containers["monthly_spending"] = monthly_spending_container
        
        spending_group = QGroupBox("💰 Monthly Spending Overview")
        spending_layout = QVBoxLayout(spending_group)
        spending_layout.addWidget(monthly_spending_container)
        layout.addWidget(spending_group, 0, 0, 1, 2)  # Span 2 columns
        
        # Row 1: Spending Trend
        trend_container = VisualizationContainer(
            self.analytics_service,
            visualization_type="monthly_trend", 
            initial_mode=ChartMode.PREVIEW
        )
        trend_container.mode_changed.connect(self.on_visualization_mode_changed)
        self.visualization_containers["monthly_trend"] = trend_container
        
        trend_group = QGroupBox("📈 Spending Trend")
        trend_layout = QVBoxLayout(trend_group)
        trend_layout.addWidget(trend_container)
        layout.addWidget(trend_group, 1, 0)
        
        # Row 1, Col 2: Quick Stats (placeholder for now)
        stats_group = QGroupBox("📊 Quick Stats")
        stats_layout = QVBoxLayout(stats_group)
        stats_placeholder = QLabel("""
        Category Breakdown
        Budget Tracking
        Recent Expenses
        
        Coming Soon!
        """)
        stats_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_placeholder.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
        stats_layout.addWidget(stats_placeholder)
        layout.addWidget(stats_group, 1, 1)
        
        # Row 2: Future visualizations placeholder
        future_group = QGroupBox("🔮 More Insights Coming Soon")
        future_layout = QVBoxLayout(future_group)
        future_placeholder = QLabel("""
        • Category spending analysis
        • Payment method breakdown
        • Budget vs actual tracking
        • Expense patterns and trends
        • Custom date range analysis
        """)
        future_placeholder.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        future_placeholder.setStyleSheet("color: #666; padding: 15px;")
        future_layout.addWidget(future_placeholder)
        layout.addWidget(future_group, 2, 0, 1, 2)  # Span 2 columns
    
    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def on_visualization_mode_changed(self, mode: str):
        """Handle visualization mode changes."""
        if mode == ChartMode.FULL or mode == ChartMode.DETAIL:
            # Hide dashboard, show full visualization
            self.hide_dashboard_controls()
        else:
            # Back to preview mode, show dashboard
            self.show_dashboard_controls()
    
    def hide_dashboard_controls(self):
        """Hide dashboard-level controls when in detailed view."""
        self.refresh_button.setVisible(False)
        self.status_label.setText("Detailed view active")
    
    def show_dashboard_controls(self):
        """Show dashboard-level controls when returning to overview."""
        self.refresh_button.setVisible(True)
        self.status_label.setText("Dashboard ready - Click on any chart to explore in detail")
    
    def refresh_all_data(self):
        """Refresh data for all visualizations."""
        if not self.is_initialized:
            return
            
        self.status_label.setText("Refreshing all data...")
        self.refresh_button.setEnabled(False)
        
        try:
            # Refresh all visualization containers
            for container in self.visualization_containers.values():
                container.refresh_data()
            
            self.status_label.setText("✅ Data refreshed successfully")
            
            # Reset status after delay
            QTimer.singleShot(3000, lambda: self.status_label.setText("Dashboard ready - Click on any chart to explore in detail"))
            
        except Exception as e:
            self.show_error(f"Error refreshing data: {e}")
        finally:
            self.refresh_button.setEnabled(True)
    
    def show_error(self, message: str):
        """Show error message."""
        self.status_label.setText(f"❌ {message}")
        QMessageBox.warning(self, "Dashboard Error", message)
    
    def update_services(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        """Update services after authentication."""
        if not self.is_initialized:
            self.initialize_with_services(sheets_service, spreadsheet_id)
