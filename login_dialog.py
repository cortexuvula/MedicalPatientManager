from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QLabel, QMessageBox, QHBoxLayout,
                             QCheckBox, QTabWidget, QWidget, QComboBox, QGroupBox, QRadioButton, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from models import User
from security import hash_password, verify_password, is_strong_password, LoginAttemptTracker

# Track login attempts
login_tracker = LoginAttemptTracker()

class ConfigDialog(QDialog):
    """Dialog for configuring application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Configuration")
        self.setMinimumWidth(400)
        
        # Load current config
        from config import Config
        self.config = Config.get_config()
        
        # Create UI
        self.initUI()
    
    def initUI(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Mode selection
        mode_group = QGroupBox("Database Mode")
        mode_layout = QVBoxLayout()
        
        self.local_radio = QRadioButton("Local Mode (database on this computer)")
        self.remote_radio = QRadioButton("Remote Mode (connect to server)")
        
        if self.config.get("mode") == "remote":
            self.remote_radio.setChecked(True)
        else:
            self.local_radio.setChecked(True)
        
        mode_layout.addWidget(self.local_radio)
        mode_layout.addWidget(self.remote_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Remote URL
        remote_group = QGroupBox("Remote Server Settings")
        remote_layout = QFormLayout()
        
        self.remote_url = QLineEdit(self.config.get("remote_url", "http://localhost:5000/api"))
        remote_layout.addRow("Server URL:", self.remote_url)
        
        remote_group.setLayout(remote_layout)
        layout.addWidget(remote_group)
        
        # Database file
        db_group = QGroupBox("Local Database Settings")
        db_layout = QFormLayout()
        
        self.db_file = QLineEdit(self.config.get("db_file", "patient_manager.db"))
        db_layout.addRow("Database File:", self.db_file)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        
        save_button.clicked.connect(self.save_config)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_config(self):
        """Save the configuration."""
        from config import Config
        import sys
        import os
        
        # Update config object
        config = {
            "mode": "remote" if self.remote_radio.isChecked() else "local",
            "remote_url": self.remote_url.text(),
            "db_file": self.db_file.text()
        }
        
        # Save to file
        if Config.update_config(config):
            reply = QMessageBox.question(
                self, 
                "Restart Application", 
                "Configuration saved successfully. The application needs to restart to apply changes. Restart now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Accept dialog
                self.accept()
                
                # Restart application
                python = sys.executable
                os.execl(python, python, *sys.argv)
            else:
                QMessageBox.information(
                    self, 
                    "Restart Required", 
                    "You'll need to restart the application manually for changes to take effect."
                )
                self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to save configuration.")


class LoginDialog(QDialog):
    """Dialog for user login."""
    
    userAuthenticated = pyqtSignal(object)  # Signal emitted when user authenticates successfully
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Medical Patient Manager - Login")
        self.setFixedWidth(400)
        self.setFixedHeight(350)
        
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title
        title_label = QLabel("Medical Patient Manager")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        main_layout.addWidget(title_label)
        
        # Tab widget for login/register
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Login tab
        login_widget = QWidget()
        login_layout = QVBoxLayout()
        login_widget.setLayout(login_layout)
        
        # Login form
        login_form = QFormLayout()
        
        self.login_username = QLineEdit()
        login_form.addRow("Username:", self.login_username)
        
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        login_form.addRow("Password:", self.login_password)
        
        login_layout.addLayout(login_form)
        
        # Remember me
        self.remember_me = QCheckBox("Remember me")
        login_layout.addWidget(self.remember_me)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        login_layout.addWidget(self.login_button)
        
        # Add login tab
        self.tab_widget.addTab(login_widget, "Login")
        
        # Register tab
        register_widget = QWidget()
        register_layout = QVBoxLayout()
        register_widget.setLayout(register_layout)
        
        # Register form
        register_form = QFormLayout()
        
        self.register_username = QLineEdit()
        register_form.addRow("Username:", self.register_username)
        
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.Password)
        register_form.addRow("Password:", self.register_password)
        
        self.register_confirm_password = QLineEdit()
        self.register_confirm_password.setEchoMode(QLineEdit.Password)
        register_form.addRow("Confirm Password:", self.register_confirm_password)
        
        self.register_name = QLineEdit()
        register_form.addRow("Full Name:", self.register_name)
        
        self.register_email = QLineEdit()
        register_form.addRow("Email:", self.register_email)
        
        # Add role selector (default to provider, admin can only be set by another admin)
        self.register_role = QComboBox()
        self.register_role.addItem("Provider", User.ROLE_PROVIDER)
        self.register_role.addItem("Assistant", User.ROLE_ASSISTANT)
        register_form.addRow("Role:", self.register_role)
        
        register_layout.addLayout(register_form)
        
        # Password requirements info
        password_info = QLabel("Password must have at least 8 characters, with uppercase, lowercase, numbers, and special characters.")
        password_info.setWordWrap(True)
        password_info.setStyleSheet("font-size: 10px; color: #666;")
        register_layout.addWidget(password_info)
        
        # Register button
        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.register)
        register_layout.addWidget(self.register_button)
        
        # Add register tab
        self.tab_widget.addTab(register_widget, "Register")
        
        # Configuration button
        config_button = QPushButton("Configuration")
        config_button.clicked.connect(self.open_config_dialog)
        main_layout.addWidget(config_button)
    
    def login(self):
        """Handle login button click."""
        username = self.login_username.text()
        password = self.login_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Please enter both username and password.")
            return
        
        # Check if the user is locked out due to too many failed attempts
        if login_tracker.is_locked_out(username):
            remaining_time = login_tracker.get_remaining_lockout_time(username)
            QMessageBox.warning(self, "Account Locked", 
                               f"Too many failed login attempts. Please try again in {remaining_time} minutes.")
            return
        
        # Get user from database and check configuration mode
        from config import Config
        config = Config.get_config()
        mode = config.get("mode", "local")
        
        print(f"Login attempt for {username} in {mode} mode")
        
        if mode == "remote":
            # For remote mode, use API client directly
            try:
                from api_client import ApiClient
                api_client = ApiClient()
                print(f"API client base URL: {api_client.base_url}")
                
                # Try to authenticate via API
                login_response = api_client.login(username, password)
                print(f"API login response: {login_response}")
                
                if login_response.get('success'):
                    # Authentication successful through API
                    login_tracker.record_attempt(username, True)
                    
                    # Create user object from API response
                    user_data = login_response.get('user', {})
                    user = User(
                        id=user_data.get('id', 0),
                        username=username,
                        password_hash="",  # Don't store password
                        name=user_data.get('name', ''),
                        email=user_data.get('email', ''),
                        role=user_data.get('role', 'provider')
                    )
                    
                    # Emit signal and close dialog
                    self.userAuthenticated.emit(user)
                    self.accept()
                    return
                else:
                    # Authentication failed through API
                    error_msg = login_response.get('error', 'Invalid username or password')
                    print(f"API login failed: {error_msg}")
                    login_tracker.record_attempt(username, False)
                    QMessageBox.warning(self, "Login Failed", error_msg)
                    return
            except Exception as e:
                print(f"API login error: {e}")
                QMessageBox.warning(self, "Login Error", f"API connection error: {str(e)}")
                return
        
        # For local mode or if remote authentication failed
        user = self.db.get_user_by_username(username)
        
        if user and verify_password(password, user.password_hash):
            # Authentication successful - record successful attempt
            login_tracker.record_attempt(username, True)
            
            # Log the successful login event
            from audit_logger import AuditLogger
            try:
                AuditLogger.log_event(
                    user_id=user.id,
                    action="login",
                    entity_type="user",
                    entity_id=user.id
                )
            except Exception as e:
                print(f"Warning: Could not log login event: {e}")
            
            # Emit signal and close dialog
            self.userAuthenticated.emit(user)
            self.accept()
        else:
            # Authentication failed - record failed attempt
            login_tracker.record_attempt(username, False)
            
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
    
    def register(self):
        """Register a new user account."""
        username = self.register_username.text().strip()
        password = self.register_password.text()
        confirm_password = self.register_confirm_password.text()
        name = self.register_name.text().strip()
        email = self.register_email.text().strip()
        role = self.register_role.currentData()
        
        # Validate input
        if not username or not password:
            QMessageBox.warning(self, "Missing Fields", "Username and password are required.")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return
            
        if not is_strong_password(password):
            QMessageBox.warning(self, "Weak Password", 
                              "Password must be at least 8 characters and include uppercase, lowercase, numbers, and special characters.")
            return
            
        # Check if username already exists
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            QMessageBox.warning(self, "Username Taken", "This username is already in use. Please choose another.")
            return
            
        # Create and store the new user
        hashed_password = hash_password(password)
        user = User(username=username, password_hash=hashed_password, name=name, email=email, role=role)
        self.db.add_user(user)
        
        QMessageBox.information(self, "Registration Successful", "Your account has been created! You can now log in.")
        self.tab_widget.setCurrentIndex(0)  # Switch to login tab
    
    def open_config_dialog(self):
        """Open the configuration dialog."""
        dialog = ConfigDialog(self)
        dialog.exec_()


class UserProfileDialog(QDialog):
    """Dialog for viewing and editing user profile."""
    
    def __init__(self, db, user, parent=None):
        super().__init__(parent)
        self.db = db
        self.user = user
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("User Profile")
        self.setFixedWidth(400)
        self.setFixedHeight(350)
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form = QFormLayout()
        
        # Username (read-only)
        self.username = QLineEdit(self.user.username)
        self.username.setReadOnly(True)
        form.addRow("Username:", self.username)
        
        # Name
        self.name = QLineEdit(self.user.name or "")
        form.addRow("Full Name:", self.name)
        
        # Email
        self.email = QLineEdit(self.user.email or "")
        form.addRow("Email:", self.email)
        
        # Role (read-only)
        self.role = QLineEdit(self.user.role)
        self.role.setReadOnly(True)
        form.addRow("Role:", self.role)
        
        # Password fields
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Leave blank to keep current password")
        form.addRow("New Password:", self.password)
        
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        form.addRow("Confirm Password:", self.confirm_password)
        
        layout.addLayout(form)
        
        # Password requirement info
        password_info = QLabel("Password must have at least 8 characters, with uppercase, lowercase, numbers, and special characters.")
        password_info.setWordWrap(True)
        password_info.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(password_info)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.saveProfile)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def saveProfile(self):
        """Save changes to user profile."""
        name = self.name.text()
        email = self.email.text()
        password = self.password.text()
        confirm_password = self.confirm_password.text()
        
        # Verify current password
        if password and password != confirm_password:
            QMessageBox.warning(self, "Password Error", 
                              "New passwords do not match.")
            return
        
        # Check password strength if changing password
        if password and not is_strong_password(password):
            QMessageBox.warning(self, "Password Error", 
                              "New password doesn't meet security requirements.\n"
                              "Password must contain at least 8 characters, including "
                              "uppercase, lowercase, numbers and special characters.")
            return
        
        # Update user object
        self.user.name = name
        self.user.email = email
        if password:
            self.user.password = hash_password(password)
        
        # Update in database
        success = self.db.update_user(self.user)
        
        if success:
            QMessageBox.information(self, "Profile Updated", 
                                  "Your profile has been updated successfully.")
            self.accept()
        else:
            QMessageBox.warning(self, "Update Failed", 
                              "An error occurred while updating your profile. Please try again.")
