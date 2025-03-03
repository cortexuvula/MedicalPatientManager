from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
                             QMessageBox, QLabel, QInputDialog, QWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor

from models import User
from security import hash_password, is_strong_password, PermissionManager


class AdminPanel(QDialog):
    """Dialog for system administration tasks."""
    
    def __init__(self, db, current_user, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_user = current_user
        
        # Verify admin access
        if not self.current_user or not self.current_user.is_admin():
            QMessageBox.critical(self, "Access Denied", "You must be an administrator to access this panel.")
            self.reject()
            return
            
        self.initUI()
        self.loadUsers()
        
    def initUI(self):
        self.setWindowTitle("Admin Panel")
        self.setMinimumSize(800, 500)
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tabs header
        header_layout = QHBoxLayout()
        header_label = QLabel("User Management")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_label)
        layout.addLayout(header_layout)
        
        # User table with reorderable columns
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Name", "Email", "Role", "Actions"])
        
        # Enable column reordering - Using same approach as in working test case
        header = self.user_table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setFirstSectionMovable(True)
        
        # Style the headers to make dragging more obvious and provide visual feedback
        header.setStyleSheet("QHeaderView::section { padding: 4px; background-color: #e0e0ff; border: 1px solid #b0b0b0; }")
        
        # Track column movement
        header.sectionMoved.connect(self.onColumnMoved)
        
        # Set resize modes - this must be done AFTER enabling movement
        for i in range(header.count()):
            if i == 0 or i == 5:  # ID and Actions columns
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        self.user_table.verticalHeader().setVisible(False)
        layout.addWidget(self.user_table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        add_user_btn = QPushButton("Add User")
        add_user_btn.clicked.connect(self.addUser)
        button_layout.addWidget(add_user_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.loadUsers)
        button_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def loadUsers(self):
        """Load all users into the table."""
        self.user_table.setRowCount(0)
        
        users = self.db.get_all_users()
        self.user_table.setRowCount(len(users))
        
        for i, user in enumerate(users):
            # ID
            id_item = QTableWidgetItem(str(user.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.user_table.setItem(i, 0, id_item)
            
            # Username
            username_item = QTableWidgetItem(user.username)
            username_item.setFlags(username_item.flags() & ~Qt.ItemIsEditable)
            self.user_table.setItem(i, 1, username_item)
            
            # Name
            name_item = QTableWidgetItem(user.name or "")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.user_table.setItem(i, 2, name_item)
            
            # Email
            email_item = QTableWidgetItem(user.email or "")
            email_item.setFlags(email_item.flags() & ~Qt.ItemIsEditable)
            self.user_table.setItem(i, 3, email_item)
            
            # Role (as combobox)
            role_cell = QTableWidgetItem(user.role)
            role_cell.setFlags(role_cell.flags() & ~Qt.ItemIsEditable)
            self.user_table.setItem(i, 4, role_cell)
            
            # Actions
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)
            
            # Edit button
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(QSize(60, 25))
            edit_btn.clicked.connect(lambda checked, user_id=user.id: self.editUser(user_id))
            actions_layout.addWidget(edit_btn)
            
            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedSize(QSize(60, 25))
            # Prevent deleting self
            if user.id == self.current_user.id:
                delete_btn.setEnabled(False)
                delete_btn.setToolTip("You cannot delete your own account")
            delete_btn.clicked.connect(lambda checked, user_id=user.id: self.deleteUser(user_id))
            actions_layout.addWidget(delete_btn)
            
            # Add the layout to the cell
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            self.user_table.setCellWidget(i, 5, actions_widget)
            
            # Highlight admin users
            if user.role == User.ROLE_ADMIN:
                for col in range(self.user_table.columnCount()):
                    if col != 5:  # Skip actions column
                        item = self.user_table.item(i, col)
                        item.setBackground(QColor(230, 230, 250))  # Light purple
    
    def addUser(self):
        """Add a new user to the system."""
        # Get username
        username, ok = QInputDialog.getText(self, "Add User", "Username:")
        if not ok or not username:
            return
            
        # Check if username exists
        if self.db.get_user_by_username(username):
            QMessageBox.warning(self, "Username Exists", "This username is already taken.")
            return
            
        # Get password
        password, ok = QInputDialog.getText(self, "Add User", "Password:")
        if not ok:
            return
            
        if not is_strong_password(password):
            QMessageBox.warning(self, "Weak Password", "Password must be at least 8 characters and include uppercase, lowercase, numbers, and special characters.")
            return
            
        # Get name
        name, ok = QInputDialog.getText(self, "Add User", "Full Name (optional):")
        if not ok:
            return
            
        # Get email
        email, ok = QInputDialog.getText(self, "Add User", "Email (optional):")
        if not ok:
            return
            
        # Get role
        roles = [User.ROLE_ASSISTANT, User.ROLE_PROVIDER, User.ROLE_ADMIN]
        role, ok = QInputDialog.getItem(self, "Add User", "Role:", roles, 1, False)
        if not ok:
            return
            
        # Create user
        user = User(
            username=username,
            password=hash_password(password),
            name=name,
            email=email,
            role=role
        )
        
        self.db.add_user(user)
        QMessageBox.information(self, "User Added", f"User '{username}' has been added successfully.")
        self.loadUsers()
    
    def editUser(self, user_id):
        """Edit an existing user."""
        user = self.db.get_user_by_id(user_id)
        if not user:
            QMessageBox.warning(self, "Error", "User not found.")
            return
            
        # Get updated name
        name, ok = QInputDialog.getText(self, "Edit User", "Full Name:", text=user.name or "")
        if not ok:
            return
            
        # Get updated email
        email, ok = QInputDialog.getText(self, "Edit User", "Email:", text=user.email or "")
        if not ok:
            return
            
        # Get updated role
        roles = [User.ROLE_ASSISTANT, User.ROLE_PROVIDER, User.ROLE_ADMIN]
        current_index = roles.index(user.role) if user.role in roles else 1
        role, ok = QInputDialog.getItem(self, "Edit User", "Role:", roles, current_index, False)
        if not ok:
            return
            
        # Ask about password reset
        reset_password = QMessageBox.question(self, "Reset Password", 
                                           "Do you want to reset this user's password?",
                                           QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes
                                           
        if reset_password:
            password, ok = QInputDialog.getText(self, "Reset Password", "New Password:")
            if ok and password:
                if not is_strong_password(password):
                    QMessageBox.warning(self, "Weak Password", "Password must be at least 8 characters and include uppercase, lowercase, numbers, and special characters.")
                    return
                user.password = hash_password(password)
        
        # Update user data
        user.name = name
        user.email = email
        user.role = role
        
        self.db.update_user(user)
        QMessageBox.information(self, "User Updated", f"User '{user.username}' has been updated successfully.")
        self.loadUsers()
    
    def deleteUser(self, user_id):
        """Delete a user from the system."""
        if user_id == self.current_user.id:
            QMessageBox.warning(self, "Cannot Delete", "You cannot delete your own account.")
            return
            
        user = self.db.get_user_by_id(user_id)
        if not user:
            QMessageBox.warning(self, "Error", "User not found.")
            return
            
        # Confirm deletion
        confirm = QMessageBox.question(self, "Confirm Deletion", 
                                     f"Are you sure you want to delete user '{user.username}'?\n\nThis action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
                                     
        if confirm == QMessageBox.Yes:
            self.db.delete_user(user_id)
            QMessageBox.information(self, "User Deleted", f"User '{user.username}' has been deleted.")
            self.loadUsers()
    
    def onColumnMoved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        """Handle column movement events."""
        print(f"Column moved: Logical index {logicalIndex} moved from {oldVisualIndex} to {newVisualIndex}")
