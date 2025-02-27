import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QPushButton, QLabel, 
                             QInputDialog, QMessageBox, QTabWidget, QSplitter,
                             QFrame, QLineEdit, QAction, QMenu, QDialog, QTreeWidget,
                             QTreeWidgetItem)
from PyQt5.QtCore import Qt, QSize, QSettings
from PyQt5.QtGui import QFont, QIcon

from database import Database
from models import Patient, Program, Task, User, SharedAccess, AuditLog
from kanban_board import KanbanBoard
from login_dialog import LoginDialog, UserProfileDialog
from security import hash_password, verify_password, is_strong_password, PermissionManager, sanitize_data_for_logs
from admin_panel import AdminPanel
from share_access_dialog import ShareAccessDialog
from audit_log_viewer import AuditLogViewer
from safe_audit_logger import SafeAuditLogger
from session_manager import SessionManager


class MedicalPatientManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.settings = QSettings("CascadeTeam", "MedicalPatientManager")
        self.current_user = None
        self.is_logged_in = False
        self.current_patient = None
        self.current_program = None
        
        # Initialize the audit logger
        self.audit_logger = SafeAuditLogger(self.db)
        
        # Initialize the session manager
        self.session_manager = SessionManager()

        self.initUI()
        self.checkLogin()
        
    def initUI(self):
        self.setWindowTitle("Medical Patient Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Setup menu bar
        self.setupMenuBar()
        
        # Main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Left panel for patients
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        
        # Patients section
        patients_label = QLabel("Patients")
        patients_label.setFont(QFont("Arial", 14, QFont.Bold))
        left_layout.addWidget(patients_label)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search patients...")
        self.search_input.textChanged.connect(self.filterPatients)
        left_layout.addWidget(self.search_input)
        
        # Patient list
        self.patient_list = QTreeWidget()
        self.patient_list.setFont(QFont("Arial", 12))
        self.patient_list.setHeaderHidden(True)
        self.patient_list.itemSelectionChanged.connect(self.onPatientSelected)
        left_layout.addWidget(self.patient_list)
        
        # Patient buttons
        patient_buttons = QHBoxLayout()
        self.add_patient_btn = QPushButton("Add Patient")
        self.add_patient_btn.clicked.connect(self.addPatient)
        self.edit_patient_btn = QPushButton("Edit")
        self.edit_patient_btn.clicked.connect(self.editPatient)
        self.delete_patient_btn = QPushButton("Delete")
        self.delete_patient_btn.clicked.connect(self.deletePatient)
        self.share_patient_btn = QPushButton("Share")
        self.share_patient_btn.clicked.connect(self.sharePatient)
        
        patient_buttons.addWidget(self.add_patient_btn)
        patient_buttons.addWidget(self.edit_patient_btn)
        patient_buttons.addWidget(self.delete_patient_btn)
        patient_buttons.addWidget(self.share_patient_btn)
        left_layout.addLayout(patient_buttons)
        
        # Right panel (contains programs and kanban)
        right_panel = QWidget()
        self.right_layout = QVBoxLayout()
        right_panel.setLayout(self.right_layout)
        
        # Patient info section
        self.patient_info = QLabel("Select a patient")
        self.patient_info.setFont(QFont("Arial", 16, QFont.Bold))
        self.right_layout.addWidget(self.patient_info)
        
        # Programs section
        programs_section = QWidget()
        programs_layout = QVBoxLayout()
        programs_section.setLayout(programs_layout)
        
        programs_header = QHBoxLayout()
        programs_label = QLabel("Programs")
        programs_label.setFont(QFont("Arial", 14, QFont.Bold))
        programs_header.addWidget(programs_label)
        
        self.add_program_btn = QPushButton("Add Program")
        self.add_program_btn.clicked.connect(self.addProgram)
        programs_header.addWidget(self.add_program_btn)
        programs_layout.addLayout(programs_header)
        
        self.program_tabs = QTabWidget()
        self.program_tabs.setTabPosition(QTabWidget.North)
        self.program_tabs.setTabsClosable(True)
        self.program_tabs.tabCloseRequested.connect(self.closeTab)
        programs_layout.addWidget(self.program_tabs)
        
        self.right_layout.addWidget(programs_section)
        self.selected_patient_id = None
        
        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])  # Initial sizes
        main_layout.addWidget(splitter)
        
        # Display welcome message initially
        self.welcome_label = QLabel("Welcome to Medical Patient Manager\n\nSelect a patient to view their programs or add a new patient.")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.welcome_label.setFont(QFont("Arial", 14))
        self.right_layout.addWidget(self.welcome_label)
        
        # Initialize empty kanban board container
        self.kanban_container = QWidget()
        self.kanban_layout = QVBoxLayout()
        self.kanban_container.setLayout(self.kanban_layout)
        self.right_layout.addWidget(self.kanban_container)
        self.kanban_container.hide()  # Hide initially
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # User info in status bar
        self.user_info_label = QLabel()
        self.status_bar.addPermanentWidget(self.user_info_label)
        
    def setupMenuBar(self):
        """Setup the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # User management actions
        login_action = QAction("Login", self)
        login_action.triggered.connect(self.showLoginDialog)
        file_menu.addAction(login_action)
        
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # User menu
        user_menu = menubar.addMenu("User")
        
        profile_action = QAction("My Profile", self)
        profile_action.triggered.connect(self.showUserProfile)
        user_menu.addAction(profile_action)
        
        # Admin menu - only shown to admin users
        self.admin_menu = menubar.addMenu("Administration")
        
        # Admin panel action
        admin_panel_action = QAction("Admin Panel", self)
        admin_panel_action.triggered.connect(self.showAdminPanel)
        self.admin_menu.addAction(admin_panel_action)
        
        # User management action
        user_management_action = QAction("User Management", self)
        user_management_action.triggered.connect(self.showAdminPanel)  # Points to same panel
        self.admin_menu.addAction(user_management_action)
        
        # Audit log action
        audit_log_action = QAction("View Audit Log", self)
        audit_log_action.triggered.connect(self.showAuditLogViewer)
        self.admin_menu.addAction(audit_log_action)
        
        # Hide admin menu by default (will show based on permission)
        self.admin_menu.menuAction().setVisible(False)
        
    def checkLogin(self):
        """Check if user is already logged in or prompt for login."""
        # Try to get saved username and password from settings
        username = self.settings.value("username", "")
        password = self.settings.value("password", "")
        
        if username and password:
            # Attempt auto-login
            user = self.db.get_user_by_username(username)
            if user and user.password == password:
                self.loginUser(user)
                return
        
        # No valid saved credentials, show login dialog
        self.showLoginDialog()
        
    def showLoginDialog(self):
        """Show the login dialog."""
        dialog = LoginDialog(self.db, self)
        dialog.userAuthenticated.connect(self.loginUser)
        
        # If dialog is rejected (closed without login), and no user is logged in, exit the app
        if dialog.exec_() == QDialog.Rejected and not self.current_user:
            sys.exit()
    
    def loginUser(self, user):
        """Set the current user and update UI."""
        self.current_user = user
        self.is_logged_in = True
        
        # Create a session
        session_id = self.session_manager.create_session(user.id)
        
        # Log successful login - with error handling
        try:
            self.audit_logger.log_login(
                user_id=user.id,
                success=True,
                details=f"User logged in from application"
            )
        except Exception as e:
            print(f"Warning: Could not log login event: {e}")
        
        # Update UI
        self.updateUserDisplay()
        
        # Save credentials if remember me was checked
        if hasattr(self, 'remember_me') and self.remember_me and self.remember_me.isChecked():
            self.settings.setValue("username", user.username)
            self.settings.setValue("password", user.password)
        
        # Load patients for this user
        self.loadPatients()
        
        # Update UI based on user role permissions
        self.updateUIPermissions()
        
        self.status_bar.showMessage(f"Welcome, {user.name or user.username}!", 3000)
    
    def logout(self):
        """Log out the current user."""
        if not self.current_user:
            return
            
        # End all user sessions
        self.session_manager.end_all_user_sessions(self.current_user.id)
        
        # Log logout with error handling
        try:
            self.audit_logger.log_logout(
                user_id=self.current_user.id
            )
        except Exception as e:
            print(f"Warning: Could not log logout event: {e}")
        
        # Clear settings
        self.settings.remove("username")
        self.settings.remove("password")
        
        # Clear current user
        self.current_user = None
        self.is_logged_in = False
        self.updateUserDisplay()
        
        # Hide admin menu
        self.admin_menu.menuAction().setVisible(False)
        
        # Clear UI
        self.patient_list.clear()
        self.clearPatientView()
        
        # Show login dialog
        self.showLoginDialog()
    
    def updateUserDisplay(self):
        """Update the UI to show current user info."""
        if self.current_user:
            display_name = self.current_user.name or self.current_user.username
            role_text = f" ({self.current_user.role})" if self.current_user.role else ""
            self.user_info_label.setText(f"Logged in as: {display_name}{role_text}")
        else:
            self.user_info_label.setText("Not logged in")
    
    def updateUIPermissions(self):
        """Update UI elements based on user role permissions."""
        if not self.current_user:
            # No user logged in - disable everything
            self.add_patient_btn.setEnabled(False)
            self.edit_patient_btn.setEnabled(False)
            self.delete_patient_btn.setEnabled(False)
            self.add_program_btn.setEnabled(False)
            self.admin_menu.menuAction().setVisible(False)
            return
            
        # Check permissions based on user role
        can_create_patient = PermissionManager.has_permission(self.current_user, 'patient.create')
        can_edit_patient = PermissionManager.has_permission(self.current_user, 'patient.update')
        can_delete_patient = PermissionManager.has_permission(self.current_user, 'patient.delete')
        can_create_program = PermissionManager.has_permission(self.current_user, 'program.create')
        can_access_admin = PermissionManager.can_access_admin_panel(self.current_user)
        
        # Update UI based on permissions
        self.add_patient_btn.setEnabled(can_create_patient)
        self.edit_patient_btn.setEnabled(can_edit_patient)
        self.delete_patient_btn.setEnabled(can_delete_patient)
        self.add_program_btn.setEnabled(can_create_program)
        
        # Show/hide admin menu
        self.admin_menu.menuAction().setVisible(can_access_admin)
    
    def loadPatients(self):
        """Load the patient list."""
        self.patient_list.clear()
        
        if not self.current_user:
            return
            
        # Create category for user's own patients
        own_patients_item = QTreeWidgetItem(["My Patients"])
        own_patients_item.setExpanded(True)
        self.patient_list.addTopLevelItem(own_patients_item)
        
        # Load patients created by this user
        patients = self.db.get_patients_by_user(self.current_user.id)
        for patient in patients:
            patient_item = QTreeWidgetItem([f"{patient.first_name} {patient.last_name}"])
            patient_item.setData(0, Qt.UserRole, patient.id)
            own_patients_item.addChild(patient_item)
        
        # Create category for shared patients
        shared_patients = self.db.get_shared_patients_for_user(self.current_user.id)
        
        if shared_patients:
            shared_patients_item = QTreeWidgetItem(["Shared With Me"])
            shared_patients_item.setExpanded(True)
            self.patient_list.addTopLevelItem(shared_patients_item)
            
            for patient in shared_patients:
                patient_item = QTreeWidgetItem([f"{patient.first_name} {patient.last_name}"])
                patient_item.setData(0, Qt.UserRole, patient.id)
                # Add owner's name as tooltip
                owner_name = self.db.get_user_name_by_id(patient.user_id)
                patient_item.setToolTip(0, f"Owner: {owner_name}")
                shared_patients_item.addChild(patient_item)
    
    def filterPatients(self, text):
        """Filter the patient list based on search text."""
        # If empty search text, show all
        if not text:
            for i in range(self.patient_list.topLevelItemCount()):
                top_item = self.patient_list.topLevelItem(i)
                top_item.setHidden(False)
                for j in range(top_item.childCount()):
                    top_item.child(j).setHidden(False)
            return
            
        # Filter based on text
        search_text = text.lower()
        
        for i in range(self.patient_list.topLevelItemCount()):
            top_item = self.patient_list.topLevelItem(i)
            
            # Check each child (patient) item
            visible_children = 0
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                patient_name = child.text(0).lower()
                
                if search_text in patient_name:
                    child.setHidden(False)
                    visible_children += 1
                else:
                    child.setHidden(True)
            
            # Hide category if all children are hidden
            top_item.setHidden(visible_children == 0)
    
    def addPatient(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to add patients.")
            return
            
        first_name, ok1 = QInputDialog.getText(self, "Add Patient", "First Name:")
        if ok1 and first_name:
            last_name, ok2 = QInputDialog.getText(self, "Add Patient", "Last Name:")
            if ok2 and last_name:
                dob, ok3 = QInputDialog.getText(self, "Add Patient", "Date of Birth (YYYY-MM-DD):")
                if ok3:
                    patient = Patient(
                        first_name=first_name, 
                        last_name=last_name, 
                        date_of_birth=dob,
                        user_id=self.current_user.id
                    )
                    self.db.add_patient(patient)
                    self.loadPatients()
                    
                    # Log the action
                    self.audit_logger.log_data_modification(
                        user_id=self.current_user.id,
                        action=AuditLog.ACTION_CREATE,
                        entity_type=AuditLog.ENTITY_PATIENT,
                        entity_id=patient.id,
                        details=f"Created new patient: {first_name} {last_name}"
                    )
                    
                    self.status_bar.showMessage(f"Patient {first_name} {last_name} added", 3000)
    
    def editPatient(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to edit patients.")
            return
            
        if not self.patient_list.currentItem():
            QMessageBox.warning(self, "Warning", "No patient selected")
            return
        
        patient_id = self.patient_list.currentItem().data(0, Qt.UserRole)
        patient = self.db.get_patient_by_id(patient_id)
        
        # Check if user has permission to edit this patient
        if not PermissionManager.can_edit_patient(self.current_user, patient):
            QMessageBox.warning(self, "Permission Denied", 
                              "You don't have permission to edit this patient.")
            return
        
        first_name, ok1 = QInputDialog.getText(self, "Edit Patient", "First Name:", text=patient.first_name)
        if ok1 and first_name:
            last_name, ok2 = QInputDialog.getText(self, "Edit Patient", "Last Name:", text=patient.last_name)
            if ok2 and last_name:
                dob, ok3 = QInputDialog.getText(self, "Edit Patient", "Date of Birth (YYYY-MM-DD):", text=patient.date_of_birth)
                if ok3:
                    patient.first_name = first_name
                    patient.last_name = last_name
                    patient.date_of_birth = dob
                    self.db.update_patient(patient)
                    self.loadPatients()
                    
                    # Update patient info if this patient is currently selected
                    if self.selected_patient_id == patient_id:
                        self.patient_info.setText(f"{patient.first_name} {patient.last_name} - DOB: {patient.date_of_birth}")
                    
                    # Log the action
                    self.audit_logger.log_data_modification(
                        user_id=self.current_user.id,
                        action=AuditLog.ACTION_UPDATE,
                        entity_type=AuditLog.ENTITY_PATIENT,
                        entity_id=patient.id,
                        details=f"Updated patient: {first_name} {last_name}"
                    )
                    
                    self.status_bar.showMessage(f"Patient updated", 3000)
    
    def deletePatient(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to delete patients.")
            return
            
        if not self.patient_list.currentItem():
            QMessageBox.warning(self, "Warning", "No patient selected")
            return
            
        patient_id = self.patient_list.currentItem().data(0, Qt.UserRole)
        patient = self.db.get_patient_by_id(patient_id)
        
        # Check if user has permission to delete this patient
        if not PermissionManager.can_delete_patient(self.current_user, patient):
            QMessageBox.warning(self, "Permission Denied", 
                              "You don't have permission to delete this patient.")
            return
            
        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                  f"Are you sure you want to delete {patient.first_name} {patient.last_name}?",
                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                                  
        if reply == QMessageBox.Yes:
            # Delete patient
            self.db.delete_patient(patient_id)
            self.loadPatients()
            self.clearPatientView()
            
            # Log the action
            self.audit_logger.log_data_modification(
                user_id=self.current_user.id,
                action=AuditLog.ACTION_DELETE,
                entity_type=AuditLog.ENTITY_PATIENT,
                entity_id=patient_id,
                details=f"Deleted patient: {patient.first_name} {patient.last_name}"
            )
    
    def clearPatientView(self):
        self.selected_patient_id = None
        self.patient_info.setText("Select a patient")
        
        # Clear tabs
        while self.program_tabs.count() > 0:
            self.program_tabs.removeTab(0)
        
        self.kanban_container.hide()
        self.welcome_label.show()
    
    def onPatientSelected(self):
        """Handle patient selection."""
        selected_items = self.patient_list.selectedItems()
        if not selected_items or not self.current_user:
            self.selected_patient_id = None
            self.patient_info.setText("Select a patient")
            self.edit_patient_btn.setEnabled(False)
            self.delete_patient_btn.setEnabled(False)
            self.share_patient_btn.setEnabled(False)
            self.add_program_btn.setEnabled(False)
            self.welcome_label.show()
            self.kanban_container.hide()
            return
            
        current_item = selected_items[0]
        patient_id = current_item.data(0, Qt.UserRole)
        
        if patient_id:
            patient = self.db.get_patient_by_id(patient_id)
            if patient:
                self.selected_patient_id = patient_id
                self.patient_info.setText(f"Patient: {patient.first_name} {patient.last_name}")
                
                # Check permissions
                is_owner = (patient.user_id == self.current_user.id)
                
                # Check if user has shared access
                access_level = None
                if not is_owner:
                    shared_access = self.db.get_shared_access(patient_id, self.current_user.id)
                    if shared_access:
                        access_level = shared_access.access_level
                
                # Set button states based on permissions
                can_edit = is_owner or (access_level in [SharedAccess.ACCESS_WRITE, SharedAccess.ACCESS_FULL])
                can_delete = is_owner  # Only owner can delete
                can_share = is_owner or (access_level == SharedAccess.ACCESS_FULL)
                
                self.edit_patient_btn.setEnabled(can_edit)
                self.delete_patient_btn.setEnabled(can_delete)
                self.share_patient_btn.setEnabled(can_share)
                self.add_program_btn.setEnabled(can_edit)
                
                # Load programs for the selected patient
                self.loadPatientPrograms(patient_id)
                
                # Show kanban board
                self.welcome_label.hide()
                self.kanban_container.show()
                
                # If not owner, show a tooltip indicating the access level
                if not is_owner and access_level:
                    access_text = {
                        SharedAccess.ACCESS_READ: "Read Only",
                        SharedAccess.ACCESS_WRITE: "Read & Write",
                        SharedAccess.ACCESS_FULL: "Full Access"
                    }.get(access_level, "Limited Access")
                    
                    owner_name = self.db.get_user_name_by_id(patient.user_id)
                    self.patient_info.setToolTip(f"Owner: {owner_name}\nYour Access: {access_text}")
                    
                # Log the access
                self.audit_logger.log_data_access(
                    user_id=self.current_user.id,
                    entity_type=AuditLog.ENTITY_PATIENT,
                    entity_id=patient_id,
                    details=f"Viewed patient: {patient.first_name} {patient.last_name}"
                )
    
    def loadPatientPrograms(self, patient_id):
        # Clear existing tabs
        while self.program_tabs.count() > 0:
            self.program_tabs.removeTab(0)
        
        programs = self.db.get_programs_by_patient(patient_id)
        
        # Clear existing kanban layout
        while self.kanban_layout.count():
            item = self.kanban_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        if programs:
            # Add tabs for each program
            for program in programs:
                # Create Kanban board for this program
                kanban = KanbanBoard(self.db, program.id)
                self.program_tabs.addTab(kanban, program.name)
        else:
            # No programs yet
            empty_widget = QWidget()
            empty_layout = QVBoxLayout()
            empty_widget.setLayout(empty_layout)
            
            empty_label = QLabel("No programs added yet. Click 'Add Program' to create one.")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(empty_label)
            
            self.program_tabs.addTab(empty_widget, "No Programs")
    
    def addProgram(self):
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Warning", "No patient selected")
            return
        
        # List of common programs
        program_options = ["Diabetes Management", "Chronic Kidney Disease Management", 
                          "Pain Management", "Hypertension Management", 
                          "Heart Failure Management", "Respiratory Disease Management",
                          "Custom Program"]
        
        program_name, ok = QInputDialog.getItem(self, "Add Program", 
                                              "Select a program type:", 
                                              program_options, 0, False)
        
        if ok and program_name:
            # If custom program selected, ask for name
            if program_name == "Custom Program":
                custom_name, ok = QInputDialog.getText(self, "Custom Program", "Enter program name:")
                if ok and custom_name:
                    program_name = custom_name
                else:
                    return
            
            # Create program
            program = Program(name=program_name, patient_id=self.selected_patient_id)
            program_id = self.db.add_program(program)
            
            # Create default tasks based on program type
            if "Diabetes" in program_name:
                default_tasks = [
                    ("Blood Glucose Monitoring", "To Do"),
                    ("Medication Adherence", "To Do"),
                    ("Dietary Management", "To Do"),
                    ("Exercise Plan", "To Do"),
                    ("Regular Check-ups", "To Do")
                ]
            elif "Kidney" in program_name:
                default_tasks = [
                    ("Blood Pressure Monitoring", "To Do"),
                    ("Fluid Intake Tracking", "To Do"),
                    ("Renal Diet Adherence", "To Do"),
                    ("Medication Management", "To Do"),
                    ("Nephrology Appointments", "To Do")
                ]
            elif "Pain" in program_name:
                default_tasks = [
                    ("Pain Assessment", "To Do"),
                    ("Medication Schedule", "To Do"),
                    ("Physical Therapy", "To Do"),
                    ("Alternative Pain Management", "To Do"),
                    ("Psychology Referral", "To Do")
                ]
            else:
                default_tasks = [
                    ("Initial Assessment", "To Do"),
                    ("Treatment Plan Development", "To Do"),
                    ("Regular Monitoring", "To Do"),
                    ("Patient Education", "To Do")
                ]
                
            # Add default tasks
            for task_name, status in default_tasks:
                task = Task(name=task_name, status=status, program_id=program_id)
                self.db.add_task(task)
            
            # Reload programs
            self.loadPatientPrograms(self.selected_patient_id)
            
            # Log the action
            self.audit_logger.log_data_modification(
                user_id=self.current_user.id,
                action=AuditLog.ACTION_CREATE,
                entity_type=AuditLog.ENTITY_PROGRAM,
                entity_id=program_id,
                details=f"Created new program: {program_name}"
            )
            
            self.status_bar.showMessage(f"Program '{program_name}' added", 3000)
    
    def closeTab(self, index):
        if self.program_tabs.count() <= 1:
            QMessageBox.warning(self, "Warning", "Cannot remove the last program tab")
            return
            
        tab_text = self.program_tabs.tabText(index)
        reply = QMessageBox.question(self, "Confirm Delete", 
                                    f"Are you sure you want to delete program '{tab_text}'?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Get the program ID from the tab widget
            program_widget = self.program_tabs.widget(index)
            if hasattr(program_widget, 'program_id'):
                self.db.delete_program(program_widget.program_id)
            
            self.program_tabs.removeTab(index)
            
            # Log the action
            self.audit_logger.log_data_modification(
                user_id=self.current_user.id,
                action=AuditLog.ACTION_DELETE,
                entity_type=AuditLog.ENTITY_PROGRAM,
                entity_id=program_widget.program_id,
                details=f"Deleted program: {tab_text}"
            )
            
            self.status_bar.showMessage(f"Program '{tab_text}' deleted", 3000)
    
    def showAdminPanel(self):
        """Show the admin panel for system administration tasks."""
        if not self.current_user or not PermissionManager.can_access_admin_panel(self.current_user):
            QMessageBox.warning(self, "Access Denied", "You must be an administrator to access this feature.")
            return
            
        admin_panel = AdminPanel(self.db, self.current_user, self)
        admin_panel.exec_()
    
    def showAuditLogViewer(self):
        """Show the audit log viewer dialog."""
        if not PermissionManager.has_permission(self.current_user, 'audit.view'):
            QMessageBox.warning(self, "Access Denied", "You don't have permission to view audit logs.")
            return
            
        # Log the action
        self.audit_logger.log_data_access(
            user_id=self.current_user.id,
            entity_type=AuditLog.ENTITY_AUDIT,
            entity_id=None,
            details="Viewed audit logs"
        )
            
        # Show the audit log viewer
        dialog = AuditLogViewer(self.db, self.current_user, self)
        dialog.exec_()
    
    def showUserProfile(self):
        """Show the user profile dialog."""
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to view your profile.")
            return
            
        dialog = UserProfileDialog(self.db, self.current_user, self)
        if dialog.exec_() == QDialog.Accepted:
            self.updateUserDisplay()
    
    def sharePatient(self):
        """Show the dialog to share patient access."""
        if not self.selected_patient_id:
            QMessageBox.warning(self, "Warning", "No patient selected")
            return
            
        patient = self.db.get_patient_by_id(self.selected_patient_id)
        if not patient:
            return
            
        # Check if current user has permission to share this patient
        is_owner = (patient.user_id == self.current_user.id)
        has_share_permission = False
        
        if not is_owner:
            shared_access = self.db.get_shared_access(patient.id, self.current_user.id)
            has_share_permission = shared_access and shared_access.access_level == SharedAccess.ACCESS_FULL
            
        if not (is_owner or has_share_permission):
            QMessageBox.warning(self, "Permission Denied", 
                              "You must be the owner or have full access to share this patient.")
            return
            
        # Show share dialog
        dialog = ShareAccessDialog(self.db, patient, self.current_user, self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh patient list to show updated sharing status
            self.loadPatients()
            
            # Log the action
            self.audit_logger.log_event(
                user_id=self.current_user.id,
                action=AuditLog.ACTION_SHARE,
                entity_type=AuditLog.ENTITY_PATIENT,
                entity_id=patient.id,
                details=f"Shared patient access: {patient.first_name} {patient.last_name}"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern style
    window = MedicalPatientManager()
    window.show()
    sys.exit(app.exec_())
