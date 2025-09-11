"""
Monthly Detail Grid View
Shows all available months in a 3-column grid layout for detailed visualization.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QScrollArea, QFrame, QGroupBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from services.analytics_service import AnalyticsService
from ui.components.monthly_spending_chart import MonthlySpendingChart, MonthlyTrendChart
from ui.components.base_chart import ChartMode


class MonthlyDetailGrid(QWidget):
    """Grid view showing detailed monthly spending charts."""
    
    # Signals
    back_to_overview = Signal()  # Request to go back to overview
    
    def __init__(self, analytics_service: AnalyticsService, parent=None):
        super().__init__(parent)
        self.analytics_service = analytics_service
        self.month_charts = {}  # Store chart widgets
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the detail grid UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with back button
        header_layout = QHBoxLayout()
        
        # Back button
        back_button = QPushButton("← Back to Overview")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        back_button.clicked.connect(self.back_to_overview.emit)
        header_layout.addWidget(back_button)
        
        # Title
        title = QLabel("Monthly Spending Details")
        title.setFont(QFont("", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title, 1)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Scrollable area for grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Grid container
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(15)
        
        scroll_area.setWidget(grid_widget)
        layout.addWidget(scroll_area, 1)
        
    def load_all_months(self):
        """Load charts for all available months in a 3-column grid."""
        print("🔄 Loading all months for detail grid view...")
        
        # Clear existing charts
        self.clear_grid()
        
        # Get all available months
        available_months = self.analytics_service.get_available_months()
        print(f"📅 Found {len(available_months)} available months: {available_months}")
        
        if not available_months:
            # Show empty state
            empty_label = QLabel("No monthly data available")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #666; font-size: 16px; padding: 40px;")
            self.grid_layout.addWidget(empty_label, 0, 0, 1, 3)
            return
        
        # Create charts in grid (3 columns)
        for i, month_name in enumerate(available_months):
            row = i // 3
            col = i % 3
            
            print(f"📊 Creating chart for {month_name} at position ({row}, {col})")
            
            # Create month chart container
            month_container = self.create_month_container(month_name)
            self.grid_layout.addWidget(month_container, row, col)
            
        print(f"✅ Grid loaded with {len(available_months)} month charts")
        
    def create_month_container(self, month_name: str) -> QWidget:
        """Create a container for a single month's chart."""
        container = QGroupBox(month_name)
        container.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333;
            }
        """)
        
        layout = QVBoxLayout(container)
        
        # Create bar chart for this month
        bar_chart = MonthlySpendingChart(
            self.analytics_service,
            mode=ChartMode.DETAIL,
            months_to_show=1
        )
        
        # Load specific month data
        bar_chart.spending_data = [self.analytics_service.get_monthly_spending(month_name)]
        bar_chart.spending_data = [data for data in bar_chart.spending_data if data is not None]
        bar_chart.set_data(bar_chart.spending_data)
        
        # Set fixed size for grid consistency
        bar_chart.setFixedSize(300, 200)
        layout.addWidget(bar_chart)
        
        # Add summary stats
        if bar_chart.spending_data:
            data = bar_chart.spending_data[0]
            if data and data.total_amount > 0:
                stats_label = QLabel(f"${data.total_amount:.2f} • {data.expense_count} expenses")
                stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stats_label.setStyleSheet("color: #666; font-size: 12px; margin: 5px;")
                layout.addWidget(stats_label)
            else:
                stats_label = QLabel("No expenses")
                stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stats_label.setStyleSheet("color: #999; font-size: 12px; margin: 5px;")
                layout.addWidget(stats_label)
        
        # Store reference
        self.month_charts[month_name] = bar_chart
        
        return container
        
    def clear_grid(self):
        """Clear all charts from the grid."""
        # Clear grid layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Clear references
        self.month_charts.clear()
        
    def refresh_data(self):
        """Refresh all month data."""
        print("🔄 Refreshing detail grid data...")
        self.load_all_months()
