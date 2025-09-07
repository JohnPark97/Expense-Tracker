"""
Payment Methods Tab
Tab for managing payment methods that appear in expense sheet dropdowns.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
import pandas as pd

from services.google_sheets import GoogleSheetsService
from ui.dialogs.payment_method_dialog import PaymentMethodDialog


class PaymentMethodsTab(QWidget):
    """Payment methods management tab."""
    
    def __init__(self, sheets_service: GoogleSheetsService, spreadsheet_id: str):
        super().__init__()
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.changed_cells = set()  # Track individual cells that have changed (row, col)
        self.original_values = {}  # Store original values for changed cells (row, col): value
        self.setup_ui()
        self.ensure_payment_methods_sheet()
    
    def setup_ui(self):
        """Setup the payment methods tab UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("💳 Payment Methods")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Manage payment methods that appear in expense sheet dropdowns")
        desc.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.add_button = QPushButton("➕ Add Payment Method")
        self.add_button.clicked.connect(self.add_payment_method)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        controls_layout.addWidget(self.add_button)
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.load_payment_methods)
        controls_layout.addWidget(self.refresh_button)
        
        self.delete_button = QPushButton("🗑️ Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_payment_methods)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c82333; }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.delete_button.setVisible(False)  # Hidden by default
        controls_layout.addWidget(self.delete_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic; margin: 5px;")
        layout.addWidget(self.status_label)
        
        # Table
        self.payment_table = QTableWidget()
        self.payment_table.setColumnCount(3)
        self.payment_table.setHorizontalHeaderLabels(["Payment Method", "Description", "Active"])
        self.payment_table.setAlternatingRowColors(True)
        self.payment_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Connect to item changed signal for real-time updates
        self.payment_table.itemChanged.connect(self.on_table_item_changed)
        
        # Connect to cell clicked signal for Active status toggle
        self.payment_table.cellClicked.connect(self.on_cell_clicked)
        
        # Connect to selection changed signal for delete button visibility
        self.payment_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        # Make table look nice
        header = self.payment_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Payment Method
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Description
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Active
        
        layout.addWidget(self.payment_table)
        
        # Bottom info
        info_label = QLabel("""
💡 Tips:
• Payment methods marked with ✅ appear in expense sheet dropdowns
• Click directly on any cell to edit payment method names and descriptions
• Click on ✅/❌ to toggle active status
• All changes sync immediately with your Google Sheets
        """)
        info_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                color: #666;
                font-size: 11px;
            }
        """)
        layout.addWidget(info_label)
    
    def ensure_payment_methods_sheet(self):
        """Ensure Payment Methods sheet exists, create if it doesn't, then load data."""
        try:
            self.status_label.setText("🔄 Checking Payment Methods sheet...")
            
            # Check if Payment Methods sheet exists
            existing_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            if "Payment Methods" not in existing_sheets:
                # Create the sheet automatically
                self.status_label.setText("🔄 Creating Payment Methods sheet...")
                success = self.sheets_service.create_payment_methods_sheet(self.spreadsheet_id)
                
                if not success:
                    self.status_label.setText("❌ Failed to create Payment Methods sheet")
                    self.show_empty_table()
                    return
                
                self.status_label.setText("✅ Payment Methods sheet created with default methods")
            
            # Load data from sheet
            self.load_payment_methods()
            
        except Exception as e:
            self.status_label.setText(f"❌ Error setting up Payment Methods: {str(e)}")
            self.show_empty_table()
    
    def load_payment_methods(self):
        """Load payment methods from Google Sheets."""
        try:
            self.status_label.setText("🔄 Loading payment methods...")
            
            # Load data from sheet
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, "'Payment Methods'!A:C"
            )
            
            if df.empty:
                self.status_label.setText("📄 Payment Methods sheet is empty")
                self.show_empty_table()
                return
            
            # Populate table
            self.populate_payment_table(df)
            self.status_label.setText(f"✅ Loaded {len(df)} payment methods")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error loading payment methods: {str(e)}")
            self.show_empty_table()
    
    def show_empty_table(self):
        """Show empty table with helpful message."""
        self.payment_table.setRowCount(1)
        self.payment_table.setItem(0, 0, QTableWidgetItem("No payment methods found"))
        self.payment_table.setItem(0, 1, QTableWidgetItem("Payment methods will be loaded automatically"))
        self.payment_table.setItem(0, 2, QTableWidgetItem("--"))
        
        # Make row non-editable and gray
        for col in range(3):
            item = self.payment_table.item(0, col)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QColor(220, 220, 220))  # Light gray color
    
    def populate_payment_table(self, df):
        """Populate table with payment methods data."""
        # Temporarily disconnect the signal to avoid triggering updates during population
        self.payment_table.itemChanged.disconnect()
        
        self.payment_table.setRowCount(len(df))
        
        for row in range(len(df)):
            # Payment Method - editable
            method_item = QTableWidgetItem(str(df.iloc[row, 0]) if pd.notna(df.iloc[row, 0]) else "")
            method_item.setToolTip("Click to edit payment method name")
            self.payment_table.setItem(row, 0, method_item)
            
            # Description - editable
            desc_item = QTableWidgetItem(str(df.iloc[row, 1]) if pd.notna(df.iloc[row, 1]) else "")
            desc_item.setToolTip("Click to edit description")
            self.payment_table.setItem(row, 1, desc_item)
            
            # Active status - clickable to toggle (not editable via typing)
            active_value = str(df.iloc[row, 2]).upper() if pd.notna(df.iloc[row, 2]) else "YES"
            active_item = QTableWidgetItem("✅" if active_value == "YES" else "❌")
            active_item.setToolTip("Click to toggle active status")
            # Make active column non-editable via keyboard but clickable
            flags = active_item.flags()
            flags &= ~Qt.ItemFlag.ItemIsEditable
            active_item.setFlags(flags)
            self.payment_table.setItem(row, 2, active_item)
        
        # Store original values for change tracking
        self.store_original_values()
        
        # Reconnect the signal
        self.payment_table.itemChanged.connect(self.on_table_item_changed)
    
    def store_original_values(self):
        """Store original values for change tracking."""
        self.original_values.clear()
        for row in range(self.payment_table.rowCount()):
            for col in range(self.payment_table.columnCount()):
                if col == 2:  # Active column - skip as it's handled by clicking
                    continue
                item = self.payment_table.item(row, col)
                value = item.text() if item else ""
                self.original_values[(row, col)] = value
    
    def highlight_changed_cell(self, row: int, col: int):
        """Apply eye-friendly highlighting to a changed cell."""
        item = self.payment_table.item(row, col)
        if item:
            # Use a very subtle blue/cream color that's eye-friendly
            item.setBackground(QColor(230, 245, 255))  # Very light blue
    
    def clear_cell_highlighting(self):
        """Clear highlighting from all cells."""
        self.changed_cells.clear()
        
        for row in range(self.payment_table.rowCount()):
            for col in range(self.payment_table.columnCount()):
                if col == 2:  # Active column - skip
                    continue
                item = self.payment_table.item(row, col)
                if item:
                    # Clear background color
                    item.setBackground(QColor())
    
    def check_cell_changed(self, row: int, col: int) -> bool:
        """Check if a cell's value has changed from its original value."""
        original_value = self.original_values.get((row, col), "")
        item = self.payment_table.item(row, col)
        current_value = item.text() if item else ""
        return current_value != original_value
    
    def on_cell_clicked(self, row: int, column: int):
        """Handle cell clicks, especially for Active status toggle."""
        if column == 2:  # Active status column
            item = self.payment_table.item(row, column)
            if item:
                # Toggle the active status
                if item.text() == "✅":
                    item.setText("❌")
                    self.update_payment_method_on_server(row, column, "No")
                else:
                    item.setText("✅")
                    self.update_payment_method_on_server(row, column, "Yes")
    
    def on_table_item_changed(self, item):
        """Handle table item changes and update server."""
        row = item.row()
        column = item.column()
        new_value = item.text()
        
        # Skip Active column changes here since they're handled by on_cell_clicked
        if column == 2:  # Active column
            return
        
        # Only process Payment Method and Description columns
        if column in [0, 1]:
            # Validate that the value is not empty for Payment Method
            if column == 0 and not new_value.strip():
                self.status_label.setText("❌ Payment method name cannot be empty")
                return
            
            # Check if cell value actually changed from original
            if self.check_cell_changed(row, column):
                # Track the changed cell
                self.changed_cells.add((row, column))
                # Apply highlighting to the changed cell
                self.highlight_changed_cell(row, column)
                # Update server immediately for payment methods (no confirm button here)
                self.update_payment_method_on_server(row, column, new_value)
            else:
                # Cell was reverted to original value
                self.changed_cells.discard((row, column))
                # Clear highlighting
                item.setBackground(QColor())
                # Still update server to ensure consistency
                self.update_payment_method_on_server(row, column, new_value)
    
    def update_payment_method_on_server(self, row: int, column: int, new_value: str):
        """Update a specific cell in the Payment Methods sheet on the server."""
        try:
            # Calculate the actual row in Google Sheets (row 0 in table = row 2 in sheet, since row 1 has headers)
            sheet_row = row + 2
            
            # Map column index to letter
            column_letters = ['A', 'B', 'C']
            if column >= len(column_letters):
                return
            
            column_letter = column_letters[column]
            cell_range = f"'Payment Methods'!{column_letter}{sheet_row}"
            
            self.status_label.setText(f"🔄 Updating {['payment method', 'description', 'active status'][column]}...")
            
            # Update the cell
            success = self.sheets_service.update_sheet_data(
                self.spreadsheet_id,
                "Payment Methods",
                [[new_value]],
                f"{column_letter}{sheet_row}"
            )
            
            if success:
                column_names = ['Payment Method', 'Description', 'Active Status']
                self.status_label.setText(f"✅ Updated {column_names[column].lower()}")
                
                # Clear highlighting for this cell and update original value
                self.changed_cells.discard((row, column))
                if column in [0, 1]:  # Only for editable columns
                    item = self.payment_table.item(row, column)
                    if item:
                        item.setBackground(QColor())  # Clear highlighting
                        self.original_values[(row, column)] = new_value  # Update original value
            else:
                self.status_label.setText(f"❌ Failed to update {column_names[column].lower()}")
                # Reload the table to restore original values
                self.load_payment_methods()
                
        except Exception as e:
            self.status_label.setText(f"❌ Error updating server: {str(e)}")
            # Reload the table to restore original values
            self.load_payment_methods()
    
    def add_payment_method(self):
        """Show dialog to add new payment method."""
        dialog = PaymentMethodDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data['name']:
                QMessageBox.warning(self, "Invalid Input", "Payment method name cannot be empty.")
                return
            
            # Add to Google Sheets
            self.status_label.setText(f"➕ Adding payment method: {data['name']}...")
            
            success = self.sheets_service.add_payment_method(
                self.spreadsheet_id,
                data['name'],
                data['description'],
                data['active']
            )
            
            if success:
                self.status_label.setText(f"✅ Added payment method: {data['name']}")
                self.load_payment_methods()  # Refresh table
            else:
                self.status_label.setText(f"❌ Failed to add payment method: {data['name']}")
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to add payment method '{data['name']}'. Please try again."
                )
    
    def on_selection_changed(self):
        """Handle table selection changes and update delete button visibility."""
        selected_rows = set()
        for item in self.payment_table.selectedItems():
            selected_rows.add(item.row())
        
        if selected_rows:
            count = len(selected_rows)
            row_text = "row" if count == 1 else "rows"
            self.delete_button.setText(f"🗑️ Delete {count} {row_text}")
            self.delete_button.setVisible(True)
        else:
            self.delete_button.setVisible(False)
    
    def delete_selected_payment_methods(self):
        """Delete selected payment methods after confirmation."""
        selected_rows = set()
        for item in self.payment_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        # Get payment method names for confirmation
        payment_method_names = []
        for row in sorted(selected_rows):
            item = self.payment_table.item(row, 0)  # Payment Method column
            if item:
                payment_method_names.append(item.text())
        
        # Confirmation dialog
        count = len(selected_rows)
        row_text = "row" if count == 1 else "rows"
        method_text = "payment method" if count == 1 else "payment methods"
        
        methods_list = "\n".join([f"• {name}" for name in payment_method_names[:5]])  # Show first 5
        if len(payment_method_names) > 5:
            methods_list += f"\n... and {len(payment_method_names) - 5} more"
        
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {count} {method_text}?\n\n{methods_list}\n\n"
            "This action cannot be undone and will remove the payment methods from Google Sheets.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete from server
        self.status_label.setText("🗑️ Deleting payment methods...")
        success_count = 0
        error_count = 0
        
        # Sort rows in reverse order to delete from bottom up (preserves row indices)
        for row in sorted(selected_rows, reverse=True):
            try:
                # Calculate actual row in Google Sheets (add 2 for header row and 0-based indexing)
                sheet_row = row + 2
                
                # Delete the row by clearing its contents and removing it
                # First, get the payment method name to verify
                item = self.payment_table.item(row, 0)
                if not item:
                    continue
                    
                payment_method_name = item.text()
                
                # Delete the row from Google Sheets
                # We'll clear the row contents by setting them to empty
                success = self.sheets_service.update_sheet_data(
                    self.spreadsheet_id,
                    "Payment Methods",
                    [["", "", ""]],  # Empty row
                    f"A{sheet_row}"
                )
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    print(f"Failed to delete payment method: {payment_method_name}")
                    
            except Exception as e:
                error_count += 1
                print(f"Error deleting row {row}: {e}")
        
        # Update status and refresh table
        if error_count == 0:
            self.status_label.setText(f"✅ Successfully deleted {success_count} {method_text}")
        else:
            self.status_label.setText(f"⚠️ Deleted {success_count}, failed {error_count}. Check server connection.")
        
        # Refresh the table to show current state
        self.load_payment_methods()
        
        # Hide delete button
        self.delete_button.setVisible(False)
    
