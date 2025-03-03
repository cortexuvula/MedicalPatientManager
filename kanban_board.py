from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QInputDialog,
                             QTextEdit, QDialog, QLineEdit, QFormLayout, QMessageBox,
                             QTabWidget, QApplication, QDialogButtonBox)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QPoint, QTimer, QSettings
from PyQt5.QtGui import QDrag, QFont, QPixmap, QCursor

from models import Task, Program


class TaskWidget(QFrame):
    """Widget representing a task in the Kanban board."""
    
    # Add signals for edit and delete
    edit_clicked = pyqtSignal(object)  # Signal when edit button is clicked (with task object)
    delete_clicked = pyqtSignal(object)  # Signal when delete button is clicked (with task object)
    
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_version = task.version  # Store the current task version
        self.initUI()
    
    def initUI(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        self.setAcceptDrops(True)  # Enable drops for vertical reordering
        
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
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFixedWidth(60)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
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
        
        # Include both task ID and type of drag (vertical or horizontal)
        task_data = f"{self.task.id}:task"
        mime_data.setText(task_data)
        drag.setMimeData(mime_data)
        
        # Create a pixmap representation of the widget for the drag
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Start drag operation
        drag.exec_(Qt.MoveAction)
    
    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasText() and ":task" in mime_data.text():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasText() and ":task" in mime_data.text():
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
            elif ":task" in text:
                # Extract task ID
                task_id = int(text.split(":", 1)[0])
                
                # If dropped directly on the column (not on a task)
                # Find the nearest task based on drop position
                drop_position = event.pos().y()
                insert_index = 0  # Default to top position
                
                # Find the index where the task should be inserted
                for i in range(self.tasks_layout.count()):
                    item = self.tasks_layout.itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), TaskWidget):
                        widget = item.widget()
                        widget_pos = widget.mapTo(self, QPoint(0, 0)).y()
                        widget_height = widget.height()
                        widget_center = widget_pos + widget_height / 2
                        
                        if drop_position < widget_center:
                            # Found the position - drop before this widget
                            break
                        insert_index = i + 1
                
                # Handle the drop - either status change or reordering
                source_task = None
                for column in self.parent().findChildren(KanbanColumn):
                    for i in range(column.tasks_layout.count()):
                        item = column.tasks_layout.itemAt(i)
                        if item and item.widget() and isinstance(item.widget(), TaskWidget):
                            task_widget = item.widget()
                            if task_widget.task.id == task_id:
                                source_task = task_widget.task
                                break
                    if source_task:
                        break
                
                if source_task and source_task.status != self.status:
                    # Status change (moved to different column)
                    self.taskDropped.emit(task_id, self.status)
                else:
                    # Reordering within the same column
                    self.taskReordered.emit(task_id, insert_index)
            else:
                # Legacy support for old format (just task ID)
                task_id = int(text)
                self.taskDropped.emit(task_id, self.status)
        
        event.acceptProposedAction()
    
    def _on_edit_clicked(self):
        """Emit signal when edit button is clicked."""
        self.edit_clicked.emit(self.task)
    
    def _on_delete_clicked(self):
        """Emit signal when delete button is clicked."""
        self.delete_clicked.emit(self.task)


class KanbanColumn(QWidget):
    """Widget representing a column in the Kanban board."""
    taskDropped = pyqtSignal(int, str)  # Task ID, new status
    columnMoved = pyqtSignal(str, int)  # Column ID, new position
    taskReordered = pyqtSignal(int, int)  # Task ID, new position
    taskDoubleClicked = pyqtSignal(object)  # Signals when a task is double-clicked (task_object)
    taskAdded = pyqtSignal(str)  # Signal to add a task to this status
    
    def __init__(self, status, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.status = status  # The status this column represents (todo, in_progress, etc.)
        self.setAcceptDrops(True)
        
        # We'll implement our own drag functionality
        
        self.initUI()
    
    def initUI(self):
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
                background-color: #e0f0f0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
            }
            
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        
        # Install event filter for the header to handle mouse events for dragging
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
            elif ":task" in text:
                # This is a task being dragged
                event.acceptProposedAction()
            else:
                # Legacy support for old format (just task ID)
                event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        # Accept drag move events to enable proper drop positioning
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
            elif ":task" in text:
                # Extract task ID
                task_id = int(text.split(":", 1)[0])
                
                # If dropped directly on the column (not on a task)
                # Find the nearest task based on drop position
                drop_position = event.pos().y()
                insert_index = 0  # Default to top position
                
                # Find the index where the task should be inserted
                for i in range(self.tasks_layout.count()):
                    item = self.tasks_layout.itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), TaskWidget):
                        widget = item.widget()
                        widget_pos = widget.mapTo(self, QPoint(0, 0)).y()
                        widget_height = widget.height()
                        widget_center = widget_pos + widget_height / 2
                        
                        if drop_position < widget_center:
                            # Found the position - drop before this widget
                            break
                        insert_index = i + 1
                
                # Handle the drop - either status change or reordering
                source_task = None
                for column in self.parent().findChildren(KanbanColumn):
                    for i in range(column.tasks_layout.count()):
                        item = column.tasks_layout.itemAt(i)
                        if item and item.widget() and isinstance(item.widget(), TaskWidget):
                            task_widget = item.widget()
                            if task_widget.task.id == task_id:
                                source_task = task_widget.task
                                break
                    if source_task:
                        break
                
                if source_task and source_task.status != self.status:
                    # Status change (moved to different column)
                    self.taskDropped.emit(task_id, self.status)
                else:
                    # Reordering within the same column
                    self.taskReordered.emit(task_id, insert_index)
            else:
                # Legacy support for old format (just task ID)
                task_id = int(text)
                self.taskDropped.emit(task_id, self.status)
        
        event.acceptProposedAction()

    def onTaskDoubleClicked(self, item):
        """Handle double-click on a task item."""
        # Get the task data stored in the item
        task = item.data(Qt.UserRole)
        # Emit signal with the task
        self.taskDoubleClicked.emit(task)


class KanbanBoard(QWidget):
    """Widget representing a Kanban board."""
    
    refreshRequired = pyqtSignal()  # Signal to indicate a refresh is needed
    
    def __init__(self, db, program_id, parent=None):
        """Initialize KanbanBoard with the database and program ID."""
        super().__init__(parent)
        self.db = db
        self.program_id = program_id
        self.config = QSettings("MedicalPatientManager", "KanbanBoard")
        
        # Get conflict resolution mode from user settings or use default
        self.conflict_resolution_mode = self.config.value(
            "conflict_resolution_mode", 
            "last_wins"
        )
        
        # Get refresh interval from user settings or use default (5 seconds)
        self.refresh_interval = int(self.config.value(
            "refresh_interval", 
            5000
        ))
        
        # Dictionary to track task versions
        self.task_versions = {}
        
        # Dictionary to store columns by ID
        self.columns = {}  # This makes columns a dictionary
        
        # Setup the UI
        self.initUI()
        
        # Load tasks
        self.loadTasks()
        
        # Setup refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.checkForUpdates)
        self.refresh_timer.start(self.refresh_interval)
    
    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel(f"{self.db.get_program_by_id(self.program_id).name}")
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
        self.createColumns()
    
    def createColumns(self):
        """Create columns for the kanban board based on configuration."""
        print("Creating kanban columns...")
        try:
            # First, remove the existing columns
            for i in reversed(range(self.columns_layout.count())):
                item = self.columns_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)
            
            # Clear the columns dictionary
            self.columns = {}
            
            # Get column configuration based on current program
            column_configs = self.db.get_program_kanban_config(self.program_id)
            print(f"Retrieved program kanban config: {column_configs}")
            
            # If no program-specific config exists, use global config
            if column_configs is None:
                print("No program-specific config, using global config")
                # Get column configuration from general settings
                kanban_config = self.config.value("kanban_columns", [])
                
                # Handle old configuration format (dictionary with key-value pairs)
                if isinstance(kanban_config, dict):
                    print("Converting old dictionary config format to list")
                    # Convert old format to new format
                    column_configs = [{"id": column_id, "title": kanban_config[column_id]} for column_id in kanban_config]
                # Handle new configuration format (list of objects)
                elif isinstance(kanban_config, list):
                    print("Using list config format")
                    column_configs = kanban_config
            
            # If no valid configuration (empty list or none), use defaults
            if not column_configs:
                print("No valid config found, using default columns")
                column_configs = [
                    {"id": "todo", "title": "To Do"},
                    {"id": "in_progress", "title": "In Progress"},
                    {"id": "done", "title": "Done"}
                ]
            
            # Now create the columns
            for config in column_configs:
                print(f"Creating column: {config}")
                column = KanbanColumn(title=config["title"], status=config["id"])
                column.taskDropped.connect(self.onTaskDropped)
                column.taskReordered.connect(self.onTaskReordered)
                column.taskDoubleClicked.connect(self.editTask)  # Connect to taskDoubleClicked signal
                column.taskAdded.connect(self.addTask)  # Connect to taskAdded signal
                column.columnMoved.connect(self.onColumnMoved)
                self.columns_layout.addWidget(column)
                self.columns[config["id"]] = column
                
            print(f"Created {len(self.columns)} columns")
            # Load tasks after creating columns
            if hasattr(self, 'tasks'):
                self.loadTasks()
        except Exception as e:
            import traceback
            print(f"Error creating columns: {e}")
            traceback.print_exc()
    
    def loadTasks(self):
        """Load tasks into columns."""
        # Get tasks for the program
        tasks = self.db.get_tasks_by_program(self.program_id)
        
        # Store current task versions for concurrency control
        self.task_versions = {task.id: task.version for task in tasks}
        
        # Group tasks by status
        tasks_by_status = {}
        for task in tasks:
            if task.status not in tasks_by_status:
                tasks_by_status[task.status] = []
            tasks_by_status[task.status].append(task)
        
        # Clear existing tasks in columns
        for column in self.columns.values():
            for i in reversed(range(column.tasks_layout.count())):
                item = column.tasks_layout.itemAt(i)
                if item.widget():
                    item.widget().setParent(None)
        
        # Add tasks to columns
        for status, column in self.columns.items():
            if status in tasks_by_status:
                # Sort tasks by order_index
                status_tasks = sorted(tasks_by_status[status], key=lambda t: t.order_index)
                for task in status_tasks:
                    task_widget = TaskWidget(task, parent=column)
                    # Connect the edit and delete signals
                    task_widget.edit_clicked.connect(self.editTask)
                    task_widget.delete_clicked.connect(self.deleteTask)
                    column.tasks_layout.addWidget(task_widget)
                    
        # Add spacer at the end of each column for proper spacing
        for column in self.columns.values():
            spacer = QWidget()
            from PyQt5.QtWidgets import QSizePolicy
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            column.tasks_layout.addWidget(spacer)
    
    def checkForUpdates(self):
        """Periodically check for updates to the kanban board."""
        # Only check if the widget is visible
        if not self.isVisible():
            return
            
        # Get current tasks from database
        current_tasks = self.db.get_tasks_by_program(self.program_id)
        
        # Extract tasks versions from database
        db_task_versions = {task.id: task.version for task in current_tasks}
        
        # Check for differences in versions
        needs_refresh = False
        
        # Look for tasks that were updated
        for task_id, db_version in db_task_versions.items():
            if task_id in self.task_versions:
                # Task exists in our local cache
                if db_version > self.task_versions[task_id]:
                    # Task was updated by another user
                    needs_refresh = True
                    break
            else:
                # New task was added
                needs_refresh = True
                break
                
        # Look for tasks that were deleted
        for task_id in self.task_versions:
            if task_id not in db_task_versions:
                # Task was deleted
                needs_refresh = True
                break
        
        # Refresh if needed
        if needs_refresh:
            self.refreshRequired.emit()
            self.loadTasks()
    
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
        """Edit an existing task with concurrency control."""
        # Check if the task version is current before editing
        current_task = self.db.get_task_by_id(task.id)
        if not current_task:
            QMessageBox.warning(self, "Task Not Found", 
                               f"The task '{task.name}' no longer exists and may have been deleted by another user.")
            self.loadTasks()
            return
        
        # Check for version conflict
        if current_task.version > task.version:
            # Task was modified by another user
            if self.conflict_resolution_mode == "last_wins":
                # Silently reload with the latest version
                self.loadTasks()
                QMessageBox.information(self, "Task Updated", 
                                       f"Task '{task.name}' was updated by another user. The latest version will be shown.")
                # Try to edit again with the latest version
                self.editTask(current_task)
                return
            else:
                # Manual conflict resolution
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"Task '{task.name}' has been modified by another user.")
                msg.setInformativeText("What would you like to do?")
                msg.setWindowTitle("Conflict Detected")
                
                btn_use_latest = msg.addButton("Use Latest Version", QMessageBox.ActionRole)
                btn_override = msg.addButton("Override with My Changes", QMessageBox.ActionRole)
                btn_cancel = msg.addButton("Cancel", QMessageBox.RejectRole)
                
                msg.exec_()
                
                if msg.clickedButton() == btn_use_latest:
                    # Reload with the latest version
                    self.loadTasks()
                    # Try to edit again with the latest version
                    self.editTask(current_task)
                    return
                elif msg.clickedButton() == btn_override:
                    # Force edit with current version
                    pass  # Continue with edit
                else:
                    # Cancel the edit
                    return
        
        # Show the edit dialog
        dialog = TaskDialog(task, parent=self)
        if dialog.exec_():
            task_data = dialog.getTaskData()
            task.name = task_data["name"]
            task.description = task_data["description"]
            
            # Update with version checking
            result = self.db.update_task(task, expected_version=task.version)
            
            if isinstance(result, dict) and result.get('conflict', False):
                QMessageBox.warning(self, "Update Conflict", 
                                   "The task was modified by another user while you were editing. Your changes were not saved.")
                self.loadTasks()
            elif result:
                # Update local version if successful
                if isinstance(result, dict) and 'new_version' in result:
                    self.task_versions[task.id] = result['new_version']
                self.loadTasks()
    
    def deleteTask(self, task):
        """Delete an existing task with concurrency control."""
        # Check if the task version is current before deleting
        current_task = self.db.get_task_by_id(task.id)
        if not current_task:
            QMessageBox.warning(self, "Task Not Found", 
                               f"The task '{task.name}' no longer exists and may have been deleted by another user.")
            self.loadTasks()
            return
            
        # Check for version conflict
        if current_task.version > task.version:
            QMessageBox.warning(self, "Task Modified", 
                               f"Task '{task.name}' has been modified by another user. Please refresh and try again.")
            self.loadTasks()
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete task '{task.name}'?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            result = self.db.delete_task(task.id)
            if result:
                # Remove from version tracking
                if task.id in self.task_versions:
                    del self.task_versions[task.id]
                self.loadTasks()
    
    def onTaskDropped(self, task_id, new_status):
        """Update task status when dropped into a new column with concurrency control."""
        # Get current task version
        task = self.db.get_task_by_id(task_id)
        if not task:
            QMessageBox.warning(self, "Task Not Found", 
                               "The task no longer exists and may have been deleted by another user.")
            self.loadTasks()
            return
            
        current_version = task.version
        expected_version = self.task_versions.get(task_id, current_version)
        
        # Update with version checking
        result = self.db.update_task_status(task_id, new_status, expected_version=expected_version)
        
        if isinstance(result, dict) and result.get('conflict', False):
            QMessageBox.warning(self, "Update Conflict", 
                               "The task was modified by another user. The board will refresh with the latest changes.")
            self.loadTasks()
        elif result:
            # Update local version if successful
            if isinstance(result, dict) and 'new_version' in result:
                self.task_versions[task_id] = result['new_version']
            self.loadTasks()
    
    def onTaskReordered(self, task_id, new_position):
        """Update task order when reordered within a column with concurrency control."""
        # Find the task to get its status and program_id
        task = None
        for column in self.columns.values():
            for i in range(column.tasks_layout.count()):
                item = column.tasks_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), TaskWidget):
                    task_widget = item.widget()
                    if task_widget.task.id == task_id:
                        task = task_widget.task
                        break
            if task:
                break
        
        if task:
            # Get expected version
            expected_version = self.task_versions.get(task_id, task.version)
            
            # Update the task order in the database with concurrency control
            result = self.db.reorder_tasks(self.program_id, task.status, task_id, new_position, expected_version=expected_version)
            
            if isinstance(result, dict) and result.get('conflict', False):
                QMessageBox.warning(self, "Reorder Conflict", 
                                   "The task order was modified by another user. The board will refresh with the latest changes.")
                self.loadTasks()
            elif result:
                # Update local version if successful
                if isinstance(result, dict) and 'new_version' in result:
                    self.task_versions[task_id] = result['new_version']
                self.loadTasks()
    
    def onColumnMoved(self, column_id, new_position):
        """Update column order when a column is moved."""
        # Get the program-specific column configuration
        column_configs = self.db.get_program_kanban_config(self.program_id)
        
        # If no program-specific config exists, get from global config
        if column_configs is None:
            # Get column configuration from global config
            kanban_config = self.config.value("kanban_columns", [])
            
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
        self.loadTasks()
        
        # Inform the user
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Settings Saved", 
                               "Kanban board columns have been updated.")
    
    def setConflictResolutionMode(self, mode):
        """Set the conflict resolution mode.
        
        Args:
            mode (str): Either "last_wins" or "manual_resolution"
        """
        if mode in ["last_wins", "manual_resolution"]:
            self.conflict_resolution_mode = mode
    
    def customizeColumns(self):
        """Customize the column titles and structure."""
        # Create the dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Customize Kanban Board")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Create tab widget for different settings
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Columns Tab
        columns_tab = QWidget()
        columns_layout = QVBoxLayout()
        columns_tab.setLayout(columns_layout)
        
        # Get program-specific column configuration
        column_configs = self.db.get_program_kanban_config(self.program_id)
        
        # If no program-specific config exists, get from global config
        if column_configs is None:
            # Get column configuration from general settings
            kanban_config = self.config.value("kanban_columns", [])
            
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
        
        # Create widgets for each column configuration
        column_widgets = []
        for i, column_config in enumerate(column_configs):
            column_id = column_config.get("id", f"column_{i}")
            title = column_config.get("title", f"Column {i+1}")
            
            row_layout = QHBoxLayout()
            
            # Column ID (read-only)
            id_label = QLabel(f"ID: {column_id}")
            row_layout.addWidget(id_label)
            
            # Column Title (editable)
            title_label = QLabel("Title:")
            row_layout.addWidget(title_label)
            
            title_edit = QLineEdit(title)
            row_layout.addWidget(title_edit)
            
            # Delete button
            from PyQt5.QtWidgets import QPushButton
            delete_btn = QPushButton("Delete")
            delete_btn.setProperty("column_index", i)
            delete_btn.clicked.connect(lambda checked, idx=i: self.deleteColumnFromCustomizeDialog(idx, column_configs))
            row_layout.addWidget(delete_btn)
            
            column_widgets.append({"id": column_id, "title_edit": title_edit})
            
            columns_layout.addLayout(row_layout)
        
        # Add columns tab
        tab_widget.addTab(columns_tab, "Columns")
        
        # Concurrency Settings Tab
        concurrency_tab = QWidget()
        concurrency_layout = QVBoxLayout()
        concurrency_tab.setLayout(concurrency_layout)
        
        # Conflict Resolution Mode
        conflict_mode_layout = QHBoxLayout()
        conflict_mode_label = QLabel("Conflict Resolution Mode:")
        conflict_mode_layout.addWidget(conflict_mode_label)
        
        from PyQt5.QtWidgets import QComboBox
        
        conflict_mode_combo = QComboBox()
        conflict_mode_combo.addItem("Last Writer Wins (Automatic)", "last_wins")
        conflict_mode_combo.addItem("Manual Resolution (Ask User)", "manual_resolution")
        
        # Set current value
        current_mode_index = 0  # default to last_wins
        if self.conflict_resolution_mode == "manual_resolution":
            current_mode_index = 1
        conflict_mode_combo.setCurrentIndex(current_mode_index)
        
        conflict_mode_layout.addWidget(conflict_mode_combo)
        concurrency_layout.addLayout(conflict_mode_layout)
        
        # Explanation of modes
        explanation = QLabel(
            "Last Writer Wins: Changes by the most recent user automatically override previous changes.\n"
            "Manual Resolution: When conflicts occur, you'll be asked how to resolve them."
        )
        explanation.setWordWrap(True)
        concurrency_layout.addWidget(explanation)
        
        # Add concurrency tab
        tab_widget.addTab(concurrency_tab, "Concurrency Settings")
        
        # Add spacer
        concurrency_layout.addStretch()
        
        # Refresh interval setting
        refresh_layout = QHBoxLayout()
        refresh_label = QLabel("Auto-refresh interval (seconds):")
        refresh_layout.addWidget(refresh_label)
        
        from PyQt5.QtWidgets import QSpinBox
        
        refresh_interval_spinner = QSpinBox()
        refresh_interval_spinner.setMinimum(1)
        refresh_interval_spinner.setMaximum(60)
        refresh_interval_spinner.setValue(int(self.refresh_timer.interval() / 1000))
        refresh_layout.addWidget(refresh_interval_spinner)
        
        concurrency_layout.addLayout(refresh_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Execute dialog
        if dialog.exec_():
            # Process column configurations
            updated_configs = []
            for widget in column_widgets:
                updated_configs.append({
                    "id": widget["id"],
                    "title": widget["title_edit"].text()
                })
            
            # Save the program-specific column configuration
            self.db.save_program_kanban_config(self.program_id, updated_configs)
            
            # Update conflict resolution mode
            new_mode = conflict_mode_combo.currentData()
            self.setConflictResolutionMode(new_mode)
            
            # Update refresh interval
            new_interval = refresh_interval_spinner.value() * 1000  # convert to milliseconds
            self.refresh_timer.setInterval(new_interval)
            
            # Recreate columns with new configuration
            self.createColumns()
            
            # Reload tasks
            self.loadTasks()
            
            # Notify user
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Settings Saved", 
                               "Kanban board settings have been updated.")
    
    def editProgram(self):
        """Edit the program name."""
        name, ok = QInputDialog.getText(self, "Edit Program", 
                                     "Program Name:", text=self.db.get_program_by_id(self.program_id).name)
        if ok and name:
            self.db.update_program(Program(name=name, id=self.program_id))
            # Update the tab text
            parent = self.parent()
            if isinstance(parent, QTabWidget):
                index = parent.indexOf(self)
                parent.setTabText(index, name)

    def deleteColumnFromCustomizeDialog(self, index, column_configs):
        """Delete a column from the kanban board.
        
        Args:
            index: Index of the column to delete
            column_configs: List of column configurations
        """
        # Check if we have enough columns to delete one
        if len(column_configs) <= 3:
            QMessageBox.warning(self, "Cannot Delete Column", 
                              "You must have at least 3 columns in your Kanban board.")
            return
            
        # Confirm with user
        column_to_delete = column_configs[index]
        
        # Get tasks in this column directly from the database
        program_tasks = self.db.get_tasks_by_program(self.program_id)
        tasks_in_column = [task for task in program_tasks if task.status == column_to_delete["id"]]
        
        message = f"Are you sure you want to delete the column '{column_to_delete['title']}'?"
        if tasks_in_column:
            message += f"\n\nThis column contains {len(tasks_in_column)} tasks that will be moved to the first available column."
        
        confirm = QMessageBox.question(
            self, 
            "Confirm Column Deletion", 
            message, 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Get the ID of the column being deleted
            deleted_column_id = column_configs[index]["id"]
            
            # Remove the column from the configuration
            column_configs.pop(index)
            
            # Save the updated configuration
            self.db.save_program_kanban_config(self.program_id, column_configs)
            
            # If there are tasks in the deleted column, move them to the first column
            if column_configs and tasks_in_column:
                first_column_id = column_configs[0]["id"]
                
                # Update task statuses in database
                for task in tasks_in_column:
                    task.status = first_column_id
                    self.db.update_task_status(task.id, first_column_id)
            
            # Recreate columns with the updated configuration
            self.createColumns()
            
            # Reload tasks to reflect the changes
            self.loadTasks()
            
            # Close the customize columns dialog by finding and closing it
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, QDialog) and widget.windowTitle() == "Customize Kanban Board":
                    widget.close()
                    break


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
