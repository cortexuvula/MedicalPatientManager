from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QInputDialog,
                             QTextEdit, QDialog, QLineEdit, QFormLayout, QMessageBox,
                             QTabWidget, QApplication, QDialogButtonBox)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from PyQt5.QtGui import QDrag, QFont, QPixmap, QCursor

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
    columnMoved = pyqtSignal(str, int)  # Column ID, new position
    
    def __init__(self, title, status, parent=None):
        super().__init__(parent)
        self.title = title
        self.status = status
        self.initUI()
    
    def initUI(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Column header
        header_layout = QHBoxLayout()
        header_widget = QFrame()
        header_widget.setObjectName("column_header")
        header_widget.setLayout(header_layout)
        header_widget.setCursor(Qt.OpenHandCursor)
        header_widget.setStyleSheet("background-color: #e0e0e0; border-radius: 3px; padding: 5px;")
        
        # Column title
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.title_label)
        
        # Add the header to the main layout
        layout.addWidget(header_widget)
        
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
        
        # Install event filter for the header to handle dragging
        header_widget.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle mouse events for the column header."""
        if obj.objectName() == "column_header":
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                self.drag_start_position = event.pos()
                return True
            elif event.type() == event.MouseMove and event.buttons() & Qt.LeftButton:
                # Check if dragging has started
                if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                    return True
                    
                # Create drag object
                drag = QDrag(obj)
                mime_data = QMimeData()
                mime_data.setText(f"kanban_column:{self.status}")
                drag.setMimeData(mime_data)
                
                # Create pixmap for dragging
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.pos())
                
                # Execute the drag
                result = drag.exec_(Qt.MoveAction)
                return True
                
        return super().eventFilter(obj, event)
    
    def setTitle(self, title):
        """Set the column title."""
        self.title = title
        self.title_label.setText(title)
    
    def addTask(self):
        self.parent().addTask(self.status)
    
    def addTaskWidget(self, task_widget):
        self.tasks_layout.addWidget(task_widget)
    
    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasText():
            text = mime_data.text()
            if text.startswith("kanban_column:"):
                # This is a column being dragged
                event.acceptProposedAction()
            else:
                # This is a task being dragged
                event.acceptProposedAction()
    
    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasText():
            text = mime_data.text()
            if text.startswith("kanban_column:"):
                # Extract dragged column ID
                dragged_column_id = text.split(":", 1)[1]
                # Let the parent handle column reordering
                parent = self.parent()
                if parent:
                    # Find the index of this column
                    for i, column in enumerate(parent.findChildren(KanbanColumn)):
                        if column == self:
                            # Emit signal to reorder columns
                            self.columnMoved.emit(dragged_column_id, i)
                            break
            else:
                # This is a task being dropped
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
        self.config = db.config
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
        
        # Button for customizing column titles
        self.customize_columns_btn = QPushButton("Customize Columns")
        self.customize_columns_btn.clicked.connect(self.customizeColumns)
        header_layout.addWidget(self.customize_columns_btn)
        
        layout.addLayout(header_layout)
        
        # Kanban columns
        self.columns_layout = QHBoxLayout()
        layout.addLayout(self.columns_layout)
        
        # Create columns
        self.columns = {}
        self.createColumns()
    
    def createColumns(self):
        """Create columns based on program-specific configuration."""
        # Clear existing columns
        for column in self.columns.values():
            column.setParent(None)
        self.columns.clear()
        
        # Clear layout
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        # Get program-specific column configuration
        column_configs = self.db.get_program_kanban_config(self.program_id)
        
        # If no program-specific config, use default config
        if column_configs is None:
            # Get column configuration from global config
            kanban_config = self.config.get("kanban_columns", [])
            column_configs = []
            
            # Handle old configuration format (dictionary with key-value pairs)
            if isinstance(kanban_config, dict):
                # Convert old format to new format
                for column_id, column_title in kanban_config.items():
                    column_configs.append({"id": column_id, "title": column_title})
            # Handle new configuration format (list of objects)
            elif isinstance(kanban_config, list):
                column_configs = kanban_config
            
            # If no valid configuration, use defaults
            if not column_configs:
                column_configs = [
                    {"id": "todo", "title": "To Do"},
                    {"id": "in_progress", "title": "In Progress"},
                    {"id": "done", "title": "Done"}
                ]
        
        # Create columns
        for column_config in column_configs:
            # Check if column_config is a dictionary or string (for compatibility)
            if isinstance(column_config, dict):
                column_id = column_config.get("id")
                column_title = column_config.get("title")
            else:
                # Handle unexpected format by using the item as both id and title
                column_id = str(column_config)
                column_title = str(column_config)
            
            column = KanbanColumn(column_title, column_id)
            self.columns[column_id] = column
            self.columns_layout.addWidget(column)
            column.taskDropped.connect(self.onTaskDropped)
            column.columnMoved.connect(self.onColumnMoved)
    
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
                self.columns["todo"].addTaskWidget(task_widget)
    
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
    
    def onColumnMoved(self, column_id, new_position):
        """Update column order when a column is moved."""
        # Get the program-specific column configuration
        column_configs = self.db.get_program_kanban_config(self.program_id)
        
        # If no program-specific config exists, get from global config
        if column_configs is None:
            # Get column configuration from global config
            kanban_config = self.config.get("kanban_columns", [])
            
            # Handle old configuration format (dictionary with key-value pairs)
            if isinstance(kanban_config, dict):
                # Convert old format to new format
                column_configs = [{"id": column_id, "title": kanban_config[column_id]} for column_id in kanban_config]
            # Handle new configuration format (list of objects)
            elif isinstance(kanban_config, list):
                column_configs = kanban_config
            
            # If no valid configuration, use defaults
            if not column_configs:
                column_configs = [
                    {"id": "todo", "title": "To Do"},
                    {"id": "in_progress", "title": "In Progress"},
                    {"id": "done", "title": "Done"}
                ]
        
        # Move the column to the new position
        for i, column in enumerate(column_configs):
            if column["id"] == column_id:
                column_configs.pop(i)
                column_configs.insert(new_position, column)
                break
        
        # Save the updated program-specific configuration
        self.db.save_program_kanban_config(self.program_id, column_configs)
        
        # Update the column titles in the UI
        self.createColumns()
        
        # Reload tasks
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
    
    def customizeColumns(self):
        """Open dialog to customize column titles."""
        dialog = ColumnSettingsDialog(self)
        dialog.exec_()
    
    def moveColumnUp(self, index):
        """Move a column up in the list (decrease index)."""
        if index <= 0:
            return False  # Already at the top
        
        # Get program-specific column configuration
        column_configs = self.db.get_program_kanban_config(self.program_id)
        
        # Swap columns
        column_configs[index], column_configs[index-1] = column_configs[index-1], column_configs[index]
        
        # Save updated configuration
        self.db.save_program_kanban_config(self.program_id, column_configs)
        
        # Update UI
        self.createColumns()
        self.loadTasks()
        return True
    
    def moveColumnDown(self, index):
        """Move a column down in the list (increase index)."""
        # Get program-specific column configuration
        column_configs = self.db.get_program_kanban_config(self.program_id)
        
        if index >= len(column_configs) - 1:
            return False  # Already at the bottom
        
        # Swap columns
        column_configs[index], column_configs[index+1] = column_configs[index+1], column_configs[index]
        
        # Save updated configuration
        self.db.save_program_kanban_config(self.program_id, column_configs)
        
        # Update UI
        self.createColumns()
        self.loadTasks()
        return True


class ColumnSettingsDialog(QDialog):
    """Dialog for customizing column titles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kanban_board = parent
        self.db = self.kanban_board.db
        self.program_id = self.kanban_board.program_id
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Customize Kanban Columns")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add description
        description = QLabel("Customize the titles of your Kanban board columns:")
        layout.addWidget(description)
        
        # Get program-specific column configuration
        program_column_config = self.db.get_program_kanban_config(self.program_id)
        
        self.current_columns = []
        
        # If we have program-specific config, use it
        if program_column_config:
            if isinstance(program_column_config, list):
                self.current_columns = program_column_config
            else:
                # Handle unexpected format
                self.current_columns = [
                    {"id": "todo", "title": "To Do"},
                    {"id": "in_progress", "title": "In Progress"},
                    {"id": "done", "title": "Done"}
                ]
        else:
            # Get current values from global config
            kanban_config = self.kanban_board.config.get("kanban_columns", [])
            
            # Handle old configuration format (dictionary with key-value pairs)
            if isinstance(kanban_config, dict):
                for column_id, column_title in kanban_config.items():
                    self.current_columns.append({"id": column_id, "title": column_title})
            # Handle new configuration format (list of objects)
            elif isinstance(kanban_config, list):
                self.current_columns = kanban_config
            
            # If no valid configuration, use defaults
            if not self.current_columns:
                self.current_columns = [
                    {"id": "todo", "title": "To Do"},
                    {"id": "in_progress", "title": "In Progress"},
                    {"id": "done", "title": "Done"}
                ]
        
        # Columns container
        self.columns_container = QFrame()
        self.columns_layout = QVBoxLayout()
        self.columns_container.setLayout(self.columns_layout)
        layout.addWidget(self.columns_container)
        
        # Add buttons for adding/removing columns
        btn_layout = QHBoxLayout()
        
        self.add_column_btn = QPushButton("Add Column")
        self.add_column_btn.clicked.connect(self.addColumn)
        btn_layout.addWidget(self.add_column_btn)
        
        # Disable the add button if we already have 5 columns
        self.add_column_btn.setEnabled(len(self.current_columns) < 5)
        
        layout.addLayout(btn_layout)
        
        # Add note about column limitations
        note = QLabel("Note: You need at least 3 columns and can have up to 5 columns.")
        note.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(note)
        
        # Build form after creating all UI elements
        self.rebuildColumnForm()
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.saveColumnTitles)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def addColumnInput(self, column, index=None):
        """Add a column input to the form"""
        row_widget = QFrame()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_widget.setLayout(row_layout)
        
        # Text input
        column_input = QLineEdit()
        column_input.setText(column["title"])
        column_input.setPlaceholderText("Column Title")
        row_layout.addWidget(column_input)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)
        
        # Move up button
        move_up_btn = QPushButton("↑")
        move_up_btn.setFixedWidth(30)
        move_up_btn.clicked.connect(lambda: self.moveColumnUp(row_widget))
        buttons_layout.addWidget(move_up_btn)
        
        # Move down button
        move_down_btn = QPushButton("↓")
        move_down_btn.setFixedWidth(30)
        move_down_btn.clicked.connect(lambda: self.moveColumnDown(row_widget))
        buttons_layout.addWidget(move_down_btn)
        
        # Remove button (only enabled if we have more than 3 columns)
        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self.removeColumn(row_widget))
        remove_btn.setEnabled(len(self.current_columns) > 3)
        buttons_layout.addWidget(remove_btn)
        
        row_layout.addLayout(buttons_layout)
        
        # Store references to widgets
        row_widget.column_input = column_input
        row_widget.column_id = column["id"]
        row_widget.move_up_btn = move_up_btn
        row_widget.move_down_btn = move_down_btn
        row_widget.remove_btn = remove_btn
        
        # Insert at position or add to end
        if index is not None and index < self.columns_layout.count():
            self.columns_layout.insertWidget(index, row_widget)
        else:
            self.columns_layout.addWidget(row_widget)
            
        return row_widget
    
    def rebuildColumnForm(self):
        """Rebuild the column form based on current columns"""
        # Clear existing form
        while self.columns_layout.count():
            widget = self.columns_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        
        # Add inputs for each column
        for column in self.current_columns:
            self.addColumnInput(column)
        
        # Update button states
        self.updateButtonStates()
    
    def updateButtonStates(self):
        """Update button states based on current columns"""
        # Get all column rows
        column_rows = []
        for i in range(self.columns_layout.count()):
            widget = self.columns_layout.itemAt(i).widget()
            if widget:
                column_rows.append(widget)
        
        # Update move up/down buttons
        for i, row in enumerate(column_rows):
            # First row can't move up
            row.move_up_btn.setEnabled(i > 0)
            # Last row can't move down
            row.move_down_btn.setEnabled(i < len(column_rows) - 1)
            # Can only remove if we have more than 3 columns
            row.remove_btn.setEnabled(len(column_rows) > 3)
        
        # Update add column button
        self.add_column_btn.setEnabled(len(column_rows) < 5)
    
    def moveColumnUp(self, row_widget):
        """Move a column up in the form"""
        # Find index of row
        index = -1
        for i in range(self.columns_layout.count()):
            if self.columns_layout.itemAt(i).widget() == row_widget:
                index = i
                break
        
        if index <= 0:
            return  # Already at the top
        
        # Swap columns in the data
        self.current_columns[index], self.current_columns[index-1] = self.current_columns[index-1], self.current_columns[index]
        
        # Rebuild form
        self.rebuildColumnForm()
    
    def moveColumnDown(self, row_widget):
        """Move a column down in the form"""
        # Find index of row
        index = -1
        for i in range(self.columns_layout.count()):
            if self.columns_layout.itemAt(i).widget() == row_widget:
                index = i
                break
        
        if index < 0 or index >= self.columns_layout.count() - 1:
            return  # Already at the bottom or not found
        
        # Swap columns in the data
        self.current_columns[index], self.current_columns[index+1] = self.current_columns[index+1], self.current_columns[index]
        
        # Rebuild form
        self.rebuildColumnForm()
    
    def removeColumn(self, row_widget):
        """Remove a column from the form"""
        # Check that we have more than 3 columns
        if self.columns_layout.count() <= 3:
            return
        
        # Find index of row
        index = -1
        for i in range(self.columns_layout.count()):
            if self.columns_layout.itemAt(i).widget() == row_widget:
                index = i
                break
        
        if index < 0:
            return  # Not found
        
        # Remove from the data
        self.current_columns.pop(index)
        
        # Rebuild form
        self.rebuildColumnForm()
    
    def addColumn(self):
        """Add a new column to the form"""
        # Check that we have less than 5 columns
        if self.columns_layout.count() >= 5:
            return
        
        # Create a unique ID for the new column
        import uuid
        new_id = str(uuid.uuid4())[:8]
        
        # Add to the data
        self.current_columns.append({"id": new_id, "title": "New Column"})
        
        # Rebuild form
        self.rebuildColumnForm()
    
    def saveColumnTitles(self):
        """Save column titles from the form"""
        # Update column titles from the form
        for i in range(self.columns_layout.count()):
            widget = self.columns_layout.itemAt(i).widget()
            if widget:
                self.current_columns[i]["title"] = widget.column_input.text()
        
        # Save to program-specific configuration
        self.db.save_program_kanban_config(self.program_id, self.current_columns)
        
        # Update the Kanban board UI
        self.kanban_board.createColumns()
        self.kanban_board.loadTasks()
        
        # Close the dialog
        self.accept()
        
        # Inform the user
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Settings Saved", 
                               "Kanban board columns have been updated.")


# Import needed for drag and drop
from PyQt5.QtWidgets import QApplication
