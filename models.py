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
    
    def __init__(self, name="", patient_id=None, id=None, created_at=None):
        self.id = id
        self.name = name
        self.patient_id = patient_id
        self.created_at = created_at
    
    def __str__(self):
        return self.name


class Task:
    """Model class for tasks within a program."""
    
    def __init__(self, name="", description="", status="To Do", program_id=None, patient_id=None, id=None, order_index=0, 
                 created_at=None, modified_at=None, version=1, color="#ffffff", priority="Medium"):
        self.id = id
        self.name = name
        self.description = description
        self.status = status
        self.program_id = program_id
        self.patient_id = patient_id
        self.order_index = order_index
        self.created_at = created_at
        self.modified_at = modified_at
        self.version = version
        self.color = color
        self.priority = priority
    
    def __str__(self):
        return self.name


class User:
    """Model class for user authentication and identification."""
    
    # User role constants
    ROLE_ADMIN = "admin"
    ROLE_PROVIDER = "provider"
    ROLE_ASSISTANT = "assistant"
    
    def __init__(self, username="", password_hash="", name="", email="", role=None, id=None, created_at=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash  # This is the hashed password
        self.name = name
        self.email = email
        
        # Debug the role assignment
        print(f"User.__init__ received role: {role}")
        
        # Make sure the role is explicitly set to admin if that's what was passed
        if role == self.ROLE_ADMIN:
            self.role = self.ROLE_ADMIN
        elif role == self.ROLE_ASSISTANT:
            self.role = self.ROLE_ASSISTANT
        else:
            self.role = role or self.ROLE_PROVIDER  # Default to provider role
            
        print(f"User.__init__ setting role to: {self.role}")
        
        self.created_at = created_at
    
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
    ACTION_REVOKE = "revoke"
    ACTION_EXPORT = "export"
    ACTION_IMPORT = "import"
    ACTION_SEARCH = "search"
    ACTION_REPORT = "report"
    ACTION_PERMISSION_CHANGE = "permission_change"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_PASSWORD_RESET = "password_reset"
    ACTION_ACCOUNT_CREATE = "account_create"
    ACTION_ACCOUNT_DISABLE = "account_disable"
    ACTION_SYSTEM_CONFIG = "system_config"
    ACTION_FAILED_LOGIN = "failed_login"
    
    # Entity types
    ENTITY_PATIENT = "patient"
    ENTITY_PROGRAM = "program"
    ENTITY_TASK = "task"
    ENTITY_USER = "user"
    ENTITY_SYSTEM = "system"
    ENTITY_REPORT = "report"
    ENTITY_AUDIT = "audit"
    
    # Severity levels - can be used for filtering and reporting
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_ALERT = "alert"
    SEVERITY_CRITICAL = "critical"
    
    def __init__(self, user_id=None, action=None, entity_type=None, entity_id=None, 
                 details=None, ip_address=None, id=None, severity=None):
        self.id = id
        self.user_id = user_id  # User who performed the action
        self.action = action  # Type of action performed
        self.entity_type = entity_type  # Type of entity affected (patient, program, user, etc.)
        self.entity_id = entity_id  # ID of the affected entity
        self.details = details  # Additional details about the action
        self.timestamp = datetime.now()
        self.ip_address = ip_address  # IP address from which the action was performed
        self.severity = severity or self.SEVERITY_INFO  # Severity level of the event
    
    def is_critical(self):
        """Check if this is a critical event."""
        return self.severity == self.SEVERITY_CRITICAL
    
    def is_security_related(self):
        """Check if this event is security-related."""
        security_actions = [
            self.ACTION_LOGIN, 
            self.ACTION_LOGOUT, 
            self.ACTION_FAILED_LOGIN,
            self.ACTION_PASSWORD_CHANGE,
            self.ACTION_PASSWORD_RESET,
            self.ACTION_PERMISSION_CHANGE,
            self.ACTION_ACCOUNT_CREATE,
            self.ACTION_ACCOUNT_DISABLE
        ]
        return self.action in security_actions
    
    def is_data_access(self):
        """Check if this event involves data access."""
        return self.action == self.ACTION_READ
    
    def is_data_modification(self):
        """Check if this event involves data modification."""
        return self.action in [
            self.ACTION_CREATE, 
            self.ACTION_UPDATE, 
            self.ACTION_DELETE,
            self.ACTION_IMPORT
        ]
    
    def is_sharing_related(self):
        """Check if this event involves sharing permissions."""
        return self.action in [self.ACTION_SHARE, self.ACTION_REVOKE]
    
    def get_formatted_timestamp(self, format="%Y-%m-%d %H:%M:%S"):
        """Get a formatted string of the timestamp."""
        if not self.timestamp:
            return "No timestamp"
            
        if isinstance(self.timestamp, str):
            try:
                # Try to parse the timestamp string to a datetime object
                # SQLite timestamps may have different formats
                try:
                    dt = datetime.strptime(self.timestamp, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        dt = datetime.strptime(self.timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        return self.timestamp
                return dt.strftime(format)
            except Exception as e:
                print(f"Error formatting timestamp '{self.timestamp}': {e}")
                return str(self.timestamp)
        elif isinstance(self.timestamp, datetime):
            return self.timestamp.strftime(format)
        return str(self.timestamp)
    
    def __str__(self):
        """Return a string representation of the audit log entry."""
        timestamp = self.get_formatted_timestamp()
        return f"[{timestamp}] {self.action.upper()} {self.entity_type}:{self.entity_id} by user:{self.user_id}"
