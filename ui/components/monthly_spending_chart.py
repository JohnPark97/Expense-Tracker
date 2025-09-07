"""
Monthly Spending Chart Component
Bar chart showing spending amounts over months with progressive detail levels.
"""

from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtCore import QRect, Qt
from typing import List, Dict, Any, Optional
import math

from services.analytics_service import MonthlySpending, AnalyticsService
from ui.components.base_chart import BaseChart, ChartMode


class MonthlySpendingChart(BaseChart):
    """Bar chart for monthly spending visualization."""
    
    def __init__(self, 
                 analytics_service: AnalyticsService, 
                 mode: str = ChartMode.PREVIEW,
                 months_to_show: int = 3):
        self.months_to_show = months_to_show
        self.spending_data: List[MonthlySpending] = []
        self.bar_rects = []  # Store bar rectangles for click detection
        
        title = f"Monthly Spending"
        if mode == ChartMode.PREVIEW:
            title = f"July - September 2025"
        
        super().__init__(analytics_service, title, mode)
        self.load_data()
    
    def load_data(self):
        """Load spending data from analytics service."""
        try:
            if self.mode == ChartMode.PREVIEW:
                # Load specific last 3 months (July, Aug, Sept 2025) for preview
                print(f"🔄 Loading last 3 months data for preview...")
                self.spending_data = self.analytics_service.get_last_three_months_spending()
            else:
                # Load more months for full view
                print(f"🔄 Loading extended months data for full view...")
                self.spending_data = self.analytics_service.get_recent_months_spending(12)
            
            print(f"📈 Chart received {len(self.spending_data)} months of data")
            for i, data in enumerate(self.spending_data):
                print(f"  Month {i+1}: {data.month_name} - ${data.total_amount:.2f} ({data.expense_count} expenses)")
            
            self.set_data(self.spending_data)
            
        except Exception as e:
            print(f"Error loading monthly spending data: {e}")
            import traceback
            traceback.print_exc()
            self.spending_data = []
            self.set_data([])
    
    def paint_chart(self, event):
        """Paint the monthly spending bar chart."""
        if not self.spending_data:
            self._paint_empty_state()
            return
        
        painter = QPainter(self.chart_widget)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            rect = self.chart_widget.rect().adjusted(20, 20, -20, -40)
            self._paint_bars(painter, rect)
            self._paint_axes(painter, rect)
            
        except Exception as e:
            print(f"Error painting chart: {e}")
            # Paint error message
            painter.setPen(QPen(self.colors['text']))
            painter.drawText(self.chart_widget.rect(), Qt.AlignmentFlag.AlignCenter, 
                           f"Chart Error\n{str(e)[:50]}")
        finally:
            if painter.isActive():
                painter.end()
    
    def _paint_empty_state(self):
        """Paint empty state when no data is available."""
        painter = QPainter(self.chart_widget)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            rect = self.chart_widget.rect()
            painter.setPen(QPen(self.colors['text']))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, 
                            "No expense data found\nAdd some expenses to see charts")
        finally:
            if painter.isActive():
                painter.end()
    
    def _paint_no_data_message(self, painter: QPainter, rect: QRect):
        """Paint message when all amounts are zero."""
        painter.setPen(QPen(self.colors['text']))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, 
                        "No spending recorded\nfor selected period")
    
    def _paint_bars(self, painter: QPainter, rect: QRect):
        """Paint the spending bars."""
        if not self.spending_data:
            return
        
        # Calculate bar dimensions
        bar_count = len(self.spending_data)
        if bar_count == 0:
            return
        
        bar_width = max(20, (rect.width() - (bar_count + 1) * 10) // bar_count)
        
        # Calculate max amount and handle zero case
        amounts = [data.total_amount for data in self.spending_data]
        max_amount = max(amounts, default=0)
        
        # If all amounts are zero or negative, show placeholder
        if max_amount <= 0:
            self._paint_no_data_message(painter, rect)
            return
        
        # Reverse data for chronological display (left to right)
        display_data = list(reversed(self.spending_data))
        self.bar_rects = []
        
        # Draw bars
        for i, spending in enumerate(display_data):
            if spending.total_amount <= 0:
                continue
                
            # Calculate bar position and height (with safe division)
            x = rect.left() + 10 + i * (bar_width + 10)
            bar_height = int((spending.total_amount / max(max_amount, 0.01)) * rect.height() * 0.8)
            y = rect.bottom() - bar_height
            
            bar_rect = QRect(x, y, bar_width, bar_height)
            self.bar_rects.append((bar_rect, spending))
            
            # Choose color based on spending trend
            color = self._get_bar_color(spending, i, display_data)
            
            # Draw bar
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(bar_rect)
            
            # Draw amount label on bar (if mode allows)
            if self.mode != ChartMode.PREVIEW or bar_height > 30:
                painter.setPen(QPen(QColor('#FFFFFF')))
                amount_text = self._format_amount(spending.total_amount)
                painter.drawText(bar_rect, Qt.AlignmentFlag.AlignCenter, amount_text)
            
            # Draw month label below bar
            painter.setPen(QPen(self.colors['text']))
            month_text = self._get_month_label(spending)
            label_rect = QRect(x, rect.bottom() + 5, bar_width, 20)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, month_text)
    
    def _paint_axes(self, painter: QPainter, rect: QRect):
        """Paint chart axes and grid lines."""
        painter.setPen(QPen(self.colors['border']))
        
        # X-axis
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        
        # Y-axis
        painter.drawLine(rect.bottomLeft(), rect.topLeft())
        
        # Y-axis labels (amounts)
        if self.spending_data and self.mode != ChartMode.PREVIEW:
            max_amount = max((data.total_amount for data in self.spending_data), default=1)
            if max_amount > 0:  # Only draw labels if we have data
                steps = 4
                for i in range(steps + 1):
                    amount = (max_amount / steps) * i
                    y = rect.bottom() - int((amount / max(max_amount, 0.01)) * rect.height() * 0.8)
                    
                    # Grid line
                    painter.setPen(QPen(self.colors['border'].lighter(130)))
                    painter.drawLine(rect.left(), y, rect.right(), y)
                    
                    # Label
                    painter.setPen(QPen(self.colors['text']))
                    label_text = self._format_amount(amount)
                    painter.drawText(rect.left() - 50, y - 5, 45, 10, 
                                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 
                                   label_text)
    
    def _get_bar_color(self, spending: MonthlySpending, index: int, data_list: List[MonthlySpending]) -> QColor:
        """Get color for a spending bar based on trends."""
        # Default color
        base_color = self.colors['primary']
        
        # Color based on amount relative to others
        if len(data_list) > 1:
            amounts = [d.total_amount for d in data_list]
            avg_amount = sum(amounts) / len(amounts)
            
            if spending.total_amount > avg_amount * 1.2:
                base_color = self.colors['warning']  # High spending
            elif spending.total_amount < avg_amount * 0.8:
                base_color = self.colors['success']  # Low spending
        
        return base_color
    
    def _format_amount(self, amount: float) -> str:
        """Format amount for display."""
        if amount >= 10000:
            return f"${amount/1000:.1f}K"
        elif amount >= 1000:
            return f"${amount/1000:.1f}K"
        else:
            return f"${amount:.0f}"
    
    def _get_month_label(self, spending: MonthlySpending) -> str:
        """Get month label based on chart mode."""
        if self.mode == ChartMode.PREVIEW:
            # Short format for preview
            month_name = spending.month_name.split()[0]  # Just month name
            return month_name[:3]  # First 3 letters
        else:
            # Full format for detailed view
            return spending.month_name
    
    def get_footer_text(self) -> str:
        """Get footer summary text."""
        if not self.spending_data:
            return "No data available"
        
        total_expenses = sum(data.expense_count for data in self.spending_data)
        total_amount = sum(data.total_amount for data in self.spending_data)
        avg_monthly = total_amount / len(self.spending_data) if self.spending_data else 0
        
        if self.mode == ChartMode.PREVIEW:
            return f"${total_amount:.0f} total, ${avg_monthly:.0f} average"
        else:
            return f"Total: ${total_amount:.2f} across {total_expenses} expenses | Monthly Average: ${avg_monthly:.2f}"
    
    def get_click_data(self, pos) -> Optional[Dict]:
        """Get data for clicked bar."""
        for bar_rect, spending in self.bar_rects:
            if bar_rect.contains(pos):
                return {
                    'type': 'monthly_detail',
                    'month': spending.month_name,
                    'amount': spending.total_amount,
                    'expenses': spending.expense_count,
                    'categories': spending.categories,
                    'top_expense': spending.top_expense
                }
        return None
    
    def set_months_to_show(self, months: int):
        """Update number of months to display."""
        self.months_to_show = months
        self.load_data()


class MonthlyTrendChart(MonthlySpendingChart):
    """Line chart variant for trend visualization."""
    
    def __init__(self, analytics_service: AnalyticsService, mode: str = ChartMode.PREVIEW):
        super().__init__(analytics_service, mode, months_to_show=6)
        self.title = "Spending Trend"
    
    def _paint_bars(self, painter: QPainter, rect: QRect):
        """Override to paint trend line instead of bars."""
        if len(self.spending_data) < 2:
            return
        
        # Calculate points for trend line
        display_data = list(reversed(self.spending_data))
        amounts = [data.total_amount for data in display_data]
        max_amount = max(amounts, default=0)
        
        # If all amounts are zero, show no data message
        if max_amount <= 0:
            self._paint_no_data_message(painter, rect)
            return
        
        points = []
        for i, spending in enumerate(display_data):
            x = rect.left() + 20 + i * ((rect.width() - 40) / max(1, len(display_data) - 1))
            y = rect.bottom() - int((spending.total_amount / max(max_amount, 0.01)) * rect.height() * 0.8)
            points.append((x, y, spending))
        
        # Draw trend line
        painter.setPen(QPen(self.colors['primary'], 3))
        for i in range(len(points) - 1):
            painter.drawLine(int(points[i][0]), int(points[i][1]), 
                           int(points[i+1][0]), int(points[i+1][1]))
        
        # Draw data points
        painter.setBrush(QBrush(self.colors['primary']))
        for x, y, spending in points:
            painter.drawEllipse(int(x-4), int(y-4), 8, 8)
            
            # Draw amount label
            if self.mode != ChartMode.PREVIEW:
                painter.setPen(QPen(self.colors['text']))
                amount_text = self._format_amount(spending.total_amount)
                painter.drawText(int(x-20), int(y-15), 40, 12, 
                               Qt.AlignmentFlag.AlignCenter, amount_text)
        
        # Store points for click detection
        self.bar_rects = [(QRect(int(x-10), int(y-10), 20, 20), spending) for x, y, spending in points]
