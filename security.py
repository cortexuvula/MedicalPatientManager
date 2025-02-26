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
        
        # Get all permissions for the user's role
        user_permissions = cls.get_permissions(user.role)
        
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
