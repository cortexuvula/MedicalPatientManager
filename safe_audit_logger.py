"""
A wrapper for the AuditLogger that handles errors gracefully,
particularly when running in remote mode.
"""

from audit_logger import AuditLogger

class SafeAuditLogger:
    """A wrapper that adds error handling to all AuditLogger methods."""
    
    def __init__(self, db):
        """Initialize with the same database connection as AuditLogger."""
        self.audit_logger = AuditLogger(db)
        self.db = db  # Keep a reference to check mode
    
    def _safe_execute(self, func, *args, **kwargs):
        """Safely execute an audit logger function with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log to console but don't crash the application
            print(f"Audit logging error (safe mode): {e}")
            return None
    
    def log_login(self, *args, **kwargs):
        """Safely log a login event."""
        return self._safe_execute(self.audit_logger.log_login, *args, **kwargs)
    
    def log_logout(self, *args, **kwargs):
        """Safely log a logout event."""
        return self._safe_execute(self.audit_logger.log_logout, *args, **kwargs)
    
    def log_failed_login(self, *args, **kwargs):
        """Safely log a failed login event."""
        return self._safe_execute(self.audit_logger.log_failed_login, *args, **kwargs)
    
    def log_data_access(self, *args, **kwargs):
        """Safely log a data access event."""
        return self._safe_execute(self.audit_logger.log_data_access, *args, **kwargs)
    
    def log_data_modification(self, *args, **kwargs):
        """Safely log a data modification event."""
        return self._safe_execute(self.audit_logger.log_data_modification, *args, **kwargs)
    
    def log_security_event(self, *args, **kwargs):
        """Safely log a security event."""
        return self._safe_execute(self.audit_logger.log_security_event, *args, **kwargs)
    
    def log_event(self, *args, **kwargs):
        """Safely log a generic event."""
        return self._safe_execute(self.audit_logger.log_event, *args, **kwargs)
    
    def get_user_activity(self, *args, **kwargs):
        """Safely get user activity logs."""
        return self._safe_execute(self.audit_logger.get_user_activity, *args, **kwargs)
