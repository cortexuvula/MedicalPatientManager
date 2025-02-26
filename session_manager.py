"""
Session management module for Medical Patient Manager.

This module provides a SessionManager class for tracking user sessions,
which is important for audit logging and security.
"""

import random
import string
import uuid
from datetime import datetime, timedelta


class SessionManager:
    """Manage user sessions for the application."""
    
    def __init__(self):
        """Initialize the session manager."""
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
            'ip_address': ip_address,
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
        # Use UUID for better uniqueness
        return str(uuid.uuid4())
    
    def _clean_expired_sessions(self):
        """Remove expired sessions from the active sessions dictionary."""
        now = datetime.now()
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if now > session['expiry_time']
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
