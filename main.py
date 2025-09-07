#!/usr/bin/env python3
"""
Expense Sheet Visualizer
A PySide6 application for visualizing Google Sheets expense data.

🎨 THEME SETTINGS: Light mode is currently enabled (dark mode disabled).
   To change themes, search for "THEME CONFIGURATION" in this file.
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Expense Sheet Visualizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Personal")
    
    # Set application-wide style
    app.setStyle('Fusion')
    
    # ============================================================================
    # 🎨 THEME CONFIGURATION - EASY TO FIND AND MODIFY
    # ============================================================================
    # Current Setting: LIGHT MODE (Dark Mode Disabled)
    # 
    # To ENABLE DARK MODE in the future:
    # 1. Uncomment the dark mode stylesheet below
    # 2. Comment out the light mode stylesheet
    # 
    # To DISABLE DARK MODE (Current Setting):
    # 1. Keep light mode stylesheet active (as below)
    # 2. Keep dark mode stylesheet commented out
    # ============================================================================
    
    # LIGHT MODE (Currently Active)
    light_theme_stylesheet = """
    QMainWindow {
        background-color: #ffffff;
        color: #000000;
    }
    QWidget {
        background-color: #ffffff;
        color: #000000;
    }
    QTabWidget::pane {
        background-color: #ffffff;
        border: 1px solid #c0c0c0;
    }
    QTabBar::tab {
        background-color: #f0f0f0;
        color: #000000;
        padding: 8px 16px;
        margin-right: 2px;
        border: 1px solid #c0c0c0;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background-color: #ffffff;
        border-bottom: 1px solid #ffffff;
    }
    QTabBar::tab:hover {
        background-color: #e8e8e8;
    }
    QTableWidget {
        background-color: #ffffff;
        alternate-background-color: #f8f9fa;
        gridline-color: #e0e0e0;
        color: #000000;
        selection-background-color: #b3d9ff;
        selection-color: #000000;
        outline: none;
        show-decoration-selected: 0;
    }
    QTableWidget::item {
        color: #000000;
        border: none;
        padding: 4px;
        outline: none;
    }
    QTableWidget::item:selected {
        color: #000000;
        outline: none;
    }
    QTableWidget::item:focus {
        color: #000000;
        border: none;
        outline: none;
    }
    QHeaderView::section {
        background-color: #f0f0f0;
        color: #000000;
        padding: 4px;
        border: 1px solid #c0c0c0;
    }
    QComboBox {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #c0c0c0;
        padding: 2px 6px;
        border-radius: 3px;
    }
    QComboBox:drop-down {
        background-color: #f0f0f0;
        border: none;
    }
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        color: #000000;
        selection-background-color: #b3d9ff;
        selection-color: #000000;
    }
    """
    
    # DARK MODE (Currently Disabled - Uncomment to enable)
    # dark_theme_stylesheet = """
    # QMainWindow {
    #     background-color: #2b2b2b;
    #     color: #ffffff;
    # }
    # QWidget {
    #     background-color: #2b2b2b;
    #     color: #ffffff;
    # }
    # QTabWidget::pane {
    #     background-color: #2b2b2b;
    #     border: 1px solid #555555;
    # }
    # QTabBar::tab {
    #     background-color: #404040;
    #     color: #ffffff;
    #     padding: 8px 16px;
    #     margin-right: 2px;
    #     border: 1px solid #555555;
    #     border-bottom: none;
    # }
    # QTabBar::tab:selected {
    #     background-color: #2b2b2b;
    #     border-bottom: 1px solid #2b2b2b;
    # }
    # QTabBar::tab:hover {
    #     background-color: #505050;
    # }
    # QTableWidget {
    #     background-color: #2b2b2b;
    #     alternate-background-color: #353535;
    #     gridline-color: #555555;
    #     color: #ffffff;
    # }
    # QHeaderView::section {
    #     background-color: #404040;
    #     color: #ffffff;
    #     padding: 4px;
    #     border: 1px solid #555555;
    # }
    # """
    
    # Apply the light theme (dark mode disabled)
    app.setStyleSheet(light_theme_stylesheet)
    
    # ============================================================================
    # 🔧 ADDITIONAL DARK MODE PREVENTION (Currently Active)
    # ============================================================================
    # Force light mode even if system prefers dark mode
    # These lines are active to prevent system dark mode from overriding our theme:
    
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    # app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True) 
    
    # Override system palette to force light colors
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(248, 249, 250))  # Very light gray
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))  # Light gray
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(179, 217, 255))  # Light blue
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    # Comment out the lines above if you want to enable dark mode in the future
    # ============================================================================
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
