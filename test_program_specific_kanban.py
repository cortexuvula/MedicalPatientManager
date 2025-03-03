"""Test script for patient-specific Kanban column configuration."""

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                            QLabel, QPushButton, QHBoxLayout, QTabWidget)
from PyQt5.QtCore import Qt
from kanban_board import KanbanBoard
from database import Database
from models import Patient, Program, Task
import os


class TestProgramSpecificKanban(QMainWindow):
    """Test window for patient-specific Kanban column configuration."""
    
    def __init__(self):
        super().__init__()
        self.db = Database(db_file="test_program_kanban.db")
        self.initUI()
        
    def initUI(self):
        """Initialize the test UI."""
        self.setWindowTitle("Test Program-Specific Kanban Configuration")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)

        # Create control buttons
        button_layout = QHBoxLayout()
        self.reorder_btn = QPushButton("Simulate Column Reordering")
        self.reorder_btn.clicked.connect(self.simulate_reordering)
        button_layout.addWidget(self.reorder_btn)
        
        self.restart_btn = QPushButton("Restart Test")
        self.restart_btn.clicked.connect(self.restart_test)
        button_layout.addWidget(self.restart_btn)
        
        layout.addLayout(button_layout)
        
        # Create tab widget for multiple kanban boards
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create patients
        patient1 = Patient(id=None, first_name="John", last_name="Doe", date_of_birth="1980-01-01", user_id=1)
        patient1_id = self.db.add_patient(patient1)
        
        patient2 = Patient(id=None, first_name="Jane", last_name="Smith", date_of_birth="1985-05-15", user_id=1)
        patient2_id = self.db.add_patient(patient2)
        
        # Create programs for each patient
        program1 = Program(id=None, name="Diabetes Management", patient_id=patient1_id)
        program1_id = self.db.add_program(program1)
        
        program2 = Program(id=None, name="Hypertension Management", patient_id=patient1_id)
        program2_id = self.db.add_program(program2)
        
        program3 = Program(id=None, name="Weight Management", patient_id=patient2_id)
        program3_id = self.db.add_program(program3)
        
        # Create some tasks
        task1 = Task(id=None, name="Check blood sugar", description="Monitor blood sugar levels daily", 
                    status="todo", program_id=program1_id)
        self.db.add_task(task1)
        
        task2 = Task(id=None, name="Exercise", description="30 minutes of walking", 
                    status="in_progress", program_id=program1_id)
        self.db.add_task(task2)
        
        task3 = Task(id=None, name="Take insulin", description="As prescribed", 
                    status="done", program_id=program1_id)
        self.db.add_task(task3)
        
        task4 = Task(id=None, name="Monitor blood pressure", description="Check BP twice daily", 
                    status="todo", program_id=program2_id)
        self.db.add_task(task4)
        
        task5 = Task(id=None, name="Reduce sodium", description="Follow low-sodium diet", 
                    status="in_progress", program_id=program2_id)
        self.db.add_task(task5)
        
        task6 = Task(id=None, name="Track calories", description="Log all meals", 
                    status="todo", program_id=program3_id)
        self.db.add_task(task6)
        
        task7 = Task(id=None, name="Weekly weigh-in", description="Record weight every Monday", 
                    status="in_progress", program_id=program3_id)
        self.db.add_task(task7)
        
        # Create kanban boards for each program
        self.kanban1 = KanbanBoard(self.db, program1_id)
        self.kanban2 = KanbanBoard(self.db, program2_id)
        self.kanban3 = KanbanBoard(self.db, program3_id)
        
        # Add to tabs
        self.tabs.addTab(self.kanban1, "John - Diabetes")
        self.tabs.addTab(self.kanban2, "John - Hypertension")
        self.tabs.addTab(self.kanban3, "Jane - Weight Management")
        
        # Add instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Each program should have its own column configuration\n"
            "2. Modify the columns using the 'Customize Columns' button in each tab\n"
            "3. Make different column arrangements for each program\n"
            "4. Switch between tabs to verify that each program maintains its own column order\n"
            "5. Try reordering columns by dragging and dropping the column headers\n"
            "6. Verify that the order is saved when you switch tabs and come back"
        )
        instructions.setStyleSheet("font-size: 14px; margin: 20px;")
        layout.addWidget(instructions)

    def simulate_reordering(self):
        """Simulate reordering columns in kanban board."""
        # Get the current column configuration of the first board
        program1_id = self.kanban1.program_id
        original_config = self.db.get_program_kanban_config(program1_id)
        
        if original_config and len(original_config) >= 3:
            # Create a new configuration with reordered columns
            new_config = original_config.copy()
            # Swap first two columns
            new_config[0], new_config[1] = new_config[1], new_config[0]
            
            # Save the new configuration
            self.db.save_program_kanban_config(program1_id, new_config)
            
            # Refresh the kanban board
            self.tabs.setCurrentIndex(0)  # Switch to first tab
            self.kanban1.refresh()
            
            print("Columns reordered. First two columns were swapped.")
        else:
            print("Cannot reorder: Not enough columns in configuration.")
    
    def restart_test(self):
        """Restart the test by recreating the kanban boards."""
        # Remove existing tabs
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        
        # Recreate the kanban boards
        program_ids = []
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id FROM programs ORDER BY id LIMIT 3")
        rows = cursor.fetchall()
        for row in rows:
            program_ids.append(row['id'])
        
        if len(program_ids) >= 3:
            # Recreate the kanban boards with the same program IDs
            self.kanban1 = KanbanBoard(self.db, program_ids[0])
            self.tabs.addTab(self.kanban1, "Program 1")
            
            self.kanban2 = KanbanBoard(self.db, program_ids[1])
            self.tabs.addTab(self.kanban2, "Program 2")
            
            self.kanban3 = KanbanBoard(self.db, program_ids[2])
            self.tabs.addTab(self.kanban3, "Program 3")
            
            print("Test restarted with fresh kanban boards.")
        else:
            print("Error: Not enough programs found in database.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_window = TestProgramSpecificKanban()
    test_window.show()
    sys.exit(app.exec_())
