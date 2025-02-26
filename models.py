from datetime import datetime

class Patient:
    """Model class for patient data."""
    
    def __init__(self, first_name="", last_name="", date_of_birth="", user_id=None, id=None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.user_id = user_id  # Primary owner/creator of patient record
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Program:
    """Model class for patient programs (e.g., diabetes management, CKD management)."""
    
    def __init__(self, name="", patient_id=None, id=None):
        self.id = id
        self.name = name
        self.patient_id = patient_id
    
    def __str__(self):
        return self.name


class Task:
    """Model class for tasks within a program."""
    
    def __init__(self, name="", description="", status="To Do", program_id=None, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.status = status
        self.program_id = program_id
    
    def __str__(self):
        return self.name


class User:
    """Model class for user authentication and identification."""
    
    # User role constants
    ROLE_ADMIN = "admin"
    ROLE_PROVIDER = "provider"
    ROLE_ASSISTANT = "assistant"
    
    def __init__(self, username="", password="", name="", email="", role=None, id=None):
        self.id = id
        self.username = username
        self.password = password  # This will be hashed
        self.name = name
        self.email = email
        self.role = role or self.ROLE_PROVIDER  # Default to provider role
    
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == self.ROLE_ADMIN
        
    def __str__(self):
        return self.username


class SharedAccess:
    """Model for shared patient access between users."""
    
    # Access level constants
    ACCESS_READ = "read"
    ACCESS_WRITE = "write"
    ACCESS_FULL = "full"
    
    def __init__(self, patient_id, user_id, granted_by, access_level, id=None, granted_at=None):
        self.id = id
        self.patient_id = patient_id
        self.user_id = user_id
        self.granted_by = granted_by
        self.access_level = access_level
        self.granted_at = granted_at or datetime.now()
        
    def can_read(self):
        """Check if this access level allows reading."""
        return self.access_level in [self.ACCESS_READ, self.ACCESS_WRITE, self.ACCESS_FULL]
        
    def can_write(self):
        """Check if this access level allows writing."""
        return self.access_level in [self.ACCESS_WRITE, self.ACCESS_FULL]
        
    def can_share(self):
        """Check if this access level allows sharing with others."""
        return self.access_level == self.ACCESS_FULL


class AuditLog:
    """Model for audit logging of sensitive operations."""
    
    # Action types
    ACTION_CREATE = "create"
    ACTION_READ = "read"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_SHARE = "share"
    
    def __init__(self, user_id=None, action=None, entity_type=None, entity_id=None, 
                 details=None, ip_address=None, id=None):
        self.id = id
        self.user_id = user_id  # User who performed the action
        self.action = action  # Type of action performed
        self.entity_type = entity_type  # Type of entity affected (patient, program, user, etc.)
        self.entity_id = entity_id  # ID of the affected entity
        self.details = details  # Additional details about the action
        self.timestamp = datetime.now()
        self.ip_address = ip_address  # IP address from which the action was performed
