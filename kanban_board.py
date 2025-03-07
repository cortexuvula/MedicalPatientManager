from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QInputDialog,
                             QTextEdit, QDialog, QLineEdit, QFormLayout, QMessageBox,
                             QTabWidget, QApplication, QDialogButtonBox, QComboBox, QSpinBox,
                             QColorDialog, QSizePolicy, QToolButton)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QPoint, QTimer, QSettings, QSize
from PyQt5.QtGui import QDrag, QFont, QPixmap, QCursor, QColor, QPainter, QPen
import copy

from models import Task, Program


class TaskWidget(QFrame):
    """Widget representing a task in the kanban board."""
    
    doubleClicked = pyqtSignal(object)  # Signal when the task is double-clicked
    moveTask = pyqtSignal(int, str)  # Signal to move a task (task_id, new_status)
    edit_clicked = pyqtSignal(object)  # Signal when edit button is clicked
    delete_clicked = pyqtSignal(object)  # Signal when delete button is clicked
    
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_version = task.version  # Store the current task version
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(1)
        
        # Set cursor to indicate it's draggable
        self.setCursor(Qt.PointingHandCursor)
        
        # Allow the task to be dragged
        self.setAcceptDrops(True)  # Enable drops for vertical reordering
        
        # Set fixed height
        self.setMinimumHeight(100)
        self.setMaximumHeight(200)
        self.setMinimumWidth(180)
        
        # Set style with task color and a priority border color
        priority_colors = {
            "High": "#e74c3c",   # Red for high priority
            "Medium": "#f39c12", # Orange for medium priority
            "Low": "#2ecc71"     # Green for low priority
        }
        
        priority_color = priority_colors.get(task.priority, priority_colors["Medium"])
        task_color = task.color if hasattr(task, 'color') and task.color else "#ffffff"
        
        self.setStyleSheet(f"""
            TaskWidget {{
                background-color: {task_color};
                border: 1px solid #d0d0d0;
                border-left: 6px solid {priority_color};
                border-radius: 6px;
                padding: 8px;
                margin: 4px;
            }}
        """)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Task name (first line, bold)
        self.name_label = QLabel(task.name)
        self.name_label.setWordWrap(True)
        self.name_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.name_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(self.name_label)
        
        # Priority indicator - simplified approach with direct styling
        priority_text = task.priority + " Priority"
        priority_label = QLabel(priority_text)
        priority_label.setFixedHeight(36)
        priority_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        priority_label.setFont(QFont("Segoe UI", 10))
        priority_label.setAlignment(Qt.AlignCenter)
        priority_label.setStyleSheet(f"""
            background-color: {priority_color};
            color: white;
            border-radius: 5px;
            padding: 4px;
            margin: 3px 0px;
            font-weight: bold;
        """)
        layout.addWidget(priority_label)
        
        # Description (additional lines if available)
        if task.description:
            desc_text = task.description
            if len(desc_text) > 100:
                desc_text = desc_text[:97] + "..."
                
            self.desc_label = QLabel(desc_text)
            self.desc_label.setWordWrap(True)
            self.desc_label.setFont(QFont("Segoe UI", 9))
            self.desc_label.setStyleSheet("color: #34495e; margin-top: 4px;")
            layout.addWidget(self.desc_label)
        
        # Add spacing before buttons
        layout.addSpacing(5)
        
        # Task actions
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(60, 28)
        edit_btn.setFont(QFont("Segoe UI", 8))
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c5b8c;
            }
        """)
        edit_btn.clicked.connect(self._on_edit_clicked)
        action_layout.addWidget(edit_btn)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(60, 28)
        delete_btn.setFont(QFont("Segoe UI", 8))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #922b21;
            }
        """)
        delete_btn.clicked.connect(self._on_delete_clicked)
        action_layout.addWidget(delete_btn)
        
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
    
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
        
        # Include both task ID and type of drag
        task_data = f"{self.task.id}:task"
        mime_data.setText(task_data)
        drag.setMimeData(mime_data)
        
        # Create a pixmap of the task for drag visualization
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        # Execute drag
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
            if ":task" in text:
                # Extract task ID
                task_id = int(text.split(":", 1)[0])
                
                # Find the parent KanbanColumn
                parent = self.parent()
                while parent and not isinstance(parent, KanbanColumn):
                    parent = parent.parent()
                
                if parent and isinstance(parent, KanbanColumn):
                    # Find the index where the task should be inserted
                    this_idx = -1
                    for i in range(parent.tasks_layout.count()):
                        item = parent.tasks_layout.itemAt(i)
                        if item and item.widget() == self:
                            this_idx = i
                            break
                    
                    if this_idx >= 0:
                        # Signal to the column that a task has been dropped for reordering
                        parent.taskReordered.emit(task_id, this_idx)
                        
        event.acceptProposedAction()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to open task editor."""
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit(self.task)
    
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
    
    def __init__(self, status, title, color="#f0f0f0", parent=None):
        super().__init__(parent)
        self.title = title
        self.status = status  # The status this column represents (todo, in_progress, etc.)
        self.color = color  # Background color for the column
        self.setAcceptDrops(True)
        
        # Drop indicator flag
        self.drop_indicator_visible = False
        self.drop_indicator_side = None  # "left" or "right"
        
        self.initUI()
    
    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)
        
        # Set size policy to expand horizontally and vertically
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set the column background color with a more professional appearance
        self.setStyleSheet(f"""
            QWidget {{ 
                background-color: {self.color}; 
                border-radius: 8px;
                border: 1px solid #d0d0d0;
            }}
        """)
        
        # Create a header container with styling
        header_container = QFrame()
        header_container.setMinimumHeight(40)
        header_container.setMaximumHeight(40)
        header_container.setObjectName("headerContainer")
        header_container.setStyleSheet(f"""
            #headerContainer {{
                background-color: {self.darken_color(self.color, 0.05)};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #d0d0d0;
            }}
            
            #headerContainer:hover {{
                background-color: {self.darken_color(self.color, 0.1)};
            }}
        """)
        
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        # Create a drag handle container to highlight it better
        drag_handle_container = QFrame()
        drag_handle_container.setFixedSize(24, 24)
        drag_handle_container.setObjectName("dragHandleContainer")
        drag_handle_container.setStyleSheet("""
            #dragHandleContainer {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 4px;
                border: none;
            }
            #dragHandleContainer:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)
        drag_handle_layout = QHBoxLayout(drag_handle_container)
        drag_handle_layout.setContentsMargins(0, 0, 0, 0)
        drag_handle_layout.setSpacing(0)
        
        # Add drag handle icon
        self.drag_handle = QLabel("☰")  # Unicode "trigram for heaven" symbol as a drag handle
        self.drag_handle.setFont(QFont("Segoe UI", 12))
        self.drag_handle.setStyleSheet("""
            color: #555;
            padding: 0px;
        """)
        self.drag_handle.setCursor(Qt.SizeAllCursor)  # Set cursor directly on widget instead of via stylesheet
        self.drag_handle.setAlignment(Qt.AlignCenter)
        self.drag_handle.setToolTip("Drag to reorder column")
        self.drag_handle.setMouseTracking(True)
        self.drag_handle.installEventFilter(self)
        
        drag_handle_layout.addWidget(self.drag_handle)
        header_layout.addWidget(drag_handle_container)
        
        # Title (click and drag to move)
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #2c3e50;")  # Remove cursor move since we have a dedicated handle
        self.title_label.setToolTip("Drag the handle to reorder column")
        
        # Title no longer needs to be draggable, we use just the handle
        header_layout.addWidget(self.title_label, 1)  # Give title expanding space
        
        # Add spacer to push the add button to the right
        header_layout.addStretch(1)
        
        # "+" button with manual vertical alignment adjustment
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        add_btn.setContentsMargins(0, 0, 0, 0)
        
        # Force white text color with !important to override any default styling
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white !important;
                border: none;
                border-radius: 14px;
                padding-bottom: 6px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #219653;
            }
        """)
        add_btn.clicked.connect(self.addTask)
        header_layout.addWidget(add_btn)
        
        main_layout.addWidget(header_container)
        
        # Scrollable area for tasks with improved styling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)  # Remove border
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.05);
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container for task widgets
        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet(f"background-color: {self.color};")
        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setAlignment(Qt.AlignTop)
        self.tasks_layout.setContentsMargins(5, 5, 5, 5)
        self.tasks_layout.setSpacing(10)  # Increased space between tasks
        self.tasks_container.setLayout(self.tasks_layout)
        
        scroll.setWidget(self.tasks_container)
        main_layout.addWidget(scroll)
    
    def darken_color(self, hex_color, factor=0.1):
        """Darken a hex color by a factor."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Darken
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def eventFilter(self, obj, event):
        """Handle mouse events for the column header."""
        if obj == self.drag_handle:
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                self.drag_start_position = event.pos()
                return True
            elif event.type() == event.MouseMove and event.buttons() & Qt.LeftButton:
                # Check if dragging has started
                if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                    return True
                
                # Create drag object
                drag = QDrag(self)  
                mime_data = QMimeData()
                mime_data.setText(f"kanban_column:{self.status}")
                drag.setMimeData(mime_data)
                
                # Create pixmap for dragging
                pixmap = self.grab()
                # Scale down pixmap for better visual during drag
                scaled_pixmap = pixmap.scaled(int(pixmap.width() * 0.8), int(pixmap.height() * 0.8), 
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
                drag.setPixmap(scaled_pixmap)
                # Adjust hotspot for more intuitive dragging
                drag.setHotSpot(QPoint(scaled_pixmap.width() // 2, 20))
                
                # Execute the drag
                drag.exec_(Qt.MoveAction)
                return True
                
        return super().eventFilter(obj, event)
    
    def paintEvent(self, event):
        """Override paint event to draw drop indicators when needed."""
        super().paintEvent(event)
        
        # If we're showing a drop indicator, draw it
        if self.drop_indicator_visible and self.drop_indicator_side:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Use a bright blue color for the indicator
            indicator_color = QColor("#2980b9")
            painter.setPen(QPen(indicator_color, 4))
            
            if self.drop_indicator_side == "left":
                # Draw indicator on left side
                painter.drawLine(0, 0, 0, self.height())
            else:  # right side
                # Draw indicator on right side
                painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
    
    def setTitle(self, title):
        """Set the column title."""
        self.title = title
        self.title_label.setText(title)
    
    def addTask(self):
        """Add a new task to this column by signalling the parent KanbanBoard."""
        # Find the KanbanBoard in the parent widget hierarchy
        parent = self.parent()
        while parent and not isinstance(parent, KanbanBoard):
            parent = parent.parent()
            
        if parent and isinstance(parent, KanbanBoard):
            parent.addTask(self.status)
        else:
            print("Error: Could not find KanbanBoard parent")
    
    def addTaskWidget(self, task_widget):
        """Add a task widget to this column."""
        self.tasks_layout.addWidget(task_widget)
        
        # Connect to the task widget's signals
        task_widget.doubleClicked.connect(self.onTaskDoubleClicked)
    
    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasText():
            text = mime_data.text()
            if text.startswith("kanban_column:"):
                # This is a column being dragged
                dragged_status = text.split(":", 1)[1]
                if dragged_status != self.status:  # Don't accept drag from self
                    event.acceptProposedAction()
                    # Show drop indicator
                    self.drop_indicator_visible = True
                    # Determine which side to show the indicator
                    self.drop_indicator_side = "left" if event.pos().x() < self.width() / 2 else "right"
                    self.update()  # Trigger repaint
            elif ":task" in text:
                # This is a task being dragged
                event.acceptProposedAction()
            else:
                # Legacy support for old format (just task ID)
                event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        # Accept drag move events to enable proper drop positioning
        mime_data = event.mimeData()
        if mime_data.hasText():
            text = mime_data.text()
            if text.startswith("kanban_column:"):
                dragged_status = text.split(":", 1)[1]
                if dragged_status != self.status:  # Don't accept drag from self
                    event.acceptProposedAction()
                    # Show drop indicator and update position
                    self.drop_indicator_visible = True
                    # Determine which side to show the indicator
                    self.drop_indicator_side = "left" if event.pos().x() < self.width() / 2 else "right"
                    self.update()  # Trigger repaint
            else:
                event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        """Hide drop indicator when drag leaves."""
        self.drop_indicator_visible = False
        self.update()  # Trigger repaint
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        # Hide drop indicator
        self.drop_indicator_visible = False
        self.update()  # Trigger repaint
        
        mime_data = event.mimeData()
        if mime_data.hasText():
            text = mime_data.text()
            if text.startswith("kanban_column:"):
                # Extract dragged column ID
                dragged_column_id = text.split(":", 1)[1]
                
                # Find the KanbanBoard parent
                kanban_board = None
                current = self
                while current:
                    if isinstance(current.parent(), QWidget) and hasattr(current.parent(), 'columns'):
                        kanban_board = current.parent()
                        break
                    current = current.parent()
                
                if kanban_board:
                    # Get visible columns in the correct order
                    all_columns = []
                    for i in range(kanban_board.columns_layout.count()):
                        item = kanban_board.columns_layout.itemAt(i)
                        if item and item.widget() and isinstance(item.widget(), KanbanColumn):
                            all_columns.append(item.widget())
                    
                    # Find the index of this column
                    target_index = -1
                    for i, col in enumerate(all_columns):
                        if col == self:
                            target_index = i
                            # Adjust target index based on drop position (left or right side)
                            if event.pos().x() > self.width() / 2:
                                target_index += 1  # Drop on right side moves to position after this column
                            break
                    
                    if target_index >= 0:
                        # Emit signal to move column
                        self.columnMoved.emit(dragged_column_id, target_index)
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
        
        # No need to update task counts anymore since we removed the counter
        # Update task counts for all columns after drop
        # if self.parent():
        #     for column in self.parent().findChildren(KanbanColumn):
        #         if hasattr(column, 'updateTaskCount'):
        #             column.updateTaskCount()
                
    def onTaskDoubleClicked(self, item):
        """Handle double-click on a task item."""
        # Get the task data stored in the item
        task = item.data(Qt.UserRole)
        # Emit signal with the task
        self.taskDoubleClicked.emit(task)


class KanbanBoard(QWidget):
    """Widget representing a Kanban board."""
    
    refreshRequired = pyqtSignal()  # Signal to indicate a refresh is needed
    
    def __init__(self, db, program_id, patient_id=None, parent=None):
        """Initialize KanbanBoard with the database and program ID."""
        super().__init__(parent)
        self.db = db
        self.program_id = program_id
        self.patient_id = patient_id
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
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        # Apply a clean background style to the board
        self.setStyleSheet("""
            QWidget#kanbanBoard {
                background-color: #f5f7fa;
                border-radius: 8px;
            }
        """)
        self.setObjectName("kanbanBoard")
        
        # Header with improved styling
        header_container = QFrame()
        header_container.setMaximumHeight(60)
        header_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fb;
                border-radius: 8px;
                border: 1px solid #e0e4e8;
            }
        """)
        
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Program title with better typography
        program_name = self.db.get_program_by_id(self.program_id).name
        title = QLabel(program_name)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        # Patient name (if available)
        if self.patient_id:
            try:
                patient = self.db.get_patient_by_id(self.patient_id)
                if patient:
                    patient_label = QLabel(f"Patient: {patient.first_name} {patient.last_name}")
                    patient_label.setFont(QFont("Segoe UI", 12))
                    patient_label.setStyleSheet("color: #34495e; margin-left: 15px;")
                    header_layout.addWidget(patient_label)
            except Exception as e:
                print(f"Error retrieving patient details: {e}")
        
        header_layout.addStretch()
        
        # Button container for better alignment
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Redesigned buttons for program management
        self.edit_program_btn = QPushButton("Edit Program")
        self.edit_program_btn.setFont(QFont("Segoe UI", 10))
        self.edit_program_btn.setCursor(Qt.PointingHandCursor)
        self.edit_program_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c5b8c;
            }
        """)
        self.edit_program_btn.clicked.connect(self.editProgram)
        button_layout.addWidget(self.edit_program_btn)
        
        # Button for customizing column titles with matching style
        self.customize_columns_btn = QPushButton("Customize Columns")
        self.customize_columns_btn.setFont(QFont("Segoe UI", 10))
        self.customize_columns_btn.setCursor(Qt.PointingHandCursor)
        self.customize_columns_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.customize_columns_btn.clicked.connect(self.customizeColumns)
        button_layout.addWidget(self.customize_columns_btn)
        
        header_layout.addWidget(button_container)
        layout.addWidget(header_container)
        
        # Kanban columns container with enhanced styling
        columns_container = QWidget()
        columns_container.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
                border-radius: 8px;
            }
        """)
        self.columns_layout = QHBoxLayout(columns_container)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(10)  # Add some space between columns
        self.columns_layout.setStretch(0, 1)  # Make columns stretch to fill available space
        
        # Add the container to the main layout - this will stretch to fill space
        layout.addWidget(columns_container, 1)  # Give it a stretch factor of 1 to expand
        
        # Create columns
        self.createColumns()
    
    def createColumns(self):
        """Create columns for the kanban board based on configuration."""
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
            
            # If no program-specific config exists, use global config
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
            
            # If no valid configuration (empty list or none), use defaults
            if not column_configs:
                column_configs = [
                    {"id": "todo", "title": "To Do", "color": "#f0f7ff"},         # Light blue for To Do
                    {"id": "in_progress", "title": "In Progress", "color": "#fff7e6"}, # Light orange for In Progress
                    {"id": "done", "title": "Done", "color": "#f0fff5"}           # Light green for Done
                ]
            
            # Define default colors for common column types if not specified in config
            default_colors = {
                "todo": "#f0f7ff",       # Light blue for To Do
                "backlog": "#f5f5f5",    # Light grey for Backlog
                "in_progress": "#fff7e6", # Light orange for In Progress
                "review": "#f5f0ff",     # Light purple for Review
                "testing": "#fff0f7",    # Light pink for Testing
                "done": "#f0fff5"        # Light green for Done
            }
            
            # Now create the columns with professional styling
            for config in column_configs:
                # Use default color based on column ID if no color specified
                column_id = config["id"].lower()
                color = config.get("color", default_colors.get(column_id, "#f5f7fa"))
                
                column = KanbanColumn(
                    title=config["title"], 
                    status=config["id"], 
                    color=color
                )
                
                # Connect signals
                column.taskDropped.connect(self.onTaskDropped)
                column.taskReordered.connect(self.onTaskReordered)
                column.taskDoubleClicked.connect(self.editTask)
                column.taskAdded.connect(self.addTask)
                column.columnMoved.connect(self.onColumnMoved)
                
                # Set a fixed minimum width for more consistent layout
                column.setMinimumWidth(250)
                
                # Add to layout with stretch factor
                self.columns_layout.addWidget(column, 1)
                self.columns[config["id"]] = column
                
            # Add stretch at the end to prevent columns from expanding too wide
            self.columns_layout.addStretch(0)
                
            # Load tasks after creating columns
            if hasattr(self, 'tasks'):
                self.loadTasks()
                
            # Update task counts for all columns
            for column in self.columns.values():
                if hasattr(column, 'updateTaskCount'):
                    column.updateTaskCount()
                    
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
                    task_widget.doubleClicked.connect(self.editTask)
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
                program_id=self.program_id,
                patient_id=self.patient_id if hasattr(self, 'patient_id') else None,
                priority=task_data["priority"],
                color=task_data["color"]
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
            task.priority = task_data["priority"]
            task.color = task_data["color"]
            
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
        """Handle a task being dropped in a new column (status change).
        
        Args:
            task_id: ID of the task being moved
            new_status: New status (column) for the task
        """
        # Get the task object
        task = self.db.get_task_by_id(task_id)
        if not task:
            print(f"Error: Task with ID {task_id} not found")
            return
            
        old_status = task.status
        if old_status == new_status:
            # No change in status
            return
            
        # Update the task status with version checking
        result = self.db.update_task_status(task_id, new_status, expected_version=task.version)
        success, conflict_data = result
        
        if not success:
            # Handle conflict based on conflict resolution mode
            if self.conflict_resolution_mode == "manual":
                self._showConflictDialog("The task has been modified by another user.", 
                                         "Would you like to override their changes?")
            # In "last_writer_wins" mode, we'll refresh the board which will show the latest state
        
        # Reload the tasks to reflect any changes
        self.loadTasks()
    
    def onTaskReordered(self, task_id, new_position):
        """Update task order when reordered within a column with concurrency control."""
        # Get current task version
        task = self.db.get_task_by_id(task_id)
        if not task:
            QMessageBox.warning(self, "Task Not Found", 
                              "The task no longer exists and may have been deleted by another user.")
            self.loadTasks()
            return
            
        # Update with version checking
        result = self.db.reorder_tasks(task_id, new_position, expected_version=task.version)
        success, conflict_data = result
        
        if not success:
            # Handle conflict based on conflict resolution mode
            if self.conflict_resolution_mode == "manual":
                QMessageBox.warning(self, "Update Conflict", 
                                   "The task was modified by another user. The board will refresh with the latest changes.")
            # In "last_writer_wins" mode, we'll refresh the board which will show the latest state
        
        # Reload the tasks to reflect any changes
        self.loadTasks()
    
    def onColumnMoved(self, column_id, new_position):
        """Update column order when a column is moved."""
        print(f"onColumnMoved called: {column_id} -> position {new_position}")
        
        # Get the program-specific column configuration
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
                    {"id": "todo", "title": "To Do", "color": "#f0f7ff"},         # Light blue for To Do
                    {"id": "in_progress", "title": "In Progress", "color": "#fff7e6"}, # Light orange for In Progress
                    {"id": "done", "title": "Done", "color": "#f0fff5"}           # Light green for Done
                ]
        
        # Print current configuration for debugging
        print(f"Current column configs before move: {column_configs}")
        
        # Find the column to move
        column_to_move = None
        original_index = -1
        
        for i, column in enumerate(column_configs):
            if column["id"] == column_id:
                column_to_move = column
                original_index = i
                break
        
        if column_to_move is None:
            print(f"Error: Column with ID {column_id} not found in configuration")
            return
            
        # Adjust new_position if it's invalid
        if new_position < 0:
            new_position = 0
        elif new_position >= len(column_configs):
            new_position = len(column_configs) - 1
        
        # Remove the column from its original position
        column_configs.pop(original_index)
        
        # Insert it at the new position
        column_configs.insert(new_position, column_to_move)
        
        print(f"New column configs after move: {column_configs}")
        
        # Save the updated program-specific configuration
        try:
            result = self.db.save_program_kanban_config(self.program_id, column_configs)
            print(f"Save result: {result}")
        except Exception as e:
            print(f"Error saving column config: {e}")
        
        # Update the column titles in the UI
        self.createColumns()
        self.loadTasks()
        
        # Handle tasks in deleted columns
        # Move them to the first column if they were in a deleted column
        if column_configs:
            first_column_id = column_configs[0]["id"]
            existing_column_ids = [config["id"] for config in column_configs]
            
            # Get all tasks for this program
            program_tasks = self.db.get_tasks_by_program(self.program_id)
            
            # Find tasks that are in a column that no longer exists
            for task in program_tasks:
                if task.status not in existing_column_ids:
                    # Move task to first column
                    self.db.update_task_status(task.id, first_column_id)
        
    def setConflictResolutionMode(self, mode):
        """Set the conflict resolution mode.
        
        Args:
            mode (str): Either "last_wins" or "manual_resolution"
        """
        if mode in ["last_wins", "manual_resolution"]:
            self.conflict_resolution_mode = mode
    
    def customizeColumns(self):
        """Open a dialog to customize kanban board columns."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Customize Kanban Board")
        dialog.setMinimumWidth(700)  # Increased from 500
        dialog.setMinimumHeight(500)  # Added minimum height
        
        # Apply styling to the dialog
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fb;
            }
            QLabel {
                font-family: 'Segoe UI';
                font-size: 11pt;
                color: #2c3e50;
            }
            QLineEdit, QComboBox, QSpinBox {
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                font-family: 'Segoe UI';
                font-size: 10pt;
                color: #2c3e50;
                selection-background-color: #3498db;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 0px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
        """)
        
        # Main layout for the dialog
        main_layout = QVBoxLayout(dialog)
        
        # Get current column configs
        column_configs = self.db.get_program_kanban_config(self.program_id)
        column_configs_copy = copy.deepcopy(column_configs)  # Make a copy to work with
        
        # Tab widget for different settings
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Columns tab
        columns_tab = QWidget()
        columns_tab_layout = QVBoxLayout()
        columns_tab.setLayout(columns_tab_layout)
        
        # Create a scroll area for columns
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        columns_layout = QVBoxLayout()
        container.setLayout(columns_layout)
        scroll.setWidget(container)
        columns_tab_layout.addWidget(scroll)
        
        # Store column widgets for later reference
        column_widgets = []
        
        # Add existing columns to the dialog
        for i, config in enumerate(column_configs_copy):
            row_layout = QHBoxLayout()
            
            # Column ID (hidden from user but used for tracking)
            id_label = QLabel(f"ID: {config['id']}")
            id_label.setVisible(False)  # Hide the ID
            row_layout.addWidget(id_label)
            
            # Column title
            title_label = QLabel("Title:")
            row_layout.addWidget(title_label)
            
            title_edit = QLineEdit(config["title"])
            title_edit.setMinimumWidth(150)  # Make title edit wider
            row_layout.addWidget(title_edit)
            
            # Column color picker
            color_label = QLabel("Color:")
            row_layout.addWidget(color_label)
            
            column_color = config.get("color", "#f0f0f0")
            color_button = QPushButton()
            color_button.setFixedSize(24, 24)
            color_button.setStyleSheet(f"""
                background-color: {column_color};
                border: 1px solid #cccccc;
            """)
            color_button.clicked.connect(lambda checked, btn=color_button, widget_idx=len(column_widgets): 
                                         self.selectColumnColor(btn, widget_idx, column_widgets))
            row_layout.addWidget(color_button)
            
            # Delete button (only if we have more than the minimum required columns)
            delete_btn = QPushButton("Delete")
            delete_btn.setEnabled(len(column_configs_copy) > 3)  # Ensure minimum of 3 columns
            delete_btn.clicked.connect(lambda checked, idx=i: self.deleteColumnFromCustomizeDialog(idx, column_configs_copy, column_widgets, columns_layout))
            row_layout.addWidget(delete_btn)
            
            columns_layout.addLayout(row_layout)
            
            column_widgets.append({
                "id": config["id"],
                "title_edit": title_edit,
                "color_button": color_button
            })
        
        # Add "Add Column" button
        add_column_layout = QHBoxLayout()
        add_column_btn = QPushButton("Add Column")
        add_column_btn.clicked.connect(lambda: self.addColumnFromCustomizeDialog(column_configs_copy, column_widgets, columns_layout))
        add_column_layout.addWidget(add_column_btn)
        columns_tab_layout.addLayout(add_column_layout)
        
        # Add tab to tab widget
        tab_widget.addTab(columns_tab, "Columns")
        
        # Concurrency Settings Tab
        concurrency_tab = QWidget()
        concurrency_layout = QVBoxLayout()
        concurrency_tab.setLayout(concurrency_layout)
        
        # Conflict Resolution Mode
        conflict_mode_layout = QHBoxLayout()
        conflict_mode_label = QLabel("Conflict Resolution Mode:")
        conflict_mode_layout.addWidget(conflict_mode_label)
        
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
        
        # Add spacer
        concurrency_layout.addStretch()
        
        # Refresh interval setting
        refresh_layout = QHBoxLayout()
        refresh_label = QLabel("Auto-refresh interval (seconds):")
        refresh_layout.addWidget(refresh_label)
        
        refresh_interval_spinner = QSpinBox()
        refresh_interval_spinner.setMinimum(1)
        refresh_interval_spinner.setMaximum(60)
        refresh_interval_spinner.setValue(int(self.refresh_timer.interval() / 1000))
        refresh_layout.addWidget(refresh_interval_spinner)
        
        concurrency_layout.addLayout(refresh_layout)
        
        # Add concurrency tab
        tab_widget.addTab(concurrency_tab, "Concurrency Settings")
        
        # Add spacing before buttons
        main_layout.addSpacing(20)
        
        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self.saveColumnCustomizations(dialog, column_configs_copy, column_widgets, conflict_mode_combo, refresh_interval_spinner))
        button_box.rejected.connect(dialog.reject)
        main_layout.addWidget(button_box)
        
        dialog.exec_()
    
    def selectColumnColor(self, color_button, widget_idx, column_widgets):
        """Select a color for the column."""
        color = QColorDialog.getColor()
        if color.isValid():
            column_widgets[widget_idx]["color_button"].setStyleSheet(f"""
                background-color: {color.name()};
                border: 1px solid #cccccc;
            """)
    
    def saveColumnCustomizations(self, dialog, column_configs, column_widgets, conflict_mode_combo=None, refresh_interval_spinner=None):
        """Save column customizations from the dialog.
        
        Args:
            dialog: The dialog to close after saving
            column_configs: List of column configurations
            column_widgets: List of column widget references
            conflict_mode_combo: Conflict resolution mode dropdown
            refresh_interval_spinner: Auto-refresh interval spinner
        """
        # Update column titles from the input fields
        for i, config in enumerate(column_configs):
            if i < len(column_widgets):
                config["title"] = column_widgets[i]["title_edit"].text()
                config["color"] = column_widgets[i]["color_button"].styleSheet().split(":")[1].strip()
        
        # Save the updated configuration to the database
        self.db.save_program_kanban_config(self.program_id, column_configs)
        
        # Update conflict resolution mode if provided
        if conflict_mode_combo:
            new_mode = conflict_mode_combo.currentData()
            self.setConflictResolutionMode(new_mode)
        
        # Update refresh interval if provided
        if refresh_interval_spinner:
            new_interval = refresh_interval_spinner.value() * 1000  # convert to milliseconds
            self.refresh_timer.setInterval(new_interval)
        
        # Recreate columns with the updated configuration
        self.createColumns()
        
        # Reload tasks
        self.loadTasks()
        
        # Handle tasks in deleted columns
        # Move them to the first column if they were in a deleted column
        if column_configs:
            first_column_id = column_configs[0]["id"]
            existing_column_ids = [config["id"] for config in column_configs]
            
            # Get all tasks for this program
            program_tasks = self.db.get_tasks_by_program(self.program_id)
            
            # Find tasks that are in a column that no longer exists
            for task in program_tasks:
                if task.status not in existing_column_ids:
                    # Move task to first column
                    self.db.update_task_status(task.id, first_column_id)
        
        # Close the dialog
        dialog.accept()
        
    def addColumnFromCustomizeDialog(self, column_configs, column_widgets, columns_layout):
        """Add a new column from the column customization dialog."""
        # Create a new column configuration
        new_column_id = f"column_{len(column_configs) + 1}"
        new_column_title = f"Column {len(column_configs) + 1}"
        
        # Add the new column configuration to the list
        column_configs.append({"id": new_column_id, "title": new_column_title})
        
        # Create a new row for the column configuration
        row_layout = QHBoxLayout()
        
        # Column ID (hidden from user but used for tracking)
        id_label = QLabel(f"ID: {new_column_id}")
        id_label.setVisible(False)  # Hide the ID
        row_layout.addWidget(id_label)
        
        # Column title
        title_label = QLabel("Title:")
        row_layout.addWidget(title_label)
        
        title_edit = QLineEdit(new_column_title)
        title_edit.setMinimumWidth(150)  # Make title edit wider
        row_layout.addWidget(title_edit)
        
        # Column color picker
        color_label = QLabel("Color:")
        row_layout.addWidget(color_label)
        
        color_button = QPushButton()
        color_button.setFixedSize(24, 24)
        color_button.setStyleSheet("background-color: #f0f0f0; border: 1px solid #cccccc;")
        color_button.clicked.connect(lambda checked, btn=color_button, widget_idx=len(column_widgets): 
                                     self.selectColumnColor(btn, widget_idx, column_widgets))
        row_layout.addWidget(color_button)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda checked, idx=len(column_configs) - 1: self.deleteColumnFromCustomizeDialog(idx, column_configs, column_widgets, columns_layout))
        row_layout.addWidget(delete_btn)
        
        columns_layout.addLayout(row_layout)
        
        column_widgets.append({
            "id": new_column_id,
            "title_edit": title_edit,
            "color_button": color_button
        })
    
    def deleteColumnFromCustomizeDialog(self, index, column_configs, column_widgets, columns_layout):
        """Delete a column from the kanban board.
        
        Args:
            index: Index of the column to delete
            column_configs: List of column configurations
            column_widgets: List of column widget references
            columns_layout: Layout containing the column widgets
        """
        # Check if we have enough columns to delete one
        if len(column_configs) <= 3:
            QMessageBox.warning(self, "Cannot Delete Column", 
                              "You must have at least 3 columns in your Kanban board.")
            return
            
        # Confirm with user
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete the column '{column_configs[index]['title']}'?\n\n"
                                     "Any tasks in this column will be moved to the first column.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            # Remove the column from the configuration list
            column_configs.pop(index)
            
            # Remove the corresponding widget from the list
            if index < len(column_widgets):
                column_widgets.pop(index)
            
            # Find and remove the corresponding row from the dialog layout
            # The row should be at the same index as the column in the config
            # But we need to account for the Add Column button at the end
            row_idx = index
            row_item = columns_layout.itemAt(row_idx)
            
            if row_item and row_item.layout():
                # Remove all widgets from the layout
                row_layout = row_item.layout()
                while row_layout.count():
                    item = row_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # Remove the layout itself
                columns_layout.removeItem(row_item)
            
            # Update "column_index" property of remaining delete buttons
            for i in range(columns_layout.count() - 1):  # -1 to exclude the Add Column button
                row_item = columns_layout.itemAt(i)
                if row_item and row_item.layout():
                    for j in range(row_item.layout().count()):
                        widget = row_item.layout().itemAt(j).widget()
                        if isinstance(widget, QPushButton) and widget.text() == "Delete":
                            old_index = widget.property("column_index")
                            if old_index is not None and old_index > index:
                                widget.setProperty("column_index", old_index - 1)
                                # Update the click handler
                                widget.clicked.disconnect()
                                widget.clicked.connect(lambda checked, idx=old_index-1: self.deleteColumnFromCustomizeDialog(idx, column_configs, column_widgets, columns_layout))

    def editProgram(self):
        """Edit the current program name."""
        program = self.db.get_program_by_id(self.program_id)
        if not program:
            QMessageBox.warning(self, "Error", "Program not found")
            return
        
        # Create a custom dialog instead of using QInputDialog for more size control
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Program")
        dialog.setMinimumWidth(400)  # Increased width
        dialog.setMinimumHeight(150)  # Increased height
        
        # Create a form layout for the dialog
        layout = QVBoxLayout(dialog)
        
        # Add label and input field
        form_layout = QFormLayout()
        name_input = QLineEdit(program.name)
        name_input.setMinimumHeight(30)  # Taller input field
        name_input.setFont(QFont("Segoe UI", 11))
        
        form_layout.addRow("Program name:", name_input)
        layout.addLayout(form_layout)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Apply some styling to the dialog
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fb;
            }
            QLabel {
                font-family: 'Segoe UI';
                font-size: 11pt;
                color: #2c3e50;
            }
            QLineEdit {
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                font-family: 'Segoe UI';
                font-size: 11pt;
                color: #2c3e50;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        # Show the dialog and get result
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            new_name = name_input.text().strip()
            if new_name:
                program.name = new_name
                success = self.db.update_program(program)
                
                if success:
                    # Update the tab title if this is within a tab widget
                    parent = self.parent()
                    if isinstance(parent, QTabWidget):
                        index = parent.indexOf(self)
                        if index != -1:
                            parent.setTabText(index, new_name)
                            
                    # Update the header title
                    self.findChild(QLabel).setText(new_name)
                else:
                    QMessageBox.warning(self, "Error", "Failed to update program name")


class TaskDialog(QDialog):
    """Dialog for adding or editing a task."""
    
    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_color = task.color if task and hasattr(task, 'color') and task.color else "#ffffff"
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Add Task" if not self.task else "Edit Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fb;
            }
            QLabel {
                font-family: 'Segoe UI';
                font-size: 11pt;
                color: #2c3e50;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                font-family: 'Segoe UI';
                font-size: 10pt;
                color: #2c3e50;
                selection-background-color: #3498db;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 0px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)
        self.setLayout(main_layout)
        
        # Header with title
        header_label = QLabel("Add Task" if not self.task else "Edit Task")
        header_label.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(header_label)
        
        # Form layout for task fields
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 10, 0, 10)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setVerticalSpacing(12)
        
        # Task name
        name_label = QLabel("Task Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter task name...")
        if self.task:
            self.name_input.setText(self.task.name)
        form_layout.addRow(name_label, self.name_input)
        
        # Task description
        desc_label = QLabel("Description:")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Enter task description...")
        if self.task and self.task.description:
            self.desc_input.setText(self.task.description)
        self.desc_input.setMinimumHeight(100)
        form_layout.addRow(desc_label, self.desc_input)
        
        # Priority selection with styled combobox
        priority_label = QLabel("Priority:")
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["High", "Medium", "Low"])
        self.priority_combo.setItemData(0, "#e74c3c", Qt.UserRole + 1)  # Red for High
        self.priority_combo.setItemData(1, "#f39c12", Qt.UserRole + 1)  # Orange for Medium
        self.priority_combo.setItemData(2, "#2ecc71", Qt.UserRole + 1)  # Green for Low
        
        # Update the style based on the selected priority
        self.priority_combo.setStyleSheet("""
            QComboBox {
                padding-left: 10px;
                height: 30px;
            }
        """)
        
        # Set current priority
        if self.task:
            self.priority_combo.setCurrentText(self.task.priority)
        else:
            self.priority_combo.setCurrentText("Medium")
            
        # Update combobox style when selection changes
        self.priority_combo.currentIndexChanged.connect(self.updatePriorityStyle)
        self.updatePriorityStyle(self.priority_combo.currentIndex())
        
        form_layout.addRow(priority_label, self.priority_combo)
        
        # Color selection with preview
        color_label = QLabel("Background Color:")
        color_layout = QHBoxLayout()
        
        self.color_preview = QPushButton()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.task_color};
                border: 1px solid #dcdfe6;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 1px solid #3498db;
            }}
        """)
        self.color_preview.clicked.connect(self.selectColor)
        
        self.color_button = QPushButton("Choose Color")
        self.color_button.setCursor(Qt.PointingHandCursor)
        self.color_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-family: 'Segoe UI';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.color_button.clicked.connect(self.selectColor)
        
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        
        form_layout.addRow(color_label, color_layout)
        main_layout.addLayout(form_layout)
        
        main_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                color: #2c3e50;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-family: 'Segoe UI';
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #d6dbdf;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-family: 'Segoe UI';
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
    
    def updatePriorityStyle(self, index):
        """Update the combobox style based on the selected priority."""
        color = self.priority_combo.itemData(index, Qt.UserRole + 1)
        self.priority_combo.setStyleSheet(f"""
            QComboBox {{
                padding-left: 10px;
                height: 30px;
                border-left: 6px solid {color};
            }}
        """)
    
    def selectColor(self):
        """Open a color dialog to select a task color."""
        color = QColorDialog.getColor(initial=QColor(self.task_color))
        if color.isValid():
            self.task_color = color.name()
            self.color_preview.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.task_color};
                    border: 1px solid #dcdfe6;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 1px solid #3498db;
                }}
            """)
    
    def getTaskData(self):
        """Get the task data from the dialog."""
        return {
            "name": self.name_input.text(),
            "description": self.desc_input.toPlainText(),
            "priority": self.priority_combo.currentText(),
            "color": self.task_color
        }


class Task:
    """Represents a task in the kanban board."""
    
    def __init__(self, id=None, name="", description="", status="todo", patient_id=None, 
                 program_id=None, order_index=0, color="#ffffff", priority="Medium",
                 version=1, modified_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.status = status
        self.patient_id = patient_id
        self.program_id = program_id
        self.order_index = order_index
        self.color = color  # Background color for the task
        self.priority = priority  # Priority level: "High", "Medium", "Low"
        self.version = version  # For concurrent edit handling
        self.modified_at = modified_at  # Last modification timestamp
