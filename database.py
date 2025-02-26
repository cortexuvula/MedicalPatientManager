import os
import sqlite3
from models import Patient, Program, Task, User, SharedAccess, AuditLog
from security import hash_password, get_client_ip
from datetime import datetime, timedelta


class Database:
    """Database handler for the Medical Patient Manager application."""
    
    def __init__(self, db_file='patient_manager.db'):
        """Initialize database connection and create tables if they don't exist."""
        self.db_file = db_file
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            cursor = self.conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Check if role column exists in users table and add it if not
            self._ensure_column_exists('users', 'role', 'TEXT DEFAULT "provider"')
            
            # Create patients table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')
            
            # Create programs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                patient_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
            )
            ''')
            
            # Create tasks table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                program_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (program_id) REFERENCES programs (id) ON DELETE CASCADE
            )
            ''')
            
            # Create audit_log table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
            ''')
            
            # Create shared_access table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                access_level TEXT NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')
            
            # Create an admin user if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Create default admin user with hashed password
                hashed_password = hash_password("Admin@123")
                cursor.execute(
                    "INSERT INTO users (username, password, name, role) VALUES (?, ?, ?, ?)",
                    ("admin", hashed_password, "System Administrator", "admin")
                )
            
            # Enable foreign key support
            cursor.execute("PRAGMA foreign_keys = ON")
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            
    def _ensure_column_exists(self, table, column, column_type):
        """Ensure a column exists in a table, adding it if it doesn't."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if column not in columns:
                print(f"Adding {column} column to {table} table")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error ensuring column exists: {e}")
            
    # User operations
    def add_user(self, user):
        """Add a new user to the database."""
        try:
            cursor = self.conn.cursor()
            # Note: user.password should already be hashed before calling this function
            cursor.execute(
                "INSERT INTO users (username, password, name, email, role) VALUES (?, ?, ?, ?, ?)",
                (user.username, user.password, user.name, user.email, user.role)
            )
            self.conn.commit()
            user_id = cursor.lastrowid
            
            # Log user creation
            self.add_audit_log(
                user_id=user_id,
                action="create",
                entity_type="user",
                entity_id=user_id,
                details=f"User account created with username: {user.username}",
                ip_address=get_client_ip()
            )
            
            return user_id
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            return None
    
    def get_user_by_username(self, username):
        """Get a user by their username."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                # Use get() to safely retrieve role with a default if not found
                role = row['role'] if 'role' in row.keys() else 'provider'
                return User(
                    id=row['id'],
                    username=row['username'],
                    password=row['password'],
                    name=row['name'],
                    email=row['email'],
                    role=role
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting user by username: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get a user by ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Check if 'role' column exists in the row
                role = User.ROLE_PROVIDER  # Default role
                if 'role' in row.keys():
                    role = row['role']
                
                user = User(
                    id=row['id'],
                    username=row['username'],
                    password=row['password'],
                    name=row['name'],
                    email=row['email'],
                    role=role
                )
                return user
            return None
        except sqlite3.Error as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    def get_all_users(self):
        """Get all users from the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY username")
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                # Check if 'role' column exists in the row
                role = User.ROLE_PROVIDER  # Default role
                if 'role' in row.keys():
                    role = row['role']
                
                user = User(
                    id=row['id'],
                    username=row['username'],
                    password=row['password'],
                    name=row['name'],
                    email=row['email'],
                    role=role
                )
                users.append(user)
            
            return users
        except sqlite3.Error as e:
            print(f"Error getting all users: {e}")
            return []
    
    def update_user(self, user):
        """Update an existing user."""
        try:
            cursor = self.conn.cursor()
            # Note: user.password should already be hashed before calling this function
            cursor.execute(
                "UPDATE users SET username = ?, password = ?, name = ?, email = ?, role = ? WHERE id = ?",
                (user.username, user.password, user.name, user.email, user.role, user.id)
            )
            self.conn.commit()
            
            # Log user update
            self.add_audit_log(
                user_id=user.id,
                action="update",
                entity_type="user",
                entity_id=user.id,
                details=f"User profile updated for username: {user.username}",
                ip_address=get_client_ip()
            )
            
            return True
        except sqlite3.Error as e:
            print(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id):
        """Delete a user from the database."""
        try:
            cursor = self.conn.cursor()
            
            # Log deletion before actually deleting (for audit purposes)
            self.add_audit_log(
                user_id=None,  # No user (system operation)
                action="delete",
                entity_type="user",
                entity_id=user_id,
                details=f"User account deleted with ID: {user_id}",
                ip_address=get_client_ip()
            )
            
            # Delete the user
            cursor.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False
            
    # Patient operations
    def add_patient(self, patient):
        """Add a new patient to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO patients (first_name, last_name, date_of_birth, user_id) VALUES (?, ?, ?, ?)",
                (patient.first_name, patient.last_name, patient.date_of_birth, patient.user_id)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding patient: {e}")
            return None
    
    def get_all_patients(self, user_id=None):
        """Get all patients from the database, optionally filtered by user_id."""
        try:
            cursor = self.conn.cursor()
            if user_id:
                cursor.execute("SELECT * FROM patients WHERE user_id = ? ORDER BY last_name, first_name", (user_id,))
            else:
                cursor.execute("SELECT * FROM patients ORDER BY last_name, first_name")
            rows = cursor.fetchall()
            return [Patient(
                id=row['id'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                date_of_birth=row['date_of_birth'],
                user_id=row['user_id']
            ) for row in rows]
        except sqlite3.Error as e:
            print(f"Error getting patients: {e}")
            return []
    
    def get_patient_by_id(self, patient_id):
        """Get a patient by their ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
            row = cursor.fetchone()
            if row:
                return Patient(
                    id=row['id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    date_of_birth=row['date_of_birth'],
                    user_id=row['user_id']
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting patient by ID: {e}")
            return None
    
    def get_patients_by_user(self, user_id):
        """Get all patients created by a specific user."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM patients WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            
            patients = []
            for row in rows:
                patient = Patient(
                    id=row['id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    date_of_birth=row['date_of_birth'],
                    user_id=row['user_id']
                )
                patients.append(patient)
            
            return patients
        except sqlite3.Error as e:
            print(f"Error getting patients by user: {e}")
            return []
    
    def update_patient(self, patient):
        """Update an existing patient."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE patients SET first_name = ?, last_name = ?, date_of_birth = ?, user_id = ? WHERE id = ?",
                (patient.first_name, patient.last_name, patient.date_of_birth, patient.user_id, patient.id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating patient: {e}")
            return False
    
    def delete_patient(self, patient_id):
        """Delete a patient and all associated programs and tasks."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting patient: {e}")
            return False
    
    # Program operations
    def add_program(self, program):
        """Add a new program to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO programs (name, patient_id) VALUES (?, ?)",
                (program.name, program.patient_id)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding program: {e}")
            return None
    
    def get_programs_by_patient(self, patient_id):
        """Get all programs for a specific patient."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM programs WHERE patient_id = ? ORDER BY name", (patient_id,))
            rows = cursor.fetchall()
            return [Program(
                id=row['id'],
                name=row['name'],
                patient_id=row['patient_id']
            ) for row in rows]
        except sqlite3.Error as e:
            print(f"Error getting programs: {e}")
            return []
    
    def get_program_by_id(self, program_id):
        """Get a program by its ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
            row = cursor.fetchone()
            if row:
                return Program(
                    id=row['id'],
                    name=row['name'],
                    patient_id=row['patient_id']
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting program by ID: {e}")
            return None
    
    def update_program(self, program):
        """Update an existing program."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE programs SET name = ? WHERE id = ?",
                (program.name, program.id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating program: {e}")
            return False
    
    def delete_program(self, program_id):
        """Delete a program and all associated tasks."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM programs WHERE id = ?", (program_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting program: {e}")
            return False
    
    # Task operations
    def add_task(self, task):
        """Add a new task to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (name, description, status, program_id) VALUES (?, ?, ?, ?)",
                (task.name, task.description, task.status, task.program_id)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding task: {e}")
            return None
    
    def get_tasks_by_program(self, program_id):
        """Get all tasks for a specific program."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE program_id = ? ORDER BY created_at", (program_id,))
            rows = cursor.fetchall()
            return [Task(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                status=row['status'],
                program_id=row['program_id']
            ) for row in rows]
        except sqlite3.Error as e:
            print(f"Error getting tasks: {e}")
            return []
    
    def get_task_by_id(self, task_id):
        """Get a task by its ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return Task(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    status=row['status'],
                    program_id=row['program_id']
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting task by ID: {e}")
            return None
    
    def update_task(self, task):
        """Update an existing task."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE tasks SET name = ?, description = ?, status = ? WHERE id = ?",
                (task.name, task.description, task.status, task.id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating task: {e}")
            return False
    
    def update_task_status(self, task_id, new_status):
        """Update only the status of a task."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (new_status, task_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating task status: {e}")
            return False
    
    def delete_task(self, task_id):
        """Delete a task."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting task: {e}")
            return False
    
    def add_audit_log(self, user_id, action, entity_type, entity_id=None, details=None, ip_address=None):
        """Add an entry to the audit log."""
        try:
            cursor = self.conn.cursor()
            print(f"Adding audit log: user_id={user_id}, action={action}, entity_type={entity_type}, entity_id={entity_id}")
            cursor.execute(
                """INSERT INTO audit_log 
                   (user_id, action, entity_type, entity_id, details, ip_address) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action, entity_type, entity_id, details, ip_address)
            )
            self.conn.commit()
            log_id = cursor.lastrowid
            print(f"Successfully added audit log with ID: {log_id}")
            return log_id
        except sqlite3.Error as e:
            print(f"Error adding audit log: {e}")
            return None
    
    def get_audit_logs(self, user_id=None, action=None, entity_type=None, entity_id=None, 
                     start_date=None, end_date=None, limit=100, offset=0):
        """Retrieve audit logs based on filtering criteria.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action type
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            start_date: Filter logs after this date (string in YYYY-MM-DD format)
            end_date: Filter logs before this date (string in YYYY-MM-DD format)
            limit: Maximum number of logs to retrieve
            offset: Offset for pagination
            
        Returns:
            list: List of matching AuditLog objects
        """
        try:
            cursor = self.conn.cursor()
            
            # Build query dynamically based on provided filters
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)
                
            if action:
                query += " AND action = ?"
                params.append(action)
                
            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)
                
            if entity_id is not None:
                query += " AND entity_id = ?"
                params.append(entity_id)
                
            if start_date:
                query += " AND date(timestamp) >= date(?)"
                params.append(start_date)
                
            if end_date:
                query += " AND date(timestamp) <= date(?)"
                params.append(end_date + " 23:59:59")  # Include the whole day
            
            # Add ordering, limit, and offset
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            print(f"Executing query: {query}")
            print(f"With parameters: {params}")
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            print(f"Fetched {len(rows)} rows from database")
            
            logs = []
            for row in rows:
                log = AuditLog(
                    id=row['id'],
                    user_id=row['user_id'],
                    action=row['action'],
                    entity_type=row['entity_type'],
                    entity_id=row['entity_id'],
                    details=row['details'],
                    ip_address=row['ip_address']
                )
                # Set timestamp if it exists in the row
                if 'timestamp' in dict(row).keys():
                    log.timestamp = row['timestamp']
                logs.append(log)
            
            print(f"Created {len(logs)} AuditLog objects")    
            return logs
            
        except sqlite3.Error as e:
            print(f"Error retrieving audit logs: {e}")
            return []
    
    def get_audit_log_by_id(self, log_id):
        """Get an audit log entry by ID.
        
        Args:
            log_id: ID of the audit log entry
            
        Returns:
            AuditLog: The audit log entry, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM audit_log WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            
            if row:
                log = AuditLog(
                    id=row['id'],
                    user_id=row['user_id'],
                    action=row['action'],
                    entity_type=row['entity_type'],
                    entity_id=row['entity_id'],
                    details=row['details'],
                    ip_address=row['ip_address']
                )
                # Set timestamp if it exists in the row
                log.timestamp = row['timestamp'] if 'timestamp' in row.keys() else None
                return log
                
            return None
            
        except sqlite3.Error as e:
            print(f"Error retrieving audit log by ID: {e}")
            return None
    
    def get_audit_logs_for_entity(self, entity_type, entity_id):
        """Get all audit logs for a specific entity.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            
        Returns:
            list: List of AuditLog objects for the entity
        """
        return self.get_audit_logs(entity_type=entity_type, entity_id=entity_id)
    
    def purge_old_audit_logs(self, days=365):
        """Delete audit logs older than a specified number of days.
        
        Args:
            days: Number of days to keep logs for
            
        Returns:
            int: Number of logs deleted
        """
        try:
            cursor = self.conn.cursor()
            
            # Calculate the cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
            
            # Delete logs older than the cutoff date
            cursor.execute(
                "DELETE FROM audit_log WHERE timestamp < ?",
                (cutoff_date_str,)
            )
            self.conn.commit()
            
            return cursor.rowcount
            
        except sqlite3.Error as e:
            print(f"Error purging old audit logs: {e}")
            return 0
    
    # Shared access operations
    def add_shared_access(self, shared_access):
        """Add a new shared access record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO shared_access 
                    (patient_id, user_id, granted_by, access_level, granted_at) 
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (shared_access.patient_id, shared_access.user_id, 
                 shared_access.granted_by, shared_access.access_level)
            )
            self.conn.commit()
            
            # Get the new ID
            shared_access.id = cursor.lastrowid
            
            # Log the access grant
            self.add_audit_log(
                user_id=shared_access.granted_by,
                action="grant",
                entity_type="shared_access",
                entity_id=shared_access.id,
                details=f"Access granted to user {shared_access.user_id} for patient {shared_access.patient_id}",
                ip_address=get_client_ip()
            )
            
            return True
        except sqlite3.Error as e:
            print(f"Error adding shared access: {e}")
            return False
    
    def update_shared_access(self, shared_access):
        """Update an existing shared access record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE shared_access SET access_level = ? WHERE id = ?",
                (shared_access.access_level, shared_access.id)
            )
            self.conn.commit()
            
            # Log the access update
            self.add_audit_log(
                user_id=shared_access.granted_by,
                action="update",
                entity_type="shared_access",
                entity_id=shared_access.id,
                details=f"Access updated for user {shared_access.user_id} to {shared_access.access_level}",
                ip_address=get_client_ip()
            )
            
            return True
        except sqlite3.Error as e:
            print(f"Error updating shared access: {e}")
            return False
    
    def delete_shared_access(self, access_id):
        """Delete a shared access record."""
        try:
            # First get the access record for audit logging
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM shared_access WHERE id = ?", (access_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
                
            # Delete the access
            cursor.execute("DELETE FROM shared_access WHERE id = ?", (access_id,))
            self.conn.commit()
            
            # Log the access revocation
            self.add_audit_log(
                user_id=row['granted_by'],
                action="revoke",
                entity_type="shared_access",
                entity_id=access_id,
                details=f"Access revoked for user {row['user_id']} to patient {row['patient_id']}",
                ip_address=get_client_ip()
            )
            
            return True
        except sqlite3.Error as e:
            print(f"Error deleting shared access: {e}")
            return False
    
    def get_shared_access(self, patient_id, user_id):
        """Get a shared access record for a patient and user."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM shared_access WHERE patient_id = ? AND user_id = ?",
                (patient_id, user_id)
            )
            row = cursor.fetchone()
            
            if row:
                access = SharedAccess(
                    id=row['id'],
                    patient_id=row['patient_id'],
                    user_id=row['user_id'],
                    granted_by=row['granted_by'],
                    access_level=row['access_level']
                )
                # Set granted_at if it exists in the row
                if 'granted_at' in row.keys():
                    access.granted_at = row['granted_at']
                
                return access
            return None
        except sqlite3.Error as e:
            print(f"Error getting shared access: {e}")
            return None
    
    def get_shared_access_for_patient(self, patient_id):
        """Get all shared access records for a patient."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM shared_access WHERE patient_id = ?",
                (patient_id,)
            )
            rows = cursor.fetchall()
            
            access_list = []
            for row in rows:
                access = SharedAccess(
                    id=row['id'],
                    patient_id=row['patient_id'],
                    user_id=row['user_id'],
                    granted_by=row['granted_by'],
                    access_level=row['access_level']
                )
                # Set granted_at if it exists in the row
                if 'granted_at' in row.keys():
                    access.granted_at = row['granted_at']
                
                access_list.append(access)
            
            return access_list
        except sqlite3.Error as e:
            print(f"Error getting shared access for patient: {e}")
            return []
    
    def get_shared_patients_for_user(self, user_id):
        """Get all patients shared with a user."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT p.* 
                FROM patients p
                JOIN shared_access sa ON p.id = sa.patient_id
                WHERE sa.user_id = ?
                """,
                (user_id,)
            )
            rows = cursor.fetchall()
            
            patients = []
            for row in rows:
                patient = Patient(
                    id=row['id'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    date_of_birth=row['date_of_birth'],
                    user_id=row['user_id']
                )
                patients.append(patient)
            
            return patients
        except sqlite3.Error as e:
            print(f"Error getting shared patients for user: {e}")
            return []
    
    def get_user_name_by_id(self, user_id):
        """Get a user's name or username by ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, username FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return row['name'] if row['name'] else row['username']
            return "Unknown User"
        except sqlite3.Error as e:
            print(f"Error getting user name: {e}")
            return "Unknown User"
    
    def check_patient_access(self, patient_id, user_id, required_level=None):
        """Check if a user has access to a patient with the required level.
        
        Args:
            patient_id: ID of the patient
            user_id: ID of the user
            required_level: Required access level (None for any access)
            
        Returns:
            bool: True if user has required access, False otherwise
        """
        try:
            # Check if user is the owner of the patient
            cursor = self.conn.cursor()
            cursor.execute("SELECT user_id FROM patients WHERE id = ?", (patient_id,))
            row = cursor.fetchone()
            
            if not row:
                return False  # Patient not found
                
            # If user is owner, they have full access
            if row['user_id'] == user_id:
                return True
                
            # Otherwise, check shared access
            shared_access = self.get_shared_access(patient_id, user_id)
            if not shared_access:
                return False  # No shared access
                
            # If no specific level required, any access is sufficient
            if required_level is None:
                return True
                
            # Check for specific access level
            if required_level == SharedAccess.ACCESS_READ:
                return shared_access.can_read()
            elif required_level == SharedAccess.ACCESS_WRITE:
                return shared_access.can_write()
            elif required_level == SharedAccess.ACCESS_FULL:
                return shared_access.can_share()
                
            return False
        except sqlite3.Error as e:
            print(f"Error checking patient access: {e}")
            return False
    
    def __del__(self):
        """Close the database connection when the object is destroyed."""
        if self.conn:
            self.conn.close()
