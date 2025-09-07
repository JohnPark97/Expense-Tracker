"""
Visualization Container
Manages progressive disclosure pattern for visualizations (preview -> full -> detail).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QStackedWidget, QScrollArea, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from typing import Dict, Any, List, Optional

from services.analytics_service import AnalyticsService
from ui.components.base_chart import BaseChart, ChartMode, LoadingChart, EmptyChart
from ui.components.monthly_spending_chart import MonthlySpendingChart, MonthlyTrendChart


class VisualizationContainer(QWidget):
    """Container that manages different visualization modes and transitions."""
    
    # Signals
    mode_changed = Signal(str)  # Emitted when visualization mode changes
    detail_requested = Signal(dict)  # Emitted when detail view is requested
    
    def __init__(self, 
                 analytics_service: AnalyticsService,
                 visualization_type: str = "monthly_spending",
                 initial_mode: str = ChartMode.PREVIEW):
        super().__init__()
        
        self.analytics_service = analytics_service
        self.visualization_type = visualization_type
        self.current_mode = initial_mode
        self.charts = {}  # Store charts by mode
        
        self.setup_ui()
        self.setup_styling()
        self.load_initial_chart()
    
    def setup_ui(self):
        """Setup the container UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Navigation breadcrumb (for full/detail modes)
        self.nav_widget = QWidget()
        nav_layout = QHBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        self.back_button = QPushButton("← Back to Overview")
        self.back_button.clicked.connect(self.go_back_to_preview)
        self.back_button.setVisible(False)
        nav_layout.addWidget(self.back_button)
        
        self.breadcrumb_label = QLabel("")
        self.breadcrumb_label.setStyleSheet("color: #666; font-style: italic;")
        nav_layout.addWidget(self.breadcrumb_label)
        nav_layout.addStretch()
        
        layout.addWidget(self.nav_widget)
        
        # Stacked widget for different modes
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Mode-specific containers
        self.preview_container = self.create_preview_container()
        self.full_container = self.create_full_container()
        self.detail_container = self.create_detail_container()
        
        self.stack.addWidget(self.preview_container)
        self.stack.addWidget(self.full_container)
        self.stack.addWidget(self.detail_container)
    
    def create_preview_container(self) -> QWidget:
        """Create container for preview mode."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Preview chart will be added dynamically
        self.preview_chart_area = QWidget()
        self.preview_chart_area.setMinimumSize(320, 240)
        layout.addWidget(self.preview_chart_area)
        
        return container
    
    def create_full_container(self) -> QWidget:
        """Create container for full view mode."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Title for full view
        title_label = QLabel("Monthly Spending Analysis")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Scrollable area for multiple charts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Grid layout for multiple charts
        scroll_widget = QWidget()
        self.full_grid_layout = QGridLayout(scroll_widget)
        self.full_grid_layout.setSpacing(15)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        return container
    
    def create_detail_container(self) -> QWidget:
        """Create container for detail view mode."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Detail title (will be set dynamically)
        self.detail_title = QLabel("")
        detail_font = QFont()
        detail_font.setPointSize(16)
        detail_font.setBold(True)
        self.detail_title.setFont(detail_font)
        layout.addWidget(self.detail_title)
        
        # Detail content area
        self.detail_content = QWidget()
        detail_layout = QVBoxLayout(self.detail_content)
        
        # Summary stats
        stats_group = QGroupBox("Summary")
        self.stats_layout = QVBoxLayout(stats_group)
        detail_layout.addWidget(stats_group)
        
        # Detailed charts
        charts_group = QGroupBox("Breakdown")
        self.detail_charts_layout = QVBoxLayout(charts_group)
        detail_layout.addWidget(charts_group)
        
        layout.addWidget(self.detail_content)
        
        return container
    
    def setup_styling(self):
        """Setup container styling."""
        self.setStyleSheet("""
            VisualizationContainer {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QGroupBox {
                font-weight: bold;
                padding-top: 10px;
                margin-top: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def load_initial_chart(self):
        """Load the initial chart based on visualization type and mode."""
        # Show loading state first
        self.show_loading()
        
        # Load chart asynchronously to prevent UI blocking
        QTimer.singleShot(100, self._load_chart_async)
    
    def _load_chart_async(self):
        """Asynchronously load chart data."""
        try:
            chart = self.create_chart(self.current_mode)
            if chart:
                self.add_chart_to_container(chart, self.current_mode)
                self.set_current_mode(self.current_mode)
            else:
                self.show_empty_state()
                
        except Exception as e:
            print(f"Error loading chart: {e}")
            self.show_empty_state()
    
    def show_loading(self):
        """Show loading state."""
        loading_chart = LoadingChart("Loading Analytics...", self.current_mode)
        self.add_chart_to_container(loading_chart, ChartMode.PREVIEW)
    
    def show_empty_state(self):
        """Show empty state when no data available."""
        empty_chart = EmptyChart("No Data", "Add some expenses to see analytics", self.current_mode)
        self.add_chart_to_container(empty_chart, self.current_mode)
    
    def create_chart(self, mode: str) -> Optional[BaseChart]:
        """Create chart instance based on type and mode."""
        if self.visualization_type == "monthly_spending":
            chart = MonthlySpendingChart(self.analytics_service, mode)
        elif self.visualization_type == "monthly_trend":
            chart = MonthlyTrendChart(self.analytics_service, mode)
        else:
            return None
        
        # Connect chart signals
        chart.clicked.connect(self.on_chart_clicked)
        chart.detail_requested.connect(self.on_detail_requested)
        
        return chart
    
    def add_chart_to_container(self, chart: BaseChart, mode: str):
        """Add chart to appropriate container based on mode."""
        # Store chart reference
        self.charts[mode] = chart
        
        if mode == ChartMode.PREVIEW:
            # Clear and add to preview container
            layout = self.preview_chart_area.layout()
            if layout is None:
                layout = QVBoxLayout(self.preview_chart_area)
            else:
                self.clear_layout(layout)
            layout.addWidget(chart)
            
        elif mode == ChartMode.FULL:
            # Add to full view grid (support multiple charts)
            row = self.full_grid_layout.rowCount()
            self.full_grid_layout.addWidget(chart, row, 0)
            
        elif mode == ChartMode.DETAIL:
            # Add to detail container
            self.detail_charts_layout.addWidget(chart)
    
    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def set_current_mode(self, mode: str):
        """Set the current visualization mode."""
        self.current_mode = mode
        
        # Update stack
        if mode == ChartMode.PREVIEW:
            self.stack.setCurrentWidget(self.preview_container)
            self.back_button.setVisible(False)
        elif mode == ChartMode.FULL:
            self.stack.setCurrentWidget(self.full_container)
            self.back_button.setVisible(True)
            self.breadcrumb_label.setText("All Monthly Data")
        elif mode == ChartMode.DETAIL:
            self.stack.setCurrentWidget(self.detail_container)
            self.back_button.setVisible(True)
        
        self.mode_changed.emit(mode)
    
    def on_chart_clicked(self, action: str):
        """Handle chart click events."""
        if action == "full" and self.current_mode == ChartMode.PREVIEW:
            self.transition_to_full_view()
        elif action == "detail" and self.current_mode == ChartMode.FULL:
            self.transition_to_detail_view()
        elif action == "expand":
            self.transition_to_full_view()
    
    def on_detail_requested(self, detail_data: Dict[str, Any]):
        """Handle detail view requests."""
        self.show_detail_view(detail_data)
    
    def transition_to_full_view(self):
        """Transition from preview to full view."""
        # Clear existing full view charts
        self.clear_layout(self.full_grid_layout)
        
        # Create enhanced charts for full view
        try:
            # Main spending chart
            main_chart = self.create_chart(ChartMode.FULL)
            if main_chart:
                self.full_grid_layout.addWidget(main_chart, 0, 0)
            
            # Trend chart
            trend_chart = MonthlyTrendChart(self.analytics_service, ChartMode.FULL)
            trend_chart.clicked.connect(self.on_chart_clicked)
            self.full_grid_layout.addWidget(trend_chart, 1, 0)
            
        except Exception as e:
            print(f"Error creating full view charts: {e}")
        
        self.set_current_mode(ChartMode.FULL)
    
    def transition_to_detail_view(self, detail_data: Optional[Dict] = None):
        """Transition to detail view mode."""
        self.show_detail_view(detail_data)
    
    def show_detail_view(self, detail_data: Optional[Dict[str, Any]]):
        """Show detailed view for specific data."""
        if detail_data:
            # Set detail title
            if detail_data.get('type') == 'monthly_detail':
                month = detail_data.get('month', 'Unknown Month')
                self.detail_title.setText(f"Detailed View: {month}")
                self.breadcrumb_label.setText(f"All Monthly Data > {month}")
                
                # Update stats
                self.update_detail_stats(detail_data)
                
                # Create detail charts
                self.create_detail_charts(detail_data)
        
        self.set_current_mode(ChartMode.DETAIL)
    
    def update_detail_stats(self, detail_data: Dict[str, Any]):
        """Update detail statistics display."""
        # Clear existing stats
        self.clear_layout(self.stats_layout)
        
        # Create stat labels
        stats_info = [
            ("Total Spent:", f"${detail_data.get('amount', 0):.2f}"),
            ("Number of Expenses:", str(detail_data.get('expenses', 0))),
            ("Average per Expense:", f"${(detail_data.get('amount', 0) / max(detail_data.get('expenses', 1), 1)):.2f}")
        ]
        
        if detail_data.get('top_expense'):
            top_exp = detail_data['top_expense']
            stats_info.append(("Largest Expense:", f"${top_exp.get('amount', 0):.2f} - {top_exp.get('description', 'N/A')}"))
        
        for label_text, value_text in stats_info:
            stat_widget = QWidget()
            stat_layout = QHBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            value = QLabel(value_text)
            
            stat_layout.addWidget(label)
            stat_layout.addStretch()
            stat_layout.addWidget(value)
            
            self.stats_layout.addWidget(stat_widget)
    
    def create_detail_charts(self, detail_data: Dict[str, Any]):
        """Create detailed charts for the selected data."""
        # Clear existing detail charts
        self.clear_layout(self.detail_charts_layout)
        
        # For now, show a placeholder - we'll implement category breakdown later
        placeholder = QLabel("Category breakdown and detailed analytics will be shown here")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666; font-style: italic; padding: 40px;")
        self.detail_charts_layout.addWidget(placeholder)
    
    def go_back_to_preview(self):
        """Return to preview mode."""
        self.set_current_mode(ChartMode.PREVIEW)
    
    def refresh_data(self):
        """Refresh all chart data."""
        # Reload chart in current mode
        chart = self.charts.get(self.current_mode)
        if chart and hasattr(chart, 'load_data'):
            chart.load_data()
        
        # Clear other mode caches to ensure fresh data on next view
        other_modes = [mode for mode in self.charts.keys() if mode != self.current_mode]
        for mode in other_modes:
            if mode in self.charts:
                del self.charts[mode]
