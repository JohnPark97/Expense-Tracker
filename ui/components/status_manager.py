"""
Centralized Status Manager
Handles status messages across the application and displays them in the main window footer.
"""

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QLabel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """Types of status messages."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    LOADING = "loading"


class StatusMessage:
    """Represents a status message."""
    
    def __init__(self, message: str, message_type: MessageType, timestamp: Optional[datetime] = None):
        self.message = message
        self.message_type = message_type
        self.timestamp = timestamp or datetime.now()
    
    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] {self.message}"


class StatusManager(QObject):
    """Centralized status manager for the application."""
    
    # Signal emitted when status changes
    status_changed = Signal(str, str)  # message, style_class
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True
            self.messages: List[StatusMessage] = []
            self.current_message = "Ready"
            self.status_label: Optional[QLabel] = None
            self.auto_clear_timer = QTimer()
            self.auto_clear_timer.timeout.connect(self._auto_clear_status)
            self.auto_clear_timer.setSingleShot(True)
            
            print("🔔 StatusManager initialized")
    
    def set_status_label(self, label: QLabel):
        """Set the status label widget to update."""
        self.status_label = label
        self._update_display()
    
    def show_info(self, message: str, auto_clear: bool = True):
        """Show an info message."""
        self._add_message(message, MessageType.INFO, auto_clear)
    
    def show_success(self, message: str, auto_clear: bool = True):
        """Show a success message."""
        self._add_message(message, MessageType.SUCCESS, auto_clear)
    
    def show_warning(self, message: str, auto_clear: bool = True):
        """Show a warning message."""
        self._add_message(message, MessageType.WARNING, auto_clear)
    
    def show_error(self, message: str, auto_clear: bool = False):
        """Show an error message."""
        self._add_message(message, MessageType.ERROR, auto_clear)
    
    def show_loading(self, message: str):
        """Show a loading message."""
        self._add_message(message, MessageType.LOADING, auto_clear=False)
    
    def clear_status(self):
        """Clear the current status and show 'Ready'."""
        self.current_message = "Ready"
        self._update_display()
    
    def _add_message(self, message: str, message_type: MessageType, auto_clear: bool = True):
        """Add a message to the history and update display."""
        status_msg = StatusMessage(message, message_type)
        self.messages.append(status_msg)
        
        # Keep only last 50 messages
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
        
        # Update current display
        self.current_message = message
        self._update_display()
        
        # Auto-clear after delay if requested
        if auto_clear:
            self.auto_clear_timer.stop()
            self.auto_clear_timer.start(5000)  # 5 seconds
        
        # Print to console for debugging
        icon = self._get_message_icon(message_type)
        print(f"{icon} {message}")
    
    def _update_display(self):
        """Update the status label display."""
        if self.status_label:
            style_class = self._get_style_class()
            self.status_label.setText(self.current_message)
            self.status_label.setStyleSheet(self._get_style())
            self.status_changed.emit(self.current_message, style_class)
    
    def _auto_clear_status(self):
        """Auto-clear status after timer expires."""
        if self.current_message != "Ready":
            self.clear_status()
    
    def _get_message_icon(self, message_type: MessageType) -> str:
        """Get icon for message type."""
        icons = {
            MessageType.INFO: "ℹ️",
            MessageType.SUCCESS: "✅",
            MessageType.WARNING: "⚠️",
            MessageType.ERROR: "❌",
            MessageType.LOADING: "🔄"
        }
        return icons.get(message_type, "📋")
    
    def _get_style_class(self) -> str:
        """Get CSS class for current message type."""
        if not self.messages:
            return "info"
        
        latest_type = self.messages[-1].message_type
        return latest_type.value
    
    def _get_style(self) -> str:
        """Get CSS style for current message type."""
        if not self.messages:
            return "color: #666; font-style: italic;"
        
        latest_type = self.messages[-1].message_type
        
        styles = {
            MessageType.INFO: "color: #666; font-style: italic;",
            MessageType.SUCCESS: "color: #28a745; font-weight: bold;",
            MessageType.WARNING: "color: #ffc107; font-weight: bold;",
            MessageType.ERROR: "color: #dc3545; font-weight: bold;",
            MessageType.LOADING: "color: #007bff; font-style: italic;"
        }
        
        return styles.get(latest_type, "color: #666; font-style: italic;")
    
    def get_recent_messages(self, count: int = 10) -> List[StatusMessage]:
        """Get recent messages."""
        return self.messages[-count:] if self.messages else []
    
    def get_error_messages(self) -> List[StatusMessage]:
        """Get all error messages."""
        return [msg for msg in self.messages if msg.message_type == MessageType.ERROR]
    
    def get_success_messages(self) -> List[StatusMessage]:
        """Get all success messages."""
        return [msg for msg in self.messages if msg.message_type == MessageType.SUCCESS]


# Global instance
status_manager = StatusManager()


# Convenience functions
def show_info(message: str, auto_clear: bool = True):
    """Show an info message."""
    status_manager.show_info(message, auto_clear)


def show_success(message: str, auto_clear: bool = True):
    """Show a success message."""
    status_manager.show_success(message, auto_clear)


def show_warning(message: str, auto_clear: bool = True):
    """Show a warning message."""
    status_manager.show_warning(message, auto_clear)


def show_error(message: str, auto_clear: bool = False):
    """Show an error message."""
    status_manager.show_error(message, auto_clear)


def show_loading(message: str):
    """Show a loading message."""
    status_manager.show_loading(message)


def clear_status():
    """Clear the current status."""
    status_manager.clear_status()
