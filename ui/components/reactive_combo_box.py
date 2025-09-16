"""
Reactive ComboBox Component
A dropdown that automatically updates when underlying data changes.
"""

from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import QObject, Signal, QTimer
from typing import List, Callable, Optional
from enum import Enum


class DataSourceType(Enum):
    """Types of data sources for reactive dropdowns."""
    ACCOUNTS = "accounts"
    CATEGORIES = "categories"
    PAYMENT_METHODS = "payment_methods"


class DataChangeNotifier(QObject):
    """Global notifier for data changes across the application."""
    
    # Signals for different data types
    accounts_changed = Signal()
    categories_changed = Signal()
    payment_methods_changed = Signal()
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True
            print("🔔 DataChangeNotifier initialized")


class ReactiveComboBox(QComboBox):
    """
    A ComboBox that automatically updates its options when the underlying data changes.
    
    This component listens to data change signals and refreshes its options accordingly.
    """
    
    def __init__(self, data_source_type: DataSourceType, data_fetcher: Callable[[], List[str]], 
                 parent=None, preserve_selection: bool = True):
        """
        Initialize the reactive combo box.
        
        Args:
            data_source_type: The type of data this dropdown represents
            data_fetcher: Function that returns the current list of options
            parent: Parent widget
            preserve_selection: Whether to preserve the current selection after refresh
        """
        super().__init__(parent)
        
        self.data_source_type = data_source_type
        self.data_fetcher = data_fetcher
        self.preserve_selection = preserve_selection
        
        # Get global notifier
        self.notifier = DataChangeNotifier()
        
        # Connect to appropriate signal based on data source type
        if data_source_type == DataSourceType.ACCOUNTS:
            self.notifier.accounts_changed.connect(self.refresh_options)
        elif data_source_type == DataSourceType.CATEGORIES:
            self.notifier.categories_changed.connect(self.refresh_options)
        elif data_source_type == DataSourceType.PAYMENT_METHODS:
            self.notifier.payment_methods_changed.connect(self.refresh_options)
        
        # Initial load
        self.refresh_options()
        
        print(f"🔄 ReactiveComboBox created for {data_source_type.value}")
    
    def refresh_options(self):
        """Refresh the dropdown options by fetching fresh data."""
        try:
            # Preserve current selection if requested
            current_selection = self.currentText() if self.preserve_selection else None
            
            # Get fresh data
            new_options = self.data_fetcher()
            
            # Update the dropdown
            self.clear()
            if new_options:
                self.addItems(new_options)
                
                # Restore selection if it still exists
                if current_selection and current_selection in new_options:
                    self.setCurrentText(current_selection)
                elif new_options:  # Default to first item if selection no longer exists
                    self.setCurrentIndex(0)
            
            print(f"🔄 {self.data_source_type.value.title()} dropdown refreshed: {len(new_options)} options")
            
        except Exception as e:
            print(f"❌ Error refreshing {self.data_source_type.value} dropdown: {e}")
    
    def get_current_options(self) -> List[str]:
        """Get the current options in the dropdown."""
        return [self.itemText(i) for i in range(self.count())]


class ReactiveDropdownManager:
    """
    Manager class for reactive dropdowns. Provides convenience methods for notifying changes.
    """
    
    @staticmethod
    def notify_accounts_changed():
        """Notify that account data has changed."""
        notifier = DataChangeNotifier()
        notifier.accounts_changed.emit()
        print("📢 Notified all account dropdowns of data change")
    
    @staticmethod
    def notify_categories_changed():
        """Notify that category data has changed."""
        notifier = DataChangeNotifier()
        notifier.categories_changed.emit()
        print("📢 Notified all category dropdowns of data change")
    
    @staticmethod
    def notify_payment_methods_changed():
        """Notify that payment method data has changed."""
        notifier = DataChangeNotifier()
        notifier.payment_methods_changed.emit()
        print("📢 Notified all payment method dropdowns of data change")


# Convenience factory functions
def create_accounts_dropdown(data_fetcher: Callable[[], List[str]], parent=None) -> ReactiveComboBox:
    """Create a reactive dropdown for accounts."""
    return ReactiveComboBox(DataSourceType.ACCOUNTS, data_fetcher, parent)


def create_categories_dropdown(data_fetcher: Callable[[], List[str]], parent=None) -> ReactiveComboBox:
    """Create a reactive dropdown for categories."""
    return ReactiveComboBox(DataSourceType.CATEGORIES, data_fetcher, parent)


def create_payment_methods_dropdown(data_fetcher: Callable[[], List[str]], parent=None) -> ReactiveComboBox:
    """Create a reactive dropdown for payment methods."""
    return ReactiveComboBox(DataSourceType.PAYMENT_METHODS, data_fetcher, parent)
