"""
Chart Widget for Data Visualization
PySide6 widget with matplotlib integration for creating various chart types.
"""

import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt backend for matplotlib

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QLabel, QGroupBox, QPushButton, QCheckBox,
    QSpinBox, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import seaborn as sns
import numpy as np
from typing import Optional, List, Tuple
import warnings

# Suppress matplotlib warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


class MplCanvas(FigureCanvas):
    """Matplotlib canvas widget for embedding plots in PySide6."""
    
    def __init__(self, width=12, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        
        # Configure the figure
        self.fig.patch.set_facecolor('white')
        self.setParent(None)


class ChartWidget(QWidget):
    """Widget for creating and displaying various chart types."""
    
    def __init__(self):
        super().__init__()
        self.df = pd.DataFrame()
        self.canvas = None
        self.setup_ui()
        self.setup_matplotlib_style()
    
    def setup_matplotlib_style(self):
        """Configure matplotlib and seaborn styles."""
        # Set the style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Configure matplotlib
        matplotlib.rcParams.update({
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'figure.titlesize': 14
        })
    
    def setup_ui(self):
        """Setup the chart widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Controls section
        controls_group = QGroupBox("Chart Configuration")
        controls_layout = QVBoxLayout()
        controls_group.setLayout(controls_layout)
        
        # Chart type selection
        chart_type_layout = QHBoxLayout()
        chart_type_layout.addWidget(QLabel("Chart Type:"))
        
        self.chart_selector = QComboBox()
        self.chart_selector.addItems([
            "Bar Chart",
            "Horizontal Bar Chart", 
            "Line Chart",
            "Pie Chart",
            "Histogram",
            "Scatter Plot",
            "Box Plot",
            "Area Chart",
            "Heatmap"
        ])
        self.chart_selector.currentTextChanged.connect(self.update_chart)
        chart_type_layout.addWidget(self.chart_selector)
        
        # Column selection
        self.column_selectors_layout = QHBoxLayout()
        self.x_column_selector = QComboBox()
        self.y_column_selector = QComboBox()
        
        self.column_selectors_layout.addWidget(QLabel("X Column:"))
        self.column_selectors_layout.addWidget(self.x_column_selector)
        self.column_selectors_layout.addWidget(QLabel("Y Column:"))
        self.column_selectors_layout.addWidget(self.y_column_selector)
        
        self.x_column_selector.currentTextChanged.connect(self.update_chart)
        self.y_column_selector.currentTextChanged.connect(self.update_chart)
        
        # Options
        options_layout = QHBoxLayout()
        
        self.show_grid = QCheckBox("Show Grid")
        self.show_grid.setChecked(True)
        self.show_grid.stateChanged.connect(self.update_chart)
        options_layout.addWidget(self.show_grid)
        
        self.max_items = QSpinBox()
        self.max_items.setMinimum(5)
        self.max_items.setMaximum(100)
        self.max_items.setValue(20)
        self.max_items.valueChanged.connect(self.update_chart)
        options_layout.addWidget(QLabel("Max Items:"))
        options_layout.addWidget(self.max_items)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Chart")
        refresh_btn.clicked.connect(self.update_chart)
        options_layout.addWidget(refresh_btn)
        
        # Add all control layouts
        controls_layout.addLayout(chart_type_layout)
        controls_layout.addLayout(self.column_selectors_layout)
        controls_layout.addLayout(options_layout)
        
        layout.addWidget(controls_group)
        
        # Chart area
        self.chart_area = QScrollArea()
        self.chart_area.setWidgetResizable(True)
        self.chart_area.setMinimumHeight(400)
        layout.addWidget(self.chart_area)
        
        # Initialize empty chart
        self.create_empty_chart()
    
    def create_empty_chart(self):
        """Create an empty chart placeholder."""
        self.canvas = MplCanvas(width=12, height=8)
        ax = self.canvas.fig.add_subplot(111)
        ax.text(0.5, 0.5, '📊 Load data to create charts', 
                transform=ax.transAxes, ha='center', va='center',
                fontsize=16, alpha=0.7)
        ax.set_xticks([])
        ax.set_yticks([])
        self.chart_area.setWidget(self.canvas)
        self.canvas.draw()
    
    def update_data(self, df: pd.DataFrame):
        """Update the data and refresh available options."""
        self.df = df.copy()
        
        if df.empty:
            self.create_empty_chart()
            return
        
        # Update column selectors
        columns = list(df.columns)
        
        self.x_column_selector.clear()
        self.y_column_selector.clear()
        
        self.x_column_selector.addItems(["(Auto)"] + columns)
        self.y_column_selector.addItems(["(Auto)"] + columns)
        
        # Try to auto-select reasonable defaults
        if len(columns) >= 1:
            self.x_column_selector.setCurrentText(columns[0])
        if len(columns) >= 2:
            self.y_column_selector.setCurrentText(columns[1])
        
        # Update chart
        self.update_chart()
    
    def get_selected_columns(self) -> Tuple[Optional[str], Optional[str]]:
        """Get currently selected X and Y columns."""
        x_col = self.x_column_selector.currentText()
        y_col = self.y_column_selector.currentText()
        
        if x_col == "(Auto)" or not x_col:
            x_col = None
        if y_col == "(Auto)" or not y_col:
            y_col = None
            
        return x_col, y_col
    
    def prepare_data_for_chart(self) -> Tuple[pd.DataFrame, str, str]:
        """Prepare data for charting and return processed data with column names."""
        if self.df.empty:
            return pd.DataFrame(), "", ""
        
        x_col, y_col = self.get_selected_columns()
        chart_type = self.chart_selector.currentText()
        
        # Auto-select columns based on chart type if not specified
        if not x_col and not y_col:
            if chart_type in ["Pie Chart", "Histogram"]:
                # Use first column for single-column charts
                x_col = self.df.columns[0] if len(self.df.columns) > 0 else None
            else:
                # Use first two columns for two-column charts
                x_col = self.df.columns[0] if len(self.df.columns) > 0 else None
                y_col = self.df.columns[1] if len(self.df.columns) > 1 else None
        
        # Limit data if needed
        max_items = self.max_items.value()
        limited_df = self.df.head(max_items).copy()
        
        return limited_df, x_col or "", y_col or ""
    
    def update_chart(self):
        """Update the chart based on current settings."""
        if self.df.empty:
            self.create_empty_chart()
            return
        
        try:
            # Clear the previous chart
            if self.canvas:
                self.canvas.fig.clear()
            else:
                self.canvas = MplCanvas(width=12, height=8)
                self.chart_area.setWidget(self.canvas)
            
            # Get prepared data
            data, x_col, y_col = self.prepare_data_for_chart()
            chart_type = self.chart_selector.currentText()
            
            if data.empty or not x_col:
                ax = self.canvas.fig.add_subplot(111)
                ax.text(0.5, 0.5, '⚠️ No data available for selected columns', 
                        transform=ax.transAxes, ha='center', va='center',
                        fontsize=14, alpha=0.7)
                ax.set_xticks([])
                ax.set_yticks([])
                self.canvas.draw()
                return
            
            # Create the appropriate chart
            ax = self.canvas.fig.add_subplot(111)
            
            if chart_type == "Bar Chart":
                self.create_bar_chart(ax, data, x_col, y_col)
            elif chart_type == "Horizontal Bar Chart":
                self.create_horizontal_bar_chart(ax, data, x_col, y_col)
            elif chart_type == "Line Chart":
                self.create_line_chart(ax, data, x_col, y_col)
            elif chart_type == "Pie Chart":
                self.create_pie_chart(ax, data, x_col)
            elif chart_type == "Histogram":
                self.create_histogram(ax, data, x_col)
            elif chart_type == "Scatter Plot":
                self.create_scatter_plot(ax, data, x_col, y_col)
            elif chart_type == "Box Plot":
                self.create_box_plot(ax, data, x_col, y_col)
            elif chart_type == "Area Chart":
                self.create_area_chart(ax, data, x_col, y_col)
            elif chart_type == "Heatmap":
                self.create_heatmap(ax, data)
            
            # Apply common formatting
            if self.show_grid.isChecked():
                ax.grid(True, alpha=0.3)
            
            # Adjust layout
            self.canvas.fig.tight_layout()
            
            # Refresh the canvas
            self.canvas.draw()
            
        except Exception as e:
            self.show_error_chart(f"Error creating chart: {str(e)}")
    
    def show_error_chart(self, error_message: str):
        """Display an error message on the chart."""
        if not self.canvas:
            self.canvas = MplCanvas(width=12, height=8)
            self.chart_area.setWidget(self.canvas)
        
        self.canvas.fig.clear()
        ax = self.canvas.fig.add_subplot(111)
        ax.text(0.5, 0.5, f'❌ {error_message}', 
                transform=ax.transAxes, ha='center', va='center',
                fontsize=12, alpha=0.7, wrap=True)
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas.draw()
    
    def create_bar_chart(self, ax, data: pd.DataFrame, x_col: str, y_col: str):
        """Create a bar chart."""
        if not y_col and x_col:
            # Use value counts for categorical data
            value_counts = data[x_col].value_counts().head(self.max_items.value())
            ax.bar(range(len(value_counts)), value_counts.values, color='skyblue')
            ax.set_xticks(range(len(value_counts)))
            ax.set_xticklabels(value_counts.index, rotation=45, ha='right')
            ax.set_ylabel('Count')
        elif x_col and y_col:
            # Convert y_col to numeric if possible
            y_data = pd.to_numeric(data[y_col], errors='coerce').fillna(0)
            ax.bar(data[x_col], y_data, color='lightcoral')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
        
        ax.set_title(f'Bar Chart: {x_col}' + (f' vs {y_col}' if y_col else ''))
    
    def create_horizontal_bar_chart(self, ax, data: pd.DataFrame, x_col: str, y_col: str):
        """Create a horizontal bar chart."""
        if not y_col and x_col:
            value_counts = data[x_col].value_counts().head(self.max_items.value())
            ax.barh(range(len(value_counts)), value_counts.values, color='lightgreen')
            ax.set_yticks(range(len(value_counts)))
            ax.set_yticklabels(value_counts.index)
            ax.set_xlabel('Count')
        elif x_col and y_col:
            y_data = pd.to_numeric(data[y_col], errors='coerce').fillna(0)
            ax.barh(data[x_col], y_data, color='orange')
            ax.set_ylabel(x_col)
            ax.set_xlabel(y_col)
        
        ax.set_title(f'Horizontal Bar Chart: {x_col}' + (f' vs {y_col}' if y_col else ''))
    
    def create_line_chart(self, ax, data: pd.DataFrame, x_col: str, y_col: str):
        """Create a line chart."""
        if x_col and y_col:
            y_data = pd.to_numeric(data[y_col], errors='coerce')
            ax.plot(data[x_col], y_data, marker='o', linewidth=2, markersize=4)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(f'Line Chart: {x_col} vs {y_col}')
    
    def create_pie_chart(self, ax, data: pd.DataFrame, x_col: str):
        """Create a pie chart."""
        if x_col:
            value_counts = data[x_col].value_counts().head(10)  # Limit to top 10
            colors = plt.cm.Set3(np.linspace(0, 1, len(value_counts)))
            wedges, texts, autotexts = ax.pie(value_counts.values, labels=value_counts.index, 
                                            autopct='%1.1f%%', colors=colors, startangle=90)
            ax.set_title(f'Pie Chart: {x_col}')
    
    def create_histogram(self, ax, data: pd.DataFrame, x_col: str):
        """Create a histogram."""
        if x_col:
            numeric_data = pd.to_numeric(data[x_col], errors='coerce').dropna()
            if len(numeric_data) > 0:
                ax.hist(numeric_data, bins=min(30, len(numeric_data)//2 + 1), 
                       color='purple', alpha=0.7, edgecolor='black')
                ax.set_xlabel(x_col)
                ax.set_ylabel('Frequency')
                ax.set_title(f'Histogram: {x_col}')
    
    def create_scatter_plot(self, ax, data: pd.DataFrame, x_col: str, y_col: str):
        """Create a scatter plot."""
        if x_col and y_col:
            x_data = pd.to_numeric(data[x_col], errors='coerce')
            y_data = pd.to_numeric(data[y_col], errors='coerce')
            
            # Remove rows where either value is NaN
            valid_mask = ~(x_data.isna() | y_data.isna())
            x_data = x_data[valid_mask]
            y_data = y_data[valid_mask]
            
            if len(x_data) > 0:
                ax.scatter(x_data, y_data, alpha=0.6, color='red')
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                ax.set_title(f'Scatter Plot: {x_col} vs {y_col}')
    
    def create_box_plot(self, ax, data: pd.DataFrame, x_col: str, y_col: str):
        """Create a box plot."""
        if x_col and y_col:
            # Group by x_col and plot y_col distributions
            grouped_data = []
            labels = []
            for name, group in data.groupby(x_col):
                y_values = pd.to_numeric(group[y_col], errors='coerce').dropna()
                if len(y_values) > 0:
                    grouped_data.append(y_values)
                    labels.append(name)
            
            if grouped_data:
                ax.boxplot(grouped_data, labels=labels)
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                ax.set_title(f'Box Plot: {y_col} by {x_col}')
        elif x_col:
            # Single column box plot
            numeric_data = pd.to_numeric(data[x_col], errors='coerce').dropna()
            if len(numeric_data) > 0:
                ax.boxplot([numeric_data])
                ax.set_ylabel(x_col)
                ax.set_title(f'Box Plot: {x_col}')
    
    def create_area_chart(self, ax, data: pd.DataFrame, x_col: str, y_col: str):
        """Create an area chart."""
        if x_col and y_col:
            y_data = pd.to_numeric(data[y_col], errors='coerce').fillna(0)
            ax.fill_between(range(len(data)), y_data, alpha=0.7, color='cyan')
            ax.plot(range(len(data)), y_data, color='darkblue', linewidth=2)
            
            # Set x-axis labels
            step = max(1, len(data) // 10)  # Show ~10 labels
            positions = range(0, len(data), step)
            ax.set_xticks(positions)
            ax.set_xticklabels([str(data[x_col].iloc[i]) for i in positions], rotation=45)
            
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(f'Area Chart: {x_col} vs {y_col}')
    
    def create_heatmap(self, ax, data: pd.DataFrame):
        """Create a heatmap of numeric columns."""
        # Select only numeric columns
        numeric_cols = data.select_dtypes(include=[np.number])
        
        if numeric_cols.empty:
            ax.text(0.5, 0.5, 'No numeric data for heatmap', 
                   transform=ax.transAxes, ha='center', va='center')
            return
        
        # Calculate correlation matrix
        corr_matrix = numeric_cols.corr()
        
        # Create heatmap
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                   square=True, ax=ax, cbar_kws={'shrink': 0.8})
        ax.set_title('Correlation Heatmap')
