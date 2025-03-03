"""
Test column reordering in QTableWidget.
This is a standalone test to verify column dragging functionality.
"""
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                           QTableWidgetItem, QHeaderView, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt


class TestColumnReorderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Column Reordering Test")
        self.setGeometry(100, 100, 800, 400)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create table with reorderable columns
        self.table = QTableWidget(10, 5)
        self.table.setHorizontalHeaderLabels(["Column 1", "Column 2", "Column 3", "Column 4", "Column 5"])
        
        # Enable column reordering by setting movable flag to the table's header
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setFirstSectionMovable(True)
        
        # Connect signal to track when reordering happens
        header.sectionMoved.connect(self.column_moved)
        
        # Add some visual style to the headers
        header.setStyleSheet("QHeaderView::section { padding: 4px; background-color: #e0e0ff; border: 1px solid #b0b0b0; }")
        
        # Populate with some data
        for row in range(10):
            for col in range(5):
                self.table.setItem(row, col, QTableWidgetItem(f"Item {row+1},{col+1}"))
        
        layout.addWidget(self.table)
    
    def column_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        print(f"Column moved: Logical index {logicalIndex} from {oldVisualIndex} to {newVisualIndex}")


if __name__ == "__main__":
    # Create the application
    app = QApplication(sys.argv)
    
    # Create and show the window
    window = TestColumnReorderWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())
