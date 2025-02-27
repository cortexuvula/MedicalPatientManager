import re
import bcrypt
import socket
import random
import string
import time
from datetime import datetime, timedelta


def hash_password(password):
    """Hash a password using bcrypt.
    
    Args:
        password (str): The plaintext password to hash
        
    Returns:
        str: The hashed password
    """
    # Convert to bytes if it's a string
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    
    # Return as string for storage
    return hashed.decode('utf-8')


def verify_password(password, hashed_password):
    """Verify a password against its hash.
    
    Args:
        password (str): The plaintext password to check
        hashed_password (str): The stored hashed password to check against
        
    Returns:
        bool: True if password matches hash, False otherwise
    """
    # Convert inputs to bytes if they're strings
    if isinstance(password, str):
        password = password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    
    # Check the password against the hash
    try:
        return bcrypt.checkpw(password, hashed_password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


def is_strong_password(password, min_length=8):
    """Check if a password meets minimum security requirements.
    
    Args:
        password (str): The password to check
        min_length (int): Minimum password length (default 8)
        
    Returns:
        bool: True if password is strong enough, False otherwise
    """
    if not password or len(password) < min_length:
        return False
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True


def get_client_ip():
    """Get the client's IP address for audit logging.
    
    Returns:
        str: The client IP address or a placeholder
    """
    # This is a placeholder - in a real application, this would
    # get the actual client IP from the request context
    return "127.0.0.1"


class LoginAttemptTracker:
    """Track login attempts to prevent brute force attacks."""
    
    MAX_ATTEMPTS = 5  # Maximum number of failed attempts before lockout
    LOCKOUT_DURATION = 15  # Lockout duration in minutes
    
    def __init__(self):
        self.attempts = {}  # Format: {'username': [(timestamp, success), ...]}
    
    def record_attempt(self, username, success):
        """Record a login attempt.
        
        Args:
            username (str): The username being used
            success (bool): Whether the login attempt was successful
        """
        if username not in self.attempts:
            self.attempts[username] = []
        
        # Add the current attempt
        now = datetime.now()
        self.attempts[username].append((now, success))
        
        # If successful, clear previous failed attempts
        if success:
            self.attempts[username] = [(now, True)]
    
    def get_recent_failed_attempts(self, username, window_minutes=30):
        """Get the number of recent failed attempts for a username.
        
        Args:
            username (str): The username to check
            window_minutes (int): The time window to check in minutes
            
        Returns:
            int: The number of failed attempts in the specified window
        """
        if username not in self.attempts:
            return 0
        
        # Calculate the cutoff time
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        # Count recent failed attempts
        failed = 0
        for timestamp, success in self.attempts[username]:
            if timestamp >= cutoff and not success:
                failed += 1
        
        return failed
    
    def is_locked_out(self, username):
        """Check if a user is locked out due to too many failed attempts.
        
        Args:
            username (str): The username to check
            
        Returns:
            bool: True if the user is locked out, False otherwise
        """
        # Check recent failed attempts
        failed_attempts = self.get_recent_failed_attempts(username, self.LOCKOUT_DURATION)
        return failed_attempts >= self.MAX_ATTEMPTS
    
    def get_remaining_lockout_time(self, username):
        """Get the remaining lockout time in minutes.
        
        Args:
            username (str): The username to check
            
        Returns:
            int: The remaining lockout time in minutes, or 0 if not locked out
        """
        if not self.is_locked_out(username) or username not in self.attempts:
            return 0
        
        # Find the most recent failed attempt
        most_recent = None
        for timestamp, success in sorted(self.attempts[username], key=lambda x: x[0], reverse=True):
            if not success:
                most_recent = timestamp
                break
        
        if not most_recent:
            return 0
        
        # Calculate unlock time
        unlock_time = most_recent + timedelta(minutes=self.LOCKOUT_DURATION)
        now = datetime.now()
        
        if now >= unlock_time:
            return 0
        
        # Return remaining minutes
        remaining = (unlock_time - now).total_seconds() / 60
        return round(remaining)


class PermissionManager:
    """Manage role-based permissions within the application."""
    
    # Role hierarchy (higher roles inherit permissions from lower roles)
    ROLE_HIERARCHY = {
        'admin': ['provider', 'assistant'],
        'provider': ['assistant'],
        'assistant': []
    }
    
    # Permission definitions for each role
    ROLE_PERMISSIONS = {
        'admin': [
            'user.create', 'user.read', 'user.update', 'user.delete',
            'patient.create', 'patient.read', 'patient.update', 'patient.delete',
            'program.create', 'program.read', 'program.update', 'program.delete',
            'task.create', 'task.read', 'task.update', 'task.delete',
            'access.grant', 'access.revoke',
            'audit.view',
            'admin.panel'
        ],
        'provider': [
            'patient.create', 'patient.read', 'patient.update', 'patient.delete',
            'program.create', 'program.read', 'program.update', 'program.delete',
            'task.create', 'task.read', 'task.update', 'task.delete',
            'access.grant', 'access.revoke'
        ],
        'assistant': [
            'patient.read',
            'program.read',
            'task.read', 'task.update'
        ]
    }
    
    @classmethod
    def get_permissions(cls, role):
        """Get all permissions for a role, including inherited permissions.
        
        Args:
            role (str): The role to get permissions for
            
        Returns:
            list: All permissions for the role
        """
        if role not in cls.ROLE_HIERARCHY:
            return []
        
        permissions = cls.ROLE_PERMISSIONS.get(role, []).copy()
        
        # Add inherited permissions from subordinate roles
        for inherited_role in cls.ROLE_HIERARCHY.get(role, []):
            permissions.extend(cls.get_permissions(inherited_role))
        
        # Remove duplicates
        return list(set(permissions))
    
    @classmethod
    def has_permission(cls, user, permission):
        """Check if a user has a specific permission.
        
        Args:
            user (User): The user to check
            permission (str): The permission to check
            
        Returns:
            bool: True if the user has the permission, False otherwise
        """
        if not user or not user.role:
            return False
        
        # Debug output
        print(f"Permission check for user role '{user.role}' and permission '{permission}'")
        
        # Get all permissions for the user's role
        user_permissions = cls.get_permissions(user.role)
        
        # Debug output
        print(f"Available permissions for role '{user.role}': {user_permissions}")
        
        # Check if the requested permission is in the user's permissions
        return permission in user_permissions
    
    @classmethod
    def can_access_admin_panel(cls, user):
        """Check if a user can access the admin panel.
        
        Args:
            user (User): The user to check
            
        Returns:
            bool: True if the user can access admin panel, False otherwise
        """
        return cls.has_permission(user, 'admin.panel')
    
    @classmethod
    def can_manage_users(cls, user):
        """Check if a user can manage other users.
        
        Args:
            user (User): The user to check
            
        Returns:
            bool: True if the user can manage users, False otherwise
        """
        return (cls.has_permission(user, 'user.create') and 
                cls.has_permission(user, 'user.update') and 
                cls.has_permission(user, 'user.delete'))
    
    @classmethod
    def can_edit_patient(cls, user, patient):
        """Check if a user can edit a specific patient.
        
        Args:
            user (User): The user to check
            patient (Patient): The patient to check access for
            
        Returns:
            bool: True if the user can edit the patient, False otherwise
        """
        if not user or not patient:
            return False
            
        # Admin can edit any patient
        if user.role == 'admin':
            return True
            
        # Providers can only edit their own patients
        if user.role == 'provider':
            return user.id == patient.user_id
            
        # Assistants cannot edit patients
        return False
    
    @classmethod
    def can_delete_patient(cls, user, patient):
        """Check if a user can delete a specific patient.
        
        Args:
            user (User): The user to check
            patient (Patient): The patient to check access for
            
        Returns:
            bool: True if the user can delete the patient, False otherwise
        """
        if not user or not patient:
            return False
            
        # Admin can delete any patient
        if user.role == 'admin':
            return True
            
        # Providers can only delete their own patients
        if user.role == 'provider':
            return user.id == patient.user_id
            
        # Assistants cannot delete patients
        return False


# Session tracking for audit purposes
class SessionManager:
    """Manage user sessions for tracking and audit purposes."""
    
    def __init__(self):
        self.active_sessions = {}  # Format: {session_id: {'user_id': user_id, 'start_time': datetime, 'last_activity': datetime}}
        self.session_timeout = 30  # minutes
    
    def create_session(self, user_id, ip_address=None):
        """Create a new session for a user.
        
        Args:
            user_id: ID of the user
            ip_address: IP address of the client
            
        Returns:
            str: A unique session ID
        """
        session_id = self._generate_session_id()
        now = datetime.now()
        
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'start_time': now,
            'last_activity': now,
            'ip_address': ip_address or get_client_ip(),
            'expiry_time': now + timedelta(minutes=self.session_timeout)
        }
        
        return session_id
    
    def update_session(self, session_id):
        """Update the last activity time for a session.
        
        Args:
            session_id: ID of the session to update
            
        Returns:
            bool: True if session was updated, False if session not found
        """
        if session_id in self.active_sessions:
            now = datetime.now()
            self.active_sessions[session_id]['last_activity'] = now
            self.active_sessions[session_id]['expiry_time'] = now + timedelta(minutes=self.session_timeout)
            return True
        return False
    
    def end_session(self, session_id):
        """End a session.
        
        Args:
            session_id: ID of the session to end
            
        Returns:
            bool: True if session was ended, False if session not found
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    def is_session_valid(self, session_id):
        """Check if a session is valid and not expired.
        
        Args:
            session_id: ID of the session to check
            
        Returns:
            bool: True if session is valid, False otherwise
        """
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        now = datetime.now()
        
        # Check if session has expired
        if now > session['expiry_time']:
            del self.active_sessions[session_id]
            return False
            
        return True
    
    def get_user_id(self, session_id):
        """Get the user ID for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            int: User ID associated with the session, or None if not found
        """
        if self.is_session_valid(session_id):
            return self.active_sessions[session_id]['user_id']
        return None
    
    def get_session_info(self, session_id):
        """Get all info for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            dict: Session info, or None if not found
        """
        if self.is_session_valid(session_id):
            return self.active_sessions[session_id]
        return None
    
    def get_active_sessions_count(self):
        """Get the number of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        # Remove expired sessions first
        self._clean_expired_sessions()
        return len(self.active_sessions)
    
    def get_user_sessions(self, user_id):
        """Get all active sessions for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            list: List of session IDs for the user
        """
        # Remove expired sessions first
        self._clean_expired_sessions()
        
        return [
            session_id for session_id, session in self.active_sessions.items()
            if session['user_id'] == user_id
        ]
    
    def end_all_user_sessions(self, user_id):
        """End all sessions for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Number of sessions ended
        """
        sessions_to_end = self.get_user_sessions(user_id)
        
        for session_id in sessions_to_end:
            self.end_session(session_id)
            
        return len(sessions_to_end)
    
    def _generate_session_id(self):
        """Generate a unique session ID.
        
        Returns:
            str: A unique session ID
        """
        # Generate a random string of 32 characters
        chars = string.ascii_letters + string.digits
        session_id = ''.join(random.choice(chars) for _ in range(32))
        
        # Make sure it's unique
        while session_id in self.active_sessions:
            session_id = ''.join(random.choice(chars) for _ in range(32))
            
        return session_id
    
    def _clean_expired_sessions(self):
        """Remove expired sessions from the active sessions dictionary."""
        now = datetime.now()
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if now > session['expiry_time']
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]


# Sensitive data handling
def mask_sensitive_data(data, fields_to_mask=None):
    """Mask sensitive data in a dictionary.
    
    Args:
        data (dict): Dictionary containing potentially sensitive data
        fields_to_mask (list): List of field names to mask, or None to use defaults
        
    Returns:
        dict: Dictionary with sensitive fields masked
    """
    if not data:
        return data
        
    if not fields_to_mask:
        fields_to_mask = [
            'password', 'ssn', 'social_security', 'credit_card', 'card_number',
            'date_of_birth', 'dob', 'address', 'phone', 'email'
        ]
    
    # Create a copy to avoid modifying the original
    masked_data = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively mask nested dictionaries
            masked_data[key] = mask_sensitive_data(value, fields_to_mask)
        elif isinstance(value, (list, tuple)):
            # Handle lists or tuples of dictionaries
            if value and isinstance(value[0], dict):
                masked_data[key] = [mask_sensitive_data(item, fields_to_mask) for item in value]
            else:
                masked_data[key] = value
        elif key.lower() in [f.lower() for f in fields_to_mask]:
            # Mask the sensitive field
            if value is None:
                masked_data[key] = None
            elif isinstance(value, str):
                if len(value) > 4:
                    # Show only the last 4 characters for some fields
                    if key.lower() in ['credit_card', 'card_number']:
                        masked_data[key] = '****' + value[-4:]
                    else:
                        masked_data[key] = '******'
                else:
                    masked_data[key] = '******'
            else:
                masked_data[key] = '******'
        else:
            # Pass through non-sensitive data
            masked_data[key] = value
            
    return masked_data


def is_sensitive_field(field_name):
    """Check if a field is considered sensitive.
    
    Args:
        field_name (str): The name of the field to check
        
    Returns:
        bool: True if the field is sensitive, False otherwise
    """
    sensitive_fields = [
        'password', 'ssn', 'social_security', 'credit_card', 'card_number',
        'date_of_birth', 'dob', 'address', 'phone', 'email'
    ]
    
    return field_name.lower() in [f.lower() for f in sensitive_fields]


def sanitize_data_for_logs(data):
    """Sanitize data for safe logging.
    
    This function masks sensitive fields and prepares data for
    inclusion in audit logs.
    
    Args:
        data: The data to sanitize (dict, list, or primitive)
        
    Returns:
        The sanitized data safe for logging
    """
    if isinstance(data, dict):
        return mask_sensitive_data(data)
    elif isinstance(data, (list, tuple)) and data and isinstance(data[0], dict):
        return [mask_sensitive_data(item) for item in data]
    else:
        # For primitive types, just return as is
        return data


# Enhanced IP detection
def get_client_info():
    """Get extended client information for audit logging.
    
    Returns:
        dict: A dictionary of client information
    """
    client_info = {
        'ip_address': get_client_ip(),
        'hostname': socket.gethostname(),
        'timestamp': datetime.now().isoformat()
    }
    
    return client_info


# Token generation for secure operations
def generate_secure_token(length=32):
    """Generate a secure random token.
    
    Args:
        length (int): The length of the token to generate
        
    Returns:
        str: A secure random token
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
