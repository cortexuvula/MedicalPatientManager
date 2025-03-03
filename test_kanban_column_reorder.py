"""Test script for Kanban column reordering functionality."""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtGui import QDrag
from kanban_board import KanbanBoard
from models import Database
import os


class TestKanbanColumnReorder(QMainWindow):
    """Test window for kanban column reordering."""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Test Kanban Column Reordering")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create database connection with test database file
        test_db_file = "test_db.sqlite"
        
        # Delete existing test database file if it exists
        if os.path.exists(test_db_file):
            os.remove(test_db_file)
            
        # Create database
        self.db = Database(test_db_file)
        
        # Create a program for testing
        program_id = self.db.create_program("Test Program")
        
        # Create some tasks
        self.db.create_task(program_id, "Task 1", "Description 1", "todo")
        self.db.create_task(program_id, "Task 2", "Description 2", "in_progress")
        self.db.create_task(program_id, "Task 3", "Description 3", "done")
        
        # Create central widget
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # Create the kanban board
        self.kanban_board = KanbanBoard(self.db, program_id)
        layout.addWidget(self.kanban_board)
        
        self.setCentralWidget(central_widget)
        
        # Set up column configuration
        column_configs = [
            {"id": "todo", "title": "To Do"},
            {"id": "in_progress", "title": "In Progress"},
            {"id": "done", "title": "Done"},
            {"id": "backlog", "title": "Backlog"},
            {"id": "review", "title": "Review"}
        ]
        self.db.config["kanban_columns"] = column_configs
        
        # Rebuild columns
        self.kanban_board.createColumns()
        self.kanban_board.loadTasks()
        
        # Print instructions
        print("-" * 80)
        print("KANBAN COLUMN REORDERING TEST")
        print("-" * 80)
        print("Instructions:")
        print("1. Hover over the column header (the title section of each column)")
        print("2. Click and drag the column header to a new position")
        print("3. Release the mouse button to drop the column")
        print("4. The columns should rearrange in the order you specified")
        print("5. The order should be saved in the configuration and persist")
        print("6. Close the window when done testing")
        print("-" * 80)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_window = TestKanbanColumnReorder()
    test_window.show()
    sys.exit(app.exec_())
