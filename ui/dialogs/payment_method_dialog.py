"""
Payment Method Dialog
Dialog for adding/editing payment methods.
"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit, 
    QCheckBox, QDialogButtonBox
)


class PaymentMethodDialog(QDialog):
    """Dialog for adding/editing payment methods."""
    
    def __init__(self, parent=None, method_name="", description="", active=True):
        super().__init__(parent)
        self.setWindowTitle("Payment Method")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self.method_name = method_name
        self.description = description
        self.active = active
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QFormLayout()
        self.setLayout(layout)
        
        # Method name input
        self.name_input = QLineEdit(self.method_name)
        self.name_input.setPlaceholderText("e.g., PayPal, Apple Pay, etc.")
        layout.addRow("Payment Method:", self.name_input)
        
        # Description input
        self.description_input = QTextEdit(self.description)
        self.description_input.setMaximumHeight(60)
        self.description_input.setPlaceholderText("Optional description...")
        layout.addRow("Description:", self.description_input)
        
        # Active checkbox
        self.active_checkbox = QCheckBox("Active (show in dropdowns)")
        self.active_checkbox.setChecked(self.active)
        layout.addRow("", self.active_checkbox)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_data(self):
        """Get the entered data."""
        return {
            'name': self.name_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'active': self.active_checkbox.isChecked()
        }
