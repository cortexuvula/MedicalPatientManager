"""
Audit logging module for Medical Patient Manager.

This module provides comprehensive audit logging capabilities for tracking
sensitive operations within the application. It includes functions for logging
various types of events, retrieving logs, and filtering logs based on criteria.
"""

import logging
import datetime
import json
import socket
import uuid
from functools import wraps

from models import AuditLog
from security import get_client_ip

# Configure standard Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app_audit.log',
    filemode='a'
)

# Create a logger
logger = logging.getLogger('audit')

# Sensitive fields that should be masked in logs
SENSITIVE_FIELDS = ['password', 'ssn', 'credit_card', 'date_of_birth']

class AuditLogger:
    """Class for handling audit logging operations."""
    
    def __init__(self, db):
        """Initialize the audit logger with a database connection.
        
        Args:
            db: Database instance for storing audit logs
        """
        self.db = db
    
    def log_event(self, user_id, action, entity_type, entity_id=None, details=None, ip_address=None):
        """Log an event to the audit log.
        
        Args:
            user_id: ID of the user performing the action
            action: Type of action (create, read, update, delete, etc.)
            entity_type: Type of entity being acted upon
            entity_id: ID of the entity being acted upon
            details: Additional details about the action
            ip_address: IP address of the client
            
        Returns:
            int: ID of the created audit log entry
        """
        print(f"AuditLogger.log_event called: user_id={user_id}, action={action}, entity_type={entity_type}")
        # Mask any sensitive information in the details
        masked_details = self._mask_sensitive_data(details)
        
        # Log to database
        log_id = self.db.add_audit_log(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=masked_details,
            ip_address=ip_address or get_client_ip()
        )
        print(f"AuditLogger.log_event database entry created with ID: {log_id}")
        
        # Also log to file for redundancy
        log_data = {
            'user_id': user_id,
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'details': masked_details,
            'ip_address': ip_address or get_client_ip(),
            'timestamp': datetime.datetime.now().isoformat()
        }
        logger.info(f"AUDIT: {json.dumps(log_data)}")
        
        return log_id
    
    def log_login(self, user_id, success, ip_address=None, details=None):
        """Log a login attempt.
        
        Args:
            user_id: ID of the user attempting to log in
            success: Whether the login was successful
            ip_address: IP address of the client
            details: Additional details about the login attempt
        """
        print(f"Logging login event: user_id={user_id}, success={success}")
        action = AuditLog.ACTION_LOGIN
        status = "success" if success else "failure"
        full_details = f"Login {status}. {details or ''}"
        
        return self.log_event(
            user_id=user_id,
            action=action,
            entity_type="user",
            entity_id=user_id,
            details=full_details,
            ip_address=ip_address
        )
    
    def log_logout(self, user_id, ip_address=None):
        """Log a user logout.
        
        Args:
            user_id: ID of the user logging out
            ip_address: IP address of the client
        """
        print(f"Logging logout event: user_id={user_id}")
        return self.log_event(
            user_id=user_id,
            action=AuditLog.ACTION_LOGOUT,
            entity_type="user",
            entity_id=user_id,
            details="User logged out",
            ip_address=ip_address
        )
    
    def log_data_access(self, user_id, entity_type, entity_id, details=None, ip_address=None):
        """Log access to sensitive data.
        
        Args:
            user_id: ID of the user accessing the data
            entity_type: Type of entity being accessed
            entity_id: ID of the entity being accessed
            details: Additional details about the access
            ip_address: IP address of the client
        """
        return self.log_event(
            user_id=user_id,
            action=AuditLog.ACTION_READ,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address
        )
    
    def log_data_modification(self, user_id, action, entity_type, entity_id, 
                             old_values=None, new_values=None, details=None, ip_address=None):
        """Log modification of data.
        
        Args:
            user_id: ID of the user modifying the data
            action: Type of modification (update, delete, etc.)
            entity_type: Type of entity being modified
            entity_id: ID of the entity being modified
            old_values: Previous values before modification
            new_values: New values after modification
            details: Additional details about the modification
            ip_address: IP address of the client
        """
        # Prepare change details
        change_details = details or ""
        
        if old_values and new_values:
            # Create a diff of changes
            changes = []
            for key in set(old_values.keys()) | set(new_values.keys()):
                old_val = old_values.get(key, 'N/A')
                new_val = new_values.get(key, 'N/A')
                
                # Skip if no change
                if old_val == new_val:
                    continue
                
                # Mask sensitive values
                if key in SENSITIVE_FIELDS:
                    old_val = '******' if old_val != 'N/A' else 'N/A'
                    new_val = '******' if new_val != 'N/A' else 'N/A'
                    
                changes.append(f"{key}: {old_val} -> {new_val}")
            
            if changes:
                change_details += " Changes: " + ", ".join(changes)
        
        return self.log_event(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=change_details,
            ip_address=ip_address
        )
    
    def get_logs(self, user_id=None, action=None, entity_type=None, entity_id=None, 
                 start_date=None, end_date=None, limit=100, offset=0):
        """Retrieve audit logs based on filtering criteria.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action type
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            limit: Maximum number of logs to retrieve
            offset: Offset for pagination
            
        Returns:
            list: List of matching AuditLog objects
        """
        return self.db.get_audit_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    
    def _mask_sensitive_data(self, details):
        """Mask sensitive data in log details.
        
        Args:
            details: Details to be masked
            
        Returns:
            str: Masked details
        """
        if not details:
            return details
            
        if isinstance(details, dict):
            masked = details.copy()
            for key in masked:
                if key.lower() in SENSITIVE_FIELDS:
                    masked[key] = '******'
            return json.dumps(masked)
        
        # If it's a string, try to parse as JSON
        if isinstance(details, str):
            try:
                data = json.loads(details)
                if isinstance(data, dict):
                    return self._mask_sensitive_data(data)
            except json.JSONDecodeError:
                pass
                
        # Just return the original string if we can't parse it
        return details


def audit_decorator(action, entity_type):
    """Decorator for auditing method calls.
    
    This decorator can be applied to methods to automatically log them
    to the audit trail. The decorated method must be a method of a class
    that has access to a db attribute.
    
    Args:
        action: The action being performed (create, read, update, delete)
        entity_type: The type of entity being acted upon
        
    Returns:
        decorator: A decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get user ID if available
            user_id = getattr(self, 'current_user', None)
            if user_id and hasattr(user_id, 'id'):
                user_id = user_id.id
                
            # Get entity ID if available
            entity_id = None
            if args and hasattr(args[0], 'id'):
                entity_id = args[0].id
            elif 'id' in kwargs:
                entity_id = kwargs['id']
                
            # Track time for performance monitoring
            start_time = datetime.datetime.now()
            
            # Generate a unique operation ID for correlation
            operation_id = str(uuid.uuid4())
            
            # Log the start of the operation
            details = f"Operation {operation_id} started: {func.__name__}"
            audit_logger = AuditLogger(self.db)
            audit_logger.log_event(
                user_id=user_id,
                action=f"{action}_started",
                entity_type=entity_type,
                entity_id=entity_id,
                details=details
            )
            
            # Call the original function
            try:
                result = func(self, *args, **kwargs)
                
                # Log successful completion
                duration = (datetime.datetime.now() - start_time).total_seconds()
                success_details = f"Operation {operation_id} completed successfully in {duration}s"
                audit_logger.log_event(
                    user_id=user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details=success_details
                )
                
                return result
                
            except Exception as e:
                # Log error
                duration = (datetime.datetime.now() - start_time).total_seconds()
                error_details = f"Operation {operation_id} failed after {duration}s: {str(e)}"
                audit_logger.log_event(
                    user_id=user_id,
                    action=f"{action}_error",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details=error_details
                )
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator
