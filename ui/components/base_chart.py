"""
Base Chart Component
Provides common chart functionality and styling for all visualizations.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPixmap
from typing import Dict, List, Any, Optional

from services.analytics_service import AnalyticsService


class ChartMode:
    """Chart display modes."""
    PREVIEW = "preview"      # Small preview version
    FULL = "full"           # Full-size interactive version  
    DETAIL = "detail"       # Detailed drill-down version


class BaseChart(QWidget):
    """Base class for all chart components."""
    
    # Signals
    clicked = Signal(str)  # Emitted when chart is clicked (with mode info)
    detail_requested = Signal(dict)  # Emitted when detail view is requested
    
    def __init__(self, 
                 analytics_service: AnalyticsService,
                 title: str = "Chart",
                 mode: str = ChartMode.PREVIEW):
        super().__init__()
        
        self.analytics_service = analytics_service
        self.title = title
        self.mode = mode
        self.data = None
        
        # Chart styling
        self.colors = {
            'primary': QColor('#2196F3'),
            'secondary': QColor('#FF9800'), 
            'success': QColor('#4CAF50'),
            'warning': QColor('#FF5722'),
            'info': QColor('#00BCD4'),
            'background': QColor('#FFFFFF'),
            'text': QColor('#333333'),
            'border': QColor('#E0E0E0')
        }
        
        # Size configurations by mode
        self.size_config = {
            ChartMode.PREVIEW: QSize(300, 200),
            ChartMode.FULL: QSize(600, 400),
            ChartMode.DETAIL: QSize(800, 600)
        }
        
        self.setup_ui()
        self.setup_styling()
    
    def setup_ui(self):
        """Setup the base UI structure."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with title and actions
        header_layout = QHBoxLayout()
        
        # Title
        self.title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setPointSize(14 if self.mode == ChartMode.PREVIEW else 16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Action buttons (different per mode)
        if self.mode == ChartMode.PREVIEW:
            self.expand_button = QPushButton("📊 View All")
            self.expand_button.clicked.connect(self.request_full_view)
            header_layout.addWidget(self.expand_button)
        elif self.mode == ChartMode.FULL:
            self.detail_button = QPushButton("🔍 Details")
            self.detail_button.clicked.connect(self.request_detail_view)
            header_layout.addWidget(self.detail_button)
        
        layout.addLayout(header_layout)
        
        # Chart area
        self.chart_widget = QWidget()
        self.chart_widget.setMinimumSize(self.size_config[self.mode])
        self.chart_widget.paintEvent = self.paint_chart
        self.chart_widget.mousePressEvent = self.on_chart_click
        layout.addWidget(self.chart_widget)
        
        # Footer with summary info
        if self.mode != ChartMode.PREVIEW:
            self.footer_label = QLabel("")
            self.footer_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(self.footer_label)
    
    def setup_styling(self):
        """Setup chart styling based on mode."""
        base_style = """
            BaseChart {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """
        
        if self.mode == ChartMode.PREVIEW:
            style = base_style + """
                BaseChart {
                    max-width: 320px;
                    max-height: 240px;
                }
                BaseChart:hover {
                    border-color: #2196f3;
                    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
                }
            """
        else:
            style = base_style + """
                BaseChart {
                    min-width: 500px;
                    min-height: 350px;
                }
            """
        
        self.setStyleSheet(style)
    
    def set_data(self, data: Any):
        """Set chart data and trigger refresh."""
        self.data = data
        self.refresh_chart()
    
    def refresh_chart(self):
        """Refresh chart display."""
        if self.data is not None:
            self.update_footer()
            self.chart_widget.update()
    
    def update_footer(self):
        """Update footer text with summary info."""
        if hasattr(self, 'footer_label') and self.data:
            footer_text = self.get_footer_text()
            self.footer_label.setText(footer_text)
    
    def paint_chart(self, event):
        """Paint the chart. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement paint_chart method")
    
    def get_footer_text(self) -> str:
        """Get footer summary text. Must be implemented by subclasses."""
        return "Base chart - override get_footer_text in subclass"
    
    def on_chart_click(self, event):
        """Handle chart click events."""
        if self.mode == ChartMode.PREVIEW:
            self.clicked.emit("expand")
        elif self.mode == ChartMode.FULL:
            # Determine what was clicked and emit detail request
            click_data = self.get_click_data(event.pos())
            if click_data:
                self.detail_requested.emit(click_data)
    
    def get_click_data(self, pos) -> Optional[Dict]:
        """Get data for clicked position. Override in subclasses."""
        return None
    
    def request_full_view(self):
        """Request transition to full view."""
        self.clicked.emit("full")
    
    def request_detail_view(self):
        """Request transition to detail view."""
        self.clicked.emit("detail")
    
    def set_mode(self, mode: str):
        """Change chart mode and rebuild UI."""
        if mode != self.mode:
            self.mode = mode
            # Clear and rebuild
            for i in reversed(range(self.layout().count())):
                child = self.layout().itemAt(i).widget()
                if child:
                    child.deleteLater()
            self.setup_ui()
            self.setup_styling()
            self.refresh_chart()


class LoadingChart(BaseChart):
    """Loading placeholder chart."""
    
    def __init__(self, title: str = "Loading...", mode: str = ChartMode.PREVIEW):
        super().__init__(None, title, mode)
        self.animation_step = 0
        
        # Simple animation timer
        from PySide6.QtCore import QTimer
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)  # 100ms intervals
    
    def paint_chart(self, event):
        """Paint loading animation."""
        painter = QPainter(self.chart_widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw loading spinner
        rect = self.chart_widget.rect()
        center_x = rect.width() // 2
        center_y = rect.height() // 2
        
        painter.setPen(QPen(self.colors['primary'], 3))
        
        # Draw rotating arc
        start_angle = (self.animation_step * 10) % 360
        painter.drawArc(center_x - 20, center_y - 20, 40, 40, start_angle, 120)
        
        # Draw loading text
        painter.setPen(QPen(self.colors['text']))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Loading data...")
    
    def get_footer_text(self) -> str:
        return "Please wait while data is being loaded..."
    
    def animate(self):
        """Update animation."""
        self.animation_step += 1
        self.chart_widget.update()
        
        # Stop after reasonable time to prevent infinite loading
        if self.animation_step > 100:
            self.timer.stop()


class EmptyChart(BaseChart):
    """Empty state chart."""
    
    def __init__(self, title: str = "No Data", message: str = "No data available", mode: str = ChartMode.PREVIEW):
        self.message = message
        super().__init__(None, title, mode)
    
    def paint_chart(self, event):
        """Paint empty state."""
        painter = QPainter(self.chart_widget)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.chart_widget.rect()
        
        # Draw empty state icon and message
        painter.setPen(QPen(self.colors['border']))
        painter.setBrush(QBrush(self.colors['border']))
        
        # Simple empty icon (circle with line through it)
        center_x = rect.width() // 2
        center_y = rect.height() // 2 - 20
        
        painter.drawEllipse(center_x - 25, center_y - 25, 50, 50)
        painter.setPen(QPen(QColor('#999'), 2))
        painter.drawLine(center_x - 15, center_y - 15, center_x + 15, center_y + 15)
        
        # Draw message
        painter.setPen(QPen(self.colors['text']))
        text_rect = rect.adjusted(10, center_y + 40, -10, -10)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
    
    def get_footer_text(self) -> str:
        return "Add some expenses to see visualizations"
