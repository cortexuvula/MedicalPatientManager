from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QInputDialog,
                             QTextEdit, QDialog, QLineEdit, QFormLayout, QMessageBox,
                             QTabWidget, QApplication, QDialogButtonBox)
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
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
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
    
    def setTitle(self, title):
        """Set the column title."""
        self.title = title
        self.title_label.setText(title)
    
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
        """Create columns based on configuration."""
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
        
        # Get column configuration
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
        """Customize column titles."""
        from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, QDialogButtonBox, 
                                    QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QFrame)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Customize Kanban Columns")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Add description
        description = QLabel("Customize the titles of your Kanban board columns:")
        layout.addWidget(description)
        
        # Get current values from config
        kanban_config = self.config.get("kanban_columns", [])
        self.current_columns = []
        
        # Handle old configuration format (dictionary with key-value pairs)
        if isinstance(kanban_config, dict):
            # Convert old format to new format
            for column_id, column_title in kanban_config.items():
                self.current_columns.append({"id": column_id, "title": column_title})
        # Handle new configuration format (list of objects)
        elif isinstance(kanban_config, list):
            self.current_columns = kanban_config
        
        if not self.current_columns:
            # Fallback to default columns
            self.current_columns = [
                {"id": "todo", "title": "To Do"},
                {"id": "in_progress", "title": "In Progress"},
                {"id": "done", "title": "Done"}
            ]
        
        # Create a form container with scrollable area
        self.form_layout = QFormLayout()
        form_container = QFrame()
        form_container.setLayout(self.form_layout)
        
        # Add existing column inputs
        self.column_inputs = []
        for index, column in enumerate(self.current_columns):
            self.addColumnInput(column, index)
        
        layout.addWidget(form_container)
        
        # Add note about maximum columns
        max_note = QLabel("Note: Maximum 5 columns allowed")
        layout.addWidget(max_note)
        
        # Add buttons for adding/removing columns
        buttons_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Column")
        add_btn.clicked.connect(self.addColumn)
        buttons_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Last Column")
        remove_btn.clicked.connect(self.removeColumn)
        buttons_layout.addWidget(remove_btn)
        
        layout.addLayout(buttons_layout)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.saveColumnTitles)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Store dialog reference
        self.columns_dialog = dialog
        dialog.exec_()
    
    def addColumnInput(self, column, index=None):
        """Add a column input to the form"""
        column_id = column.get("id")
        column_title = column.get("title")
        
        row_layout = QHBoxLayout()
        
        # Create label and input
        label = QLabel(f"{column_id.capitalize()}:")
        input_field = QLineEdit(column_title)
        
        # Add to layout
        row_layout.addWidget(label)
        row_layout.addWidget(input_field)
        
        # Add up/down buttons for reordering
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtGui import QIcon
        from PyQt5.QtCore import QSize
        
        button_layout = QHBoxLayout()
        
        up_btn = QPushButton("↑")
        up_btn.setFixedSize(30, 25)
        up_btn.setToolTip("Move column up")
        up_btn.clicked.connect(lambda: self.moveColumnUp(column_id))
        
        down_btn = QPushButton("↓")
        down_btn.setFixedSize(30, 25)
        down_btn.setToolTip("Move column down")
        down_btn.clicked.connect(lambda: self.moveColumnDown(column_id))
        
        button_layout.addWidget(up_btn)
        button_layout.addWidget(down_btn)
        button_layout.setSpacing(1)
        
        row_layout.addLayout(button_layout)
        
        # Add the row to form
        if index is not None and index < self.form_layout.rowCount():
            self.form_layout.insertRow(index, row_layout)
        else:
            self.form_layout.addRow(row_layout)
        
        # Store the input field and buttons
        self.column_inputs.append({
            "id": column_id, 
            "input": input_field,
            "up_btn": up_btn,
            "down_btn": down_btn
        })
    
    def addColumn(self):
        """Add a new column to the form"""
        if len(self.column_inputs) >= 5:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Maximum Columns", 
                              "You can have a maximum of 5 columns.")
            return
        
        # Generate a unique ID
        column_id = f"column_{len(self.column_inputs) + 1}"
        column_title = f"New Column {len(self.column_inputs) + 1}"
        
        # Add to current columns
        new_column = {"id": column_id, "title": column_title}
        self.current_columns.append(new_column)
        
        # Add to form
        self.addColumnInput(new_column)
    
    def removeColumn(self):
        """Remove the last column"""
        if len(self.column_inputs) <= 3:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Minimum Columns", 
                              "You must have at least 3 columns.")
            return
        
        # Get the last column index
        last_index = len(self.column_inputs) - 1
        
        # Remove the last input and its widgets
        last_column = self.column_inputs[last_index]
        last_column["input"].setParent(None)
        last_column["up_btn"].setParent(None)
        last_column["down_btn"].setParent(None)
        
        # Remove from inputs
        self.column_inputs.pop()
        
        # Remove from current columns
        self.current_columns.pop()
        
        # Remove the last row from form
        if self.form_layout.rowCount() > 0:
            # Get the layout at the last row
            row_index = self.form_layout.rowCount() - 1
            layout_item = self.form_layout.itemAt(row_index, QFormLayout.SpanningRole)
            
            if layout_item:
                # Remove all widgets from the layout
                layout = layout_item.layout()
                if layout:
                    while layout.count():
                        item = layout.takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.setParent(None)
                        sublayout = item.layout()
                        if sublayout:
                            while sublayout.count():
                                subitem = sublayout.takeAt(0)
                                subwidget = subitem.widget()
                                if subwidget:
                                    subwidget.setParent(None)
            
            # Remove the row
            self.form_layout.removeRow(row_index)
    
    def saveColumnTitles(self):
        """Save the custom column titles to config and update the UI."""
        from config import Config
        
        # Get the current configuration
        config = Config.load_config()
        
        # Update column configuration
        new_columns = []
        for column_data in self.column_inputs:
            column_id = column_data["id"]
            column_title = column_data["input"].text()
            new_columns.append({"id": column_id, "title": column_title})
        
        config["kanban_columns"] = new_columns
        
        # Save the updated configuration
        Config.save_config(config)
        
        # Update the column titles in the UI
        self.createColumns()
        
        # Reload tasks
        self.loadTasks()
        
        # Close the dialog
        self.columns_dialog.accept()
        
        # Inform the user
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Settings Saved", 
                               "Kanban board columns have been updated.")
    
    def moveColumnUp(self, column_id):
        """Move the column up in order"""
        # Find the column index
        for index, column in enumerate(self.column_inputs):
            if column["id"] == column_id:
                if index > 0:  # Not already at the top
                    # Swap in the column_inputs list
                    self.column_inputs[index], self.column_inputs[index - 1] = (
                        self.column_inputs[index - 1], self.column_inputs[index]
                    )
                    
                    # Swap in the current_columns list
                    self.current_columns[index], self.current_columns[index - 1] = (
                        self.current_columns[index - 1], self.current_columns[index]
                    )
                    
                    # Rebuild the form
                    self.rebuildColumnForm()
                break
    
    def moveColumnDown(self, column_id):
        """Move the column down in order"""
        # Find the column index
        for index, column in enumerate(self.column_inputs):
            if column["id"] == column_id:
                if index < len(self.column_inputs) - 1:  # Not already at the bottom
                    # Swap in the column_inputs list
                    self.column_inputs[index], self.column_inputs[index + 1] = (
                        self.column_inputs[index + 1], self.column_inputs[index]
                    )
                    
                    # Swap in the current_columns list
                    self.current_columns[index], self.current_columns[index + 1] = (
                        self.current_columns[index + 1], self.current_columns[index]
                    )
                    
                    # Rebuild the form
                    self.rebuildColumnForm()
                break
    
    def rebuildColumnForm(self):
        """Rebuild the form layout with the current column order"""
        # Save the current values
        current_values = {}
        for column in self.column_inputs:
            current_values[column["id"]] = column["input"].text()
        
        # Clear the form layout
        while self.form_layout.rowCount() > 0:
            # Get the layout at row 0
            layout_item = self.form_layout.itemAt(0, QFormLayout.SpanningRole)
            if layout_item:
                # Remove all widgets from the layout
                layout = layout_item.layout()
                if layout:
                    while layout.count():
                        item = layout.takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.setParent(None)
                        sublayout = item.layout()
                        if sublayout:
                            while sublayout.count():
                                subitem = sublayout.takeAt(0)
                                subwidget = subitem.widget()
                                if subwidget:
                                    subwidget.setParent(None)
            
            # Remove the row
            self.form_layout.removeRow(0)
        
        # Reset column_inputs
        self.column_inputs = []
        
        # Rebuild the form with the new order
        for column in self.current_columns:
            column_id = column.get("id")
            column_title = current_values.get(column_id, column.get("title"))
            column_data = {"id": column_id, "title": column_title}
            self.addColumnInput(column_data)


# Import needed for drag and drop
from PyQt5.QtWidgets import QApplication
