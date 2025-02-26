from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
                             QMessageBox, QLabel, QListWidget, QWidget)
from PyQt5.QtCore import Qt

from models import SharedAccess, User


class ShareAccessDialog(QDialog):
    """Dialog for managing shared patient access."""
    
    def __init__(self, db, patient, current_user, parent=None):
        super().__init__(parent)
        self.db = db
        self.patient = patient
        self.current_user = current_user
        
        # Check if current user is owner or has full access
        if patient.user_id != current_user.id:
            shared_access = self.db.get_shared_access(patient.id, current_user.id)
            if not shared_access or shared_access.access_level != SharedAccess.ACCESS_FULL:
                QMessageBox.warning(self, "Permission Denied", 
                                  "You must be the owner or have full access to manage sharing.")
                self.reject()
                return
                
        self.initUI()
        self.loadSharedUsers()
        
    def initUI(self):
        self.setWindowTitle(f"Manage Shared Access - {self.patient.first_name} {self.patient.last_name}")
        self.setMinimumSize(600, 400)
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header_label = QLabel(f"Manage Access for {self.patient.first_name} {self.patient.last_name}")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)
        
        owner_info = QLabel(f"Owner: {self.db.get_user_name_by_id(self.patient.user_id)}")
        layout.addWidget(owner_info)
        
        # Current shared users
        shared_label = QLabel("Currently Shared With:")
        shared_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(shared_label)
        
        self.shared_table = QTableWidget()
        self.shared_table.setColumnCount(4)
        self.shared_table.setHorizontalHeaderLabels(["User", "Role", "Access Level", "Actions"])
        self.shared_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.shared_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.shared_table.verticalHeader().setVisible(False)
        layout.addWidget(self.shared_table)
        
        # Add new share section
        new_share_label = QLabel("Share with New User:")
        new_share_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(new_share_label)
        
        # User selection
        user_layout = QHBoxLayout()
        
        user_label = QLabel("Select User:")
        user_layout.addWidget(user_label)
        
        self.user_combo = QComboBox()
        user_layout.addWidget(self.user_combo)
        
        access_label = QLabel("Access Level:")
        user_layout.addWidget(access_label)
        
        self.access_combo = QComboBox()
        self.access_combo.addItem("Read Only", SharedAccess.ACCESS_READ)
        self.access_combo.addItem("Read & Write", SharedAccess.ACCESS_WRITE)
        self.access_combo.addItem("Full Access", SharedAccess.ACCESS_FULL)
        self.access_combo.setCurrentIndex(0)  # Default to read-only
        user_layout.addWidget(self.access_combo)
        
        share_button = QPushButton("Share")
        share_button.clicked.connect(self.shareAccess)
        user_layout.addWidget(share_button)
        
        layout.addLayout(user_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Load available users for sharing
        self.loadAvailableUsers()
        
    def loadAvailableUsers(self):
        """Load users that the patient can be shared with."""
        self.user_combo.clear()
        
        # Get all users except the current one and those already having access
        all_users = self.db.get_all_users()
        shared_user_ids = [access.user_id for access in self.db.get_shared_access_for_patient(self.patient.id)]
        
        # We don't want to include the patient owner in the share list
        shared_user_ids.append(self.patient.user_id)
        
        for user in all_users:
            if user.id not in shared_user_ids:
                display_name = f"{user.name} ({user.username})" if user.name else user.username
                self.user_combo.addItem(display_name, user.id)
    
    def loadSharedUsers(self):
        """Load users that already have shared access to this patient."""
        self.shared_table.setRowCount(0)
        
        shared_access_list = self.db.get_shared_access_for_patient(self.patient.id)
        self.shared_table.setRowCount(len(shared_access_list))
        
        for i, access in enumerate(shared_access_list):
            user = self.db.get_user_by_id(access.user_id)
            if not user:
                continue
                
            # User name
            user_name = f"{user.name} ({user.username})" if user.name else user.username
            name_item = QTableWidgetItem(user_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.shared_table.setItem(i, 0, name_item)
            
            # User role
            role_item = QTableWidgetItem(user.role)
            role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)
            self.shared_table.setItem(i, 1, role_item)
            
            # Access level
            access_item = QTableWidgetItem(access.access_level)
            access_item.setFlags(access_item.flags() & ~Qt.ItemIsEditable)
            self.shared_table.setItem(i, 2, access_item)
            
            # Actions - Edit/Revoke buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(2)
            
            edit_button = QPushButton("Edit")
            edit_button.setMaximumWidth(60)
            edit_button.clicked.connect(lambda checked, a=access: self.editAccess(a))
            actions_layout.addWidget(edit_button)
            
            revoke_button = QPushButton("Revoke")
            revoke_button.setMaximumWidth(60)
            revoke_button.clicked.connect(lambda checked, a=access: self.revokeAccess(a))
            actions_layout.addWidget(revoke_button)
            
            actions_widget.setLayout(actions_layout)
            self.shared_table.setCellWidget(i, 3, actions_widget)
    
    def shareAccess(self):
        """Share access to the patient with a selected user."""
        if self.user_combo.count() == 0:
            QMessageBox.information(self, "No Users Available", 
                                  "There are no users available to share with.")
            return
            
        user_id = self.user_combo.currentData()
        access_level = self.access_combo.currentData()
        
        # Create shared access
        access = SharedAccess(
            patient_id=self.patient.id,
            user_id=user_id,
            granted_by=self.current_user.id,
            access_level=access_level
        )
        
        success = self.db.add_shared_access(access)
        if success:
            QMessageBox.information(self, "Access Shared", 
                                  f"Access has been granted to {self.user_combo.currentText()}")
            self.loadSharedUsers()
            self.loadAvailableUsers()  # Refresh available users
        else:
            QMessageBox.warning(self, "Error", 
                              "An error occurred while sharing access.")
    
    def editAccess(self, access):
        """Edit access level for a user."""
        user = self.db.get_user_by_id(access.user_id)
        if not user:
            return
            
        user_display = f"{user.name} ({user.username})" if user.name else user.username
        
        # Create a dialog for editing access
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle(f"Edit Access for {user_display}")
        edit_dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        edit_dialog.setLayout(layout)
        
        # Access level dropdown
        layout.addWidget(QLabel("Select access level:"))
        
        access_combo = QComboBox()
        access_combo.addItem("Read Only", SharedAccess.ACCESS_READ)
        access_combo.addItem("Read & Write", SharedAccess.ACCESS_WRITE)
        access_combo.addItem("Full Access", SharedAccess.ACCESS_FULL)
        
        # Set current selection based on existing access
        current_index = 0
        if access.access_level == SharedAccess.ACCESS_WRITE:
            current_index = 1
        elif access.access_level == SharedAccess.ACCESS_FULL:
            current_index = 2
        access_combo.setCurrentIndex(current_index)
        
        layout.addWidget(access_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(edit_dialog.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(edit_dialog.accept)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        if edit_dialog.exec_() == QDialog.Accepted:
            # Update access level
            access.access_level = access_combo.currentData()
            success = self.db.update_shared_access(access)
            
            if success:
                self.loadSharedUsers()
            else:
                QMessageBox.warning(self, "Error", 
                                  "Failed to update access level.")
    
    def revokeAccess(self, access):
        """Revoke shared access from a user."""
        user = self.db.get_user_by_id(access.user_id)
        if not user:
            return
            
        user_display = f"{user.name} ({user.username})" if user.name else user.username
        
        confirm = QMessageBox.question(
            self, "Confirm Revoke Access",
            f"Are you sure you want to revoke access for {user_display}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
            
        # Delete shared access
        success = self.db.delete_shared_access(access.id)
        
        if success:
            self.loadSharedUsers()
            self.loadAvailableUsers()  # Refresh available users
        else:
            QMessageBox.warning(self, "Error", 
                              "Failed to revoke access.")
