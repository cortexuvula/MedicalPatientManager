from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QInputDialog,
                             QTextEdit, QDialog, QLineEdit, QFormLayout, QMessageBox,
                             QTabWidget)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal
from PyQt5.QtGui import QDrag, QFont

from models import Task


class TaskWidget(QFrame):
    """Widget representing a task in the Kanban board."""
    
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.initUI()
    
    def initUI(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        self.setAcceptDrops(False)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Task title
        self.title_label = QLabel(self.task.name)
        self.title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # Task description (if any)
        if self.task.description:
            self.desc_label = QLabel(self.task.description)
            self.desc_label.setWordWrap(True)
            layout.addWidget(self.desc_label)
        
        # Task actions
        action_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setFixedWidth(60)
        self.edit_btn.clicked.connect(self.editTask)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFixedWidth(60)
        self.delete_btn.clicked.connect(self.deleteTask)
        
        action_layout.addWidget(self.edit_btn)
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        
        # Set style
        self.setStyleSheet("""
            TaskWidget {
                background-color: white;
                border-radius: 5px;
                border: 1px solid #cccccc;
            }
            
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 3px;
            }
            
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.task.id))
        drag.setMimeData(mime_data)
        
        # Create a pixmap representation of the widget for the drag
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec_(Qt.MoveAction)
    
    def editTask(self):
        # Find the parent KanbanColumn
        parent = self.parent()
        while parent and not isinstance(parent, KanbanBoard):
            parent = parent.parent()
        
        if parent:
            parent.editTask(self.task)
    
    def deleteTask(self):
        # Find the parent KanbanColumn
        parent = self.parent()
        while parent and not isinstance(parent, KanbanBoard):
            parent = parent.parent()
        
        if parent:
            parent.deleteTask(self.task)


class KanbanColumn(QWidget):
    """Widget representing a column in the Kanban board."""
    taskDropped = pyqtSignal(int, str)  # Task ID, new status
    
    def __init__(self, title, status, parent=None):
        super().__init__(parent)
        self.title = title
        self.status = status
        self.initUI()
    
    def initUI(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Column title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Tasks container
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout()
        self.tasks_container.setLayout(self.tasks_layout)
        
        # Scroll area for tasks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.tasks_container)
        layout.addWidget(scroll)
        
        # Add task button
        self.add_btn = QPushButton("+ Add Task")
        self.add_btn.clicked.connect(self.addTask)
        layout.addWidget(self.add_btn)
        
        # Set fixed width
        self.setMinimumWidth(250)
        self.setMaximumWidth(300)
        
        # Set style
        self.setStyleSheet("""
            KanbanColumn {
                background-color: #f5f5f5;
                border-radius: 5px;
                border: 1px solid #dddddd;
            }
            
            QScrollArea {
                border: none;
            }
            
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
            }
            
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
    
    def addTask(self):
        self.parent().addTask(self.status)
    
    def addTaskWidget(self, task_widget):
        self.tasks_layout.addWidget(task_widget)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        task_id = int(event.mimeData().text())
        self.taskDropped.emit(task_id, self.status)
        event.acceptProposedAction()


class TaskDialog(QDialog):
    """Dialog for adding or editing a task."""
    
    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Add Task" if not self.task else "Edit Task")
        self.setMinimumWidth(400)
        
        layout = QFormLayout()
        self.setLayout(layout)
        
        # Task name
        self.name_input = QLineEdit()
        if self.task:
            self.name_input.setText(self.task.name)
        layout.addRow("Task Name:", self.name_input)
        
        # Task description
        self.desc_input = QTextEdit()
        if self.task and self.task.description:
            self.desc_input.setText(self.task.description)
        self.desc_input.setMaximumHeight(100)
        layout.addRow("Description:", self.desc_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        layout.addRow("", button_layout)
    
    def getTaskData(self):
        """Get the task data from the dialog."""
        return {
            "name": self.name_input.text(),
            "description": self.desc_input.toPlainText()
        }


class KanbanBoard(QWidget):
    """Widget representing a Kanban board."""
    
    def __init__(self, db, program_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.program_id = program_id
        self.program = db.get_program_by_id(program_id)
        self.initUI()
        self.loadTasks()
    
    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel(f"{self.program.name}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title)
        
        # Buttons for program management
        self.edit_program_btn = QPushButton("Edit Program")
        self.edit_program_btn.clicked.connect(self.editProgram)
        header_layout.addWidget(self.edit_program_btn)
        
        layout.addLayout(header_layout)
        
        # Kanban columns
        columns_layout = QHBoxLayout()
        
        # Create columns
        self.columns = {
            "To Do": KanbanColumn("To Do", "To Do"),
            "In Progress": KanbanColumn("In Progress", "In Progress"),
            "Done": KanbanColumn("Done", "Done")
        }
        
        # Add columns to layout
        for column in self.columns.values():
            columns_layout.addWidget(column)
            column.taskDropped.connect(self.onTaskDropped)
        
        layout.addLayout(columns_layout)
    
    def loadTasks(self):
        """Load tasks from the database into the appropriate columns."""
        # Clear existing tasks
        for column in self.columns.values():
            while column.tasks_layout.count():
                item = column.tasks_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # Get tasks for this program
        tasks = self.db.get_tasks_by_program(self.program_id)
        
        # Add tasks to appropriate columns
        for task in tasks:
            task_widget = TaskWidget(task)
            if task.status in self.columns:
                self.columns[task.status].addTaskWidget(task_widget)
            else:
                # Default to "To Do" if status is not recognized
                self.columns["To Do"].addTaskWidget(task_widget)
    
    def addTask(self, status):
        """Add a new task to the specified column."""
        dialog = TaskDialog(parent=self)
        if dialog.exec_():
            task_data = dialog.getTaskData()
            task = Task(
                name=task_data["name"],
                description=task_data["description"],
                status=status,
                program_id=self.program_id
            )
            self.db.add_task(task)
            self.loadTasks()
    
    def editTask(self, task):
        """Edit an existing task."""
        dialog = TaskDialog(task, parent=self)
        if dialog.exec_():
            task_data = dialog.getTaskData()
            task.name = task_data["name"]
            task.description = task_data["description"]
            self.db.update_task(task)
            self.loadTasks()
    
    def deleteTask(self, task):
        """Delete an existing task."""
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete task '{task.name}'?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.db.delete_task(task.id)
            self.loadTasks()
    
    def onTaskDropped(self, task_id, new_status):
        """Update task status when dropped into a new column."""
        self.db.update_task_status(task_id, new_status)
        self.loadTasks()
    
    def editProgram(self):
        """Edit the program name."""
        name, ok = QInputDialog.getText(self, "Edit Program", 
                                     "Program Name:", text=self.program.name)
        if ok and name:
            self.program.name = name
            # Update the program in the database
            if not self.db.update_program(self.program):
                QMessageBox.warning(self, "Error", "Failed to update program in database")
                return
            
            # Update the tab text
            parent = self.parent()
            if isinstance(parent, QTabWidget):
                index = parent.indexOf(self)
                parent.setTabText(index, name)


# Import needed for drag and drop
from PyQt5.QtWidgets import QApplication
