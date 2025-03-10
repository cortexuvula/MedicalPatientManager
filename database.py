import os
import sqlite3
from models import Patient, Program, Task, User, SharedAccess, AuditLog
from security import hash_password, get_client_ip
from datetime import datetime, timedelta
from config import Config
import bcrypt  # Add bcrypt import for password verification
# For remote mode
try:
    from api_client import ApiClient
except ImportError:
    print("ApiClient not available, remote mode might not work")


class Database:
    """Database handler for the Medical Patient Manager application."""
    
    def __init__(self, db_file=None):
        """Initialize database connection and create tables if they don't exist."""
        # Load configuration
        self.config = Config.load_config()
        self.mode = self.config.get("mode", "local")
        
        # Set database file
        if db_file:
            self.db_file = db_file
        else:
            self.db_file = self.config.get("db_file", "patient_manager.db")
        
        self.conn = None
        self.api_client = None
        
        if self.mode == "local":
            self._connect()
            self._create_tables()
        else:
            # Remote mode
            self.remote_url = self.config.get("remote_url")
            self.api_client = ApiClient()
    
    def _connect(self):
        """Connect to the SQLite database."""
        try:
            # Close existing connection if it exists
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass  # Ignore errors when closing existing connection
            
            # Ensure database file path is valid
            db_dir = os.path.dirname(self.db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None
            return False
    
    def check_connection(self):
        """Ensure the database connection is active and reconnect if necessary."""
        if self.mode != "local":
            return True
            
        if self.conn is None:
            return self._connect()
            
        # Test if connection is still valid
        try:
            self.conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            # Connection is not valid, try to reconnect
            return self._connect()
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            cursor = self.conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
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
                patient_id INTEGER,
                program_id INTEGER NOT NULL,
                order_index INTEGER DEFAULT 0,
                color TEXT DEFAULT "#ffffff",
                priority TEXT DEFAULT "Medium",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP,
                version INTEGER DEFAULT 1,
                FOREIGN KEY (program_id) REFERENCES programs (id) ON DELETE CASCADE
            )
            ''')
            
            # Check if order_index column exists in tasks table and add it if not
            self._ensure_column_exists('tasks', 'order_index', 'INTEGER DEFAULT 0')
            
            # Check if modified_at column exists in tasks table and add it if not
            self._ensure_column_exists('tasks', 'modified_at', 'TIMESTAMP')
            
            # Check if version column exists in tasks table and add it if not
            self._ensure_column_exists('tasks', 'version', 'INTEGER DEFAULT 1')
            
            # Check if color column exists in tasks table and add it if not
            self._ensure_column_exists('tasks', 'color', 'TEXT DEFAULT "#ffffff"')
            
            # Check if priority column exists in tasks table and add it if not
            self._ensure_column_exists('tasks', 'priority', 'TEXT DEFAULT "Medium"')
            
            # Check if patient_id column exists in tasks table and add it if not
            self._ensure_column_exists('tasks', 'patient_id', 'INTEGER')
            
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
            
            # Create program_kanban_config table for storing patient-specific column configurations
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS program_kanban_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER,
                column_config TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (program_id) REFERENCES programs (id) ON DELETE CASCADE
            )
            ''')
            
            # Create an admin user if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                # Create default admin user with hashed password
                hashed_password = hash_password("Admin@123")
                cursor.execute(
                    "INSERT INTO users (username, password_hash, name, role) VALUES (?, ?, ?, ?)",
                    ("admin", hashed_password, "System Administrator", "admin")
                )
            
            # Enable foreign key support
            cursor.execute("PRAGMA foreign_keys = ON")
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            
    def _ensure_column_exists(self, table, column, data_type):
        """Check if a column exists in a table and add it if not."""
        try:
            cursor = self.conn.cursor()
            
            # Attempt to get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [column_info[1] for column_info in cursor.fetchall()]
            
            # Add column if it doesn't exist
            if column not in columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {data_type}")
                print(f"Adding {column} column to {table} table")
                
                # Initialize modified_at timestamps after adding the column
                if column == 'modified_at':
                    cursor.execute(f"UPDATE {table} SET {column} = CURRENT_TIMESTAMP")
                    print(f"Initializing {column} values in {table} table")
                
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
                "INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)",
                (user.username, user.password_hash, user.name, user.email, user.role)
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
        """Get a user by username."""
        if self.mode == "remote":
            # In remote mode, we need to use the API client
            try:
                # Call an API endpoint to get user by username if available
                # Otherwise, create a temporary user object for login verification
                # The actual verification will be done by the login API
                user = User(
                    id=0,  # Temporary ID
                    username=username,
                    password_hash="",  # Password will be verified by API
                    name="Remote User",
                    email="",
                    role="provider"
                )
                return user
            except Exception as e:
                print(f"Error in remote get_user_by_username: {e}")
                return None
        else:
            try:
                # Make sure we're connected to the database
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return None
                        
                cursor = self.conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user_data = cursor.fetchone()
                
                if user_data:
                    try:
                        # Check if password column exists in users table
                        password_field = 'password_hash'
                        if 'password_hash' not in dict(user_data) and 'password' in dict(user_data):
                            password_field = 'password'
                            print("Warning: Using 'password' field instead of 'password_hash'")
                        
                        # Extract role with proper debugging
                        user_data_dict = dict(user_data)
                        print(f"User data keys: {list(user_data_dict.keys())}")
                        
                        role = user_data_dict.get('role', 'provider')
                        print(f"Database role value: '{role}'")
                        
                        user = User(
                            id=user_data['id'],
                            username=user_data['username'],
                            password_hash=user_data[password_field],
                            name=user_data['name'] if 'name' in user_data else None,
                            email=user_data['email'] if 'email' in user_data else None,
                            role=role,
                            created_at=user_data['created_at'] if 'created_at' in user_data else None
                        )
                        # Debug output to verify user role before returning
                        print(f"Creating User object with role: {role}")
                        print(f"User object role after creation: {user.role}")
                        return user
                    except Exception as e:
                        print(f"Error creating User object: {e}")
                        print(f"Available keys in user_data: {list(user_data.keys())}")
                        return None
                else:
                    print(f"No user found with username: {username}")
                return None
            except sqlite3.Error as e:
                print(f"Database error in get_user_by_username: {e}")
                return None
    
    def get_user_by_id(self, user_id):
        """Get a user by ID."""
        if self.mode == "remote":
            try:
                response = self.api_client.get_user(user_id)
                
                if 'error' in response:
                    print(f"API Error getting user by ID: {response['error']}")
                    return None
                    
                if 'user' not in response:
                    print(f"Unexpected response from API: {response}")
                    return None
                    
                user_data = response['user']
                user = User(
                    id=user_data['id'],
                    username=user_data['username'],
                    password_hash='',  # No password from API for security
                    name=user_data['name'],
                    email=user_data['email'],
                    role=user_data['role']
                )
                return user
            except Exception as e:
                print(f"Error in remote get_user_by_id: {e}")
                return None
        else:
            try:
                # Check connection and reconnect if needed
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return None
                    
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    # Convert row to dict for easier access
                    row_dict = dict(row)
                    
                    # Check if 'role' column exists in the row
                    role = User.ROLE_PROVIDER  # Default role
                    if 'role' in row_dict:
                        role = row_dict['role']
                    
                    # Handle password field name differences
                    password_field = 'password_hash'
                    if 'password_hash' not in row_dict and 'password' in row_dict:
                        password_field = 'password'
                        print(f"Warning: Using 'password' field instead of 'password_hash' for user ID {user_id}")
                    
                    user = User(
                        id=row_dict['id'],
                        username=row_dict['username'],
                        password_hash=row_dict.get(password_field, ''),
                        name=row_dict.get('name', ''),
                        email=row_dict.get('email', ''),
                        role=role
                    )
                    return user
                return None
            except sqlite3.Error as e:
                print(f"Error getting user by ID: {e}")
                return None
    
    def get_all_users(self):
        """Get all users from the database."""
        if self.mode == "remote":
            try:
                response = self.api_client.get_users()
                
                if 'error' in response:
                    print(f"Error getting users from API: {response['error']}")
                    return []
                    
                if 'users' not in response:
                    print(f"Unexpected response from API: {response}")
                    return []
                    
                users = []
                for user_data in response['users']:
                    users.append(User(
                        id=user_data.get('id'),
                        username=user_data.get('username', ''),
                        password_hash='',  # Don't include passwords from API for security
                        name=user_data.get('name', ''),
                        email=user_data.get('email', ''),
                        role=user_data.get('role', User.ROLE_PROVIDER)
                    ))
                return users
            except Exception as e:
                print(f"Error in remote get_all_users: {e}")
                return []
                
        # In local mode, use database
        try:
            # Check connection and reconnect if needed
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return []
                
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY username")
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                # Convert row to dict for easier access
                row_dict = dict(row)
                
                # Check if 'role' column exists in the row
                role = User.ROLE_PROVIDER  # Default role
                if 'role' in row_dict:
                    role = row_dict['role']
                
                # Handle password field name differences
                password_field = 'password_hash'
                if 'password_hash' not in row_dict and 'password' in row_dict:
                    password_field = 'password'
                
                user = User(
                    id=row_dict['id'],
                    username=row_dict['username'],
                    password_hash=row_dict.get(password_field, ''),
                    name=row_dict.get('name', ''),
                    email=row_dict.get('email', ''),
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
                "UPDATE users SET username = ?, password_hash = ?, name = ?, email = ?, role = ? WHERE id = ?",
                (user.username, user.password_hash, user.name, user.email, user.role, user.id)
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
        if self.mode == "remote":
            try:
                patient_data = {
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'dob': patient.date_of_birth,  # Map to correct field name
                    # Include required fields with default values
                    'gender': '',
                    'phone': '',
                    'email': '',
                    'address': '',
                    'insurance_provider': '',
                    'insurance_id': '',
                    'notes': ''
                }
                response = self.api_client.add_patient(patient_data)
                if response and response.get('success'):
                    return response.get('patient_id')
                return None
            except Exception as e:
                print(f"API error adding patient: {e}")
                return None
        else:
            try:
                # Ensure database connection is active
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return None
                
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
    
    def get_patients(self, user_id=None):
        """Get all patients or patients for a specific user."""
        if self.mode == "remote":
            try:
                response = self.api_client.get_patients()
                
                if response and not response.get('error'):
                    patients_data = response.get('patients', [])
                    patients = []
                    for data in patients_data:
                        patient = Patient(
                            id=data.get('id'),
                            first_name=data.get('first_name'),
                            last_name=data.get('last_name'),
                            date_of_birth=data.get('dob'),  # Map from server's 'dob' to our 'date_of_birth'
                            user_id=data.get('user_id', 1),  # Default to admin user
                            created_at=data.get('created_at')
                        )
                        patients.append(patient)
                    print(f"Retrieved {len(patients)} patients from API")
                    return patients
                return []
            except Exception as e:
                print(f"API error getting patients: {e}")
                return []
        else:
            try:
                # Ensure database connection is active
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return []
                
                query = "SELECT * FROM patients"
                params = []
                if user_id:
                    query += " WHERE user_id = ?"
                    params.append(user_id)
                    
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
                
                patients = []
                for row in result:
                    patient = Patient(
                        id=row['id'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        date_of_birth=row['date_of_birth'],
                        user_id=row['user_id'],
                        created_at=row['created_at']
                    )
                    patients.append(patient)
                
                return patients
            except sqlite3.Error as e:
                print(f"Error getting patients: {e}")
                return []
    
    def get_patient(self, patient_id):
        """Get a patient by ID."""
        if self.mode == "remote":
            try:
                response = self.api_client.get_patient(patient_id)
                
                if response and not response.get('error'):
                    data = response.get('patient', {})
                    return Patient(
                        id=data.get('id'),
                        first_name=data.get('first_name'),
                        last_name=data.get('last_name'),
                        date_of_birth=data.get('dob'),  # Map from server's 'dob' to our 'date_of_birth'
                        user_id=data.get('user_id', 1),
                        created_at=data.get('created_at')
                    )
                return None
            except Exception as e:
                print(f"API error getting patient {patient_id}: {e}")
                return None
        else:
            try:
                # Ensure database connection is active
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return None
                
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT * FROM patients WHERE id = ?
                ''', (patient_id,))
                
                row = cursor.fetchone()
                if row:
                    return Patient(
                        id=row['id'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        date_of_birth=row['date_of_birth'],
                        user_id=row['user_id'],
                        created_at=row['created_at']
                    )
                return None
            except sqlite3.Error as e:
                print(f"Error getting patient {patient_id}: {e}")
                return None
    
    def get_all_patients(self, user_id=None):
        """Get all patients from the database, optionally filtered by user_id."""
        if self.mode == "remote":
            try:
                response = self.api_client.get_patients()
                
                if 'error' in response:
                    print(f"Error getting patients from API: {response['error']}")
                    return []
                
                if 'patients' not in response:
                    print(f"Unexpected response from API: {response}")
                    return []
                
                patients = []
                for patient_data in response['patients']:
                    patient = Patient(
                        id=patient_data.get('id'),
                        first_name=patient_data.get('first_name', ''),
                        last_name=patient_data.get('last_name', ''),
                        date_of_birth=patient_data.get('date_of_birth', ''),
                        user_id=patient_data.get('user_id')
                    )
                    # If a user_id filter is provided, apply it client-side
                    if not user_id or patient.user_id == user_id:
                        patients.append(patient)
                
                return patients
            except Exception as e:
                print(f"Error in remote get_all_patients: {e}")
                return []
        else:
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
        if self.mode == "remote":
            try:
                response = self.api_client.get_patient(patient_id)
                
                if 'error' in response:
                    print(f"Error getting patient from API: {response['error']}")
                    return None
                
                if 'patient' not in response:
                    print(f"Unexpected response from API: {response}")
                    return None
                
                patient_data = response['patient']
                patient = Patient(
                    id=patient_data['id'],
                    first_name=patient_data['first_name'],
                    last_name=patient_data['last_name'],
                    date_of_birth=patient_data['date_of_birth'],
                    user_id=patient_data['user_id']
                )
                if 'created_at' in patient_data:
                    patient.created_at = patient_data['created_at']
                return patient
                
            except Exception as e:
                print(f"Error in remote get_patient_by_id: {e}")
                return None
                
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
        # In remote mode, use API client to get patients
        if self.mode == "remote":
            try:
                from api_client import ApiClient
                api_client = ApiClient()
                response = api_client.get("patients")
                
                # The API returns a dict with a 'patients' key containing the list
                if isinstance(response, dict) and 'patients' in response:
                    patient_list = response['patients']
                elif isinstance(response, list):
                    patient_list = response
                else:
                    print(f"Error: Unexpected response format from API: {response}")
                    return []
                
                # Convert API response to Patient objects
                patients = []
                for patient_data in patient_list:
                    patient = Patient(
                        id=patient_data.get('id', 0),
                        first_name=patient_data.get('first_name', ''),
                        last_name=patient_data.get('last_name', ''),
                        date_of_birth=patient_data.get('date_of_birth', ''),
                        user_id=patient_data.get('user_id', user_id)
                    )
                    patients.append(patient)
                
                print(f"Retrieved {len(patients)} patients from API")
                return patients
            except Exception as e:
                print(f"Error getting patients from API: {e}")
                return []
                
        # In local mode, use database
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
        if self.mode == "remote":
            try:
                response = self.api_client.update_patient(patient)
                return response.get('success', False)
            except Exception as e:
                print(f"API error updating patient: {e}")
                return False
        else:
            try:
                # Ensure database connection is active
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return False
                
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
        if self.mode == "remote":
            try:
                response = self.api_client.delete_patient(patient_id)
                return response.get('success', False)
            except Exception as e:
                print(f"API error deleting patient: {e}")
                return False
        else:
            try:
                # Ensure database connection is active
                if not self.conn:
                    success = self._connect()
                    if not success:
                        print("Failed to connect to the database")
                        return False
                
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
        if self.mode == "remote":
            try:
                program_data = {
                    'name': program.name,
                    'patient_id': program.patient_id
                }
                response = self.api_client.add_program(program_data)
                if 'error' in response:
                    print(f"Error adding program through API: {response['error']}")
                    return None
                
                if 'program' in response and 'id' in response['program']:
                    program_id = response['program']['id']
                    # Set default kanban columns for the new program
                    default_columns = [
                        {"id": "todo", "title": "To Do"},
                        {"id": "in_progress", "title": "In Progress"},
                        {"id": "done", "title": "Done"}
                    ]
                    self.save_program_kanban_config(program_id, default_columns)
                    return program_id
                
                print(f"Unexpected response from API: {response}")
                return None
                
            except Exception as e:
                print(f"Error in remote add_program: {e}")
                return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO programs (name, patient_id) VALUES (?, ?)",
                (program.name, program.patient_id)
            )
            self.conn.commit()
            program_id = cursor.lastrowid
            
            # Set default kanban columns for the new program
            default_columns = [
                {"id": "todo", "title": "To Do"},
                {"id": "in_progress", "title": "In Progress"},
                {"id": "done", "title": "Done"}
            ]
            self.save_program_kanban_config(program_id, default_columns)
            
            return program_id
        except sqlite3.Error as e:
            print(f"Error adding program: {e}")
            return None
    
    def get_programs_by_patient(self, patient_id):
        """Get all programs for a specific patient."""
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                response = self.api_client.get_programs(patient_id)
                
                if 'error' in response:
                    print(f"Error getting programs from API: {response['error']}")
                    return []
                
                if 'programs' not in response:
                    print(f"Error: Unexpected response format from API for programs: {response}")
                    return []
                
                # Convert API response to Program objects
                programs = []
                for program_data in response['programs']:
                    program = Program(
                        id=program_data['id'],
                        name=program_data['name'],
                        patient_id=program_data['patient_id']
                    )
                    if 'created_at' in program_data:
                        program.created_at = program_data['created_at']
                    programs.append(program)
                
                print(f"Retrieved {len(programs)} programs from API for patient {patient_id}")
                return programs
            except Exception as e:
                print(f"Error getting programs from API: {e}")
                return []
                
        # In local mode, use database
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
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                response = self.api_client.get_program(program_id)
                
                if 'error' in response:
                    print(f"API error getting program by ID: {response['error']}")
                    return None
                    
                if 'program' in response:
                    program_data = response['program']
                    program = Program(
                        id=program_data.get('id'),
                        name=program_data.get('name', ''),
                        patient_id=program_data.get('patient_id')
                    )
                    return program
                    
                print(f"Unexpected response from API: {response}")
                return None
            except Exception as e:
                print(f"Error getting program from API: {e}")
                return None
                
        # In local mode, use database
        try:
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return None
                
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
        print(f"Updating program in mode: {self.mode}")
        
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                program_data = {
                    'name': program.name
                }
                
                print(f"Updating program {program.id} via API")
                response = self.api_client.put(f"programs/{program.id}", data=program_data)
                
                if 'error' in response:
                    print(f"API error updating program: {response['error']}")
                    return False
                
                return True
            except Exception as e:
                print(f"Error updating program via API: {e}")
                return False
        
        # In local mode, use database
        try:
            # Check connection and reconnect if needed
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return False
            
            print(f"Database connection: {self.conn}")
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
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                print(f"Deleting program {program_id} via API")
                response = self.api_client.delete(f"programs/{program_id}")
                
                if 'error' in response:
                    print(f"API error deleting program: {response['error']}")
                    return False
                
                return True
            except Exception as e:
                print(f"Error deleting program via API: {e}")
                return False
        
        # In local mode, use database
        try:
            # Check connection and reconnect if needed
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return False
                
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM programs WHERE id = ?", (program_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting program: {e}")
            return False
    
    # Task operations
    def add_task(self, task):
        """Add a task to the database and return it with the assigned ID."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Get highest order index for the status
        cursor.execute("""
            SELECT COALESCE(MAX(order_index), -1) + 1 AS next_order
            FROM tasks 
            WHERE program_id = ? AND status = ?
        """, (task.program_id, task.status))
        next_order = cursor.fetchone()['next_order']
        
        cursor.execute('''
            INSERT INTO tasks (name, description, status, patient_id, program_id, order_index, color, priority, modified_at, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
        ''', (task.name, task.description, task.status, 
              getattr(task, 'patient_id', None),  # Use getattr to safely handle missing attribute
              task.program_id, next_order, 
              getattr(task, 'color', "#ffffff"),  # Use getattr for color too 
              getattr(task, 'priority', "Medium")))  # And for priority
        
        task_id = cursor.lastrowid
        self.conn.commit()
        
        # Return the task with its new ID
        task.id = task_id
        return task
    
    def get_tasks_by_program(self, program_id):
        """Get all tasks for a specific program."""
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                response = self.api_client.get(f"tasks", params={"program_id": program_id})
                
                if 'tasks' in response and isinstance(response['tasks'], list):
                    # Convert API response to Task objects
                    tasks = []
                    for task_data in response['tasks']:
                        task = Task(
                            id=task_data.get('id', 0),
                            name=task_data.get('name', ''),
                            description=task_data.get('description', ''),
                            status=task_data.get('status', 'To Do'),
                            program_id=task_data.get('program_id', program_id),
                            order_index=task_data.get('order_index', 0),
                            created_at=task_data.get('created_at'),
                            modified_at=task_data.get('modified_at'),
                            version=task_data.get('version', 1)
                        )
                        tasks.append(task)
                    
                    print(f"Retrieved {len(tasks)} tasks from API for program {program_id}")
                    return tasks
                else:
                    print(f"Error: Unexpected response format from API for tasks: {response}")
                    return []
                
            except Exception as e:
                print(f"Error getting tasks from API: {e}")
                return []
                
        # In local mode, use database
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE program_id = ? 
                ORDER BY status, order_index, created_at
            """, (program_id,))
            rows = cursor.fetchall()
            return [Task(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                status=row['status'],
                patient_id=row['patient_id'],
                program_id=row['program_id'],
                order_index=row['order_index'] if 'order_index' in row.keys() else 0,
                color=row['color'] if 'color' in row.keys() else "#ffffff",
                priority=row['priority'] if 'priority' in row.keys() else "Medium",
                created_at=row['created_at'] if 'created_at' in row.keys() else None,
                modified_at=row['modified_at'] if 'modified_at' in row.keys() else None,
                version=row['version'] if 'version' in row.keys() else 1
            ) for row in rows]
        except sqlite3.Error as e:
            print(f"Error getting tasks: {e}")
            return []
    
    def get_task_by_id(self, task_id):
        """Get a task by its ID."""
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                response = self.api_client.get(f"tasks/{task_id}")
                
                if 'error' in response:
                    print(f"API error getting task by ID: {response['error']}")
                    return None
                    
                if 'task' in response:
                    task_data = response['task']
                    task = Task(
                        id=task_data.get('id'),
                        name=task_data.get('name', ''),
                        description=task_data.get('description', ''),
                        status=task_data.get('status', 'To Do'),
                        patient_id=task_data.get('patient_id'),
                        program_id=task_data.get('program_id'),
                        order_index=task_data.get('order_index', 0),
                        color=task_data.get('color', "#ffffff"),
                        priority=task_data.get('priority', "Medium"),
                        version=task_data.get('version', 1)
                    )
                    if 'created_at' in task_data:
                        task.created_at = task_data['created_at']
                    if 'modified_at' in task_data:
                        task.modified_at = task_data['modified_at']
                    return task
                    
                print(f"Unexpected response from API: {response}")
                return None
            except Exception as e:
                print(f"Error getting task from API: {e}")
                return None
                
        # In local mode, use database
        try:
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return None
                
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return Task(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    status=row['status'],
                    patient_id=row['patient_id'],
                    program_id=row['program_id'],
                    order_index=row['order_index'] if 'order_index' in row.keys() else 0,
                    color=row['color'] if 'color' in row.keys() else "#ffffff",
                    priority=row['priority'] if 'priority' in row.keys() else "Medium",
                    created_at=row['created_at'] if 'created_at' in row.keys() else None,
                    modified_at=row['modified_at'] if 'modified_at' in row.keys() else None,
                    version=row['version'] if 'version' in row.keys() else 1
                )
            return None
        except sqlite3.Error as e:
            print(f"Error getting task by ID: {e}")
            return None
    
    def update_task(self, task, expected_version=None):
        """Update a task.
        
        Returns:
            tuple: (success, conflict_data)
                - success (bool): True if the update was successful, False if there was a conflict
                - conflict_data (dict or None): If there was a conflict, contains the server task and client task
        """
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # First check if the task exists and get the current version
        cursor.execute("SELECT version FROM tasks WHERE id = ?", (task.id,))
        row = cursor.fetchone()
        if not row:
            return (False, {"error": "Task not found"})
        
        current_version = row['version']
        
        # If expected_version is provided, check for conflicts
        if expected_version is not None and current_version != expected_version:
            # There's a conflict - another user has modified this task
            # Get the current server version of the task
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task.id,))
            server_task = self._create_task_from_row(cursor.fetchone())
            
            # Return conflict information
            return (False, {
                "server_task": server_task,
                "client_task": task,
                "error": "Conflict detected: This task has been modified by another user."
            })
        
        # No conflict, proceed with the update
        now = datetime.now().isoformat()
        new_version = current_version + 1
        
        cursor.execute(
            """UPDATE tasks 
               SET name = ?, description = ?, status = ?, order_index = ?, 
                   color = ?, priority = ?, version = ?, modified_at = ?
               WHERE id = ?""",
            (task.name, task.description, task.status, task.order_index, 
             task.color if hasattr(task, 'color') else "#ffffff", 
             task.priority if hasattr(task, 'priority') else "Medium",
             new_version, now, task.id)
        )
        
        # Update the task's version
        task.version = new_version
        task.modified_at = now
        
        self.conn.commit()
        return (True, None)
    
    def update_task_status(self, task_id, new_status, expected_version=None):
        """Update only the status of a task with concurrency control."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # First check if the task exists and get the current version
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return (False, {"error": "Task not found"})
        
        task = self._create_task_from_row(row)
        current_version = task.version
        
        # If expected_version is provided, check for conflicts
        if expected_version is not None and current_version != expected_version:
            # There's a conflict - another user has modified this task
            # Return conflict information
            return (False, {
                "server_task": task,
                "error": "Conflict detected: This task has been modified by another user."
            })
        
        # No conflict, proceed with the update
        now = datetime.now().isoformat()
        new_version = current_version + 1
        
        cursor.execute(
            """UPDATE tasks 
               SET status = ?, version = ?, modified_at = ?
               WHERE id = ?""",
            (new_status, new_version, now, task_id)
        )
        
        self.conn.commit()
        
        # Return the updated task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        updated_task = self._create_task_from_row(cursor.fetchone())
        return (True, {"updated_task": updated_task})
    
    def update_task_order(self, task_id, new_order_index):
        """Update only the order of a task."""
        try:
            # Check connection and reconnect if needed
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return False
                
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE tasks SET order_index = ?, modified_at = CURRENT_TIMESTAMP, version = version + 1 WHERE id = ?",
                (new_order_index, task_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating task order: {e}")
            return False
            
    def reorder_tasks(self, task_id, new_index, expected_version=None):
        """Reorder a task within its column.
        
        Args:
            task_id: ID of the task to reorder
            new_index: New position within the column (0-based)
            expected_version: Optional version to check for concurrency control
            
        Returns:
            tuple: (success, conflict_data)
                - success (bool): True if the update was successful, False if there was a conflict
                - conflict_data (dict or None): If there was a conflict, contains error information
        """
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # First get the task to be reordered
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return (False, {"error": "Task not found"})
        
        task = self._create_task_from_row(row)
        current_version = task.version
        
        # If expected_version is provided, check for conflicts
        if expected_version is not None and current_version != expected_version:
            return (False, {
                "server_task": task,
                "error": "Conflict detected: This task has been modified by another user."
            })
        
        # Get all tasks in the same column
        cursor.execute(
            "SELECT id, order_index FROM tasks WHERE program_id = ? AND status = ? ORDER BY order_index",
            (task.program_id, task.status)
        )
        tasks = cursor.fetchall()
        
        # Create a list of task IDs in the current order
        task_ids = [t['id'] for t in tasks]
        
        # If the task is not in the list, return error
        if task_id not in task_ids:
            return (False, {"error": "Task not found in the column"})
        
        # Remove the task from the current position
        task_ids.remove(task_id)
        
        # Insert the task at the new position
        if new_index >= len(task_ids):
            task_ids.append(task_id)
        else:
            task_ids.insert(new_index, task_id)
        
        # Update the order_index for all tasks in the column
        now = datetime.now().isoformat()
        for i, tid in enumerate(task_ids):
            if tid == task_id:
                # Update the version for the reordered task
                new_version = current_version + 1
                cursor.execute(
                    "UPDATE tasks SET order_index = ?, version = ?, modified_at = ? WHERE id = ?",
                    (i, new_version, now, tid)
                )
            else:
                # Just update the order_index for other tasks
                cursor.execute(
                    "UPDATE tasks SET order_index = ? WHERE id = ?",
                    (i, tid)
                )
        
        self.conn.commit()
        return (True, None)
    
    def delete_task(self, task_id):
        """Delete a task."""
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                print(f"Deleting task {task_id} via API")
                response = self.api_client.delete(f"tasks/{task_id}")
                
                if 'error' in response:
                    print(f"API error deleting task: {response['error']}")
                    return False
                
                return True
            except Exception as e:
                print(f"Error deleting task via API: {e}")
                return False
        
        # In local mode, use database
        try:
            # Check connection and reconnect if needed
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return False
                
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting task: {e}")
            return False
    
    def log_action(self, action, entity_type, entity_id, details):
        """Log an action in the audit log."""
        # In remote mode, just log to console but don't try to use the database
        if self.mode == "remote":
            print(f"REMOTE MODE AUDIT LOG: action={action}, entity_type={entity_type}, entity_id={entity_id}, details={details}")
            return 0  # Return a dummy ID
            
        try:
            # Check connection and reconnect if needed
            if not self.check_connection():
                print("Error: Database connection lost and couldn't be re-established")
                return False
                
            print(f"Adding audit log: action={action}, entity_type={entity_type}, entity_id={entity_id}")
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO audit_log 
                   (user_id, action, entity_type, entity_id, details, ip_address) 
                   VALUES (?, ?, ?, ?, ?, ?)""", 
                (self.user.id if hasattr(self, 'user') and self.user else None, action, entity_type, entity_id, details, self._get_client_ip())
            )
            self.conn.commit()
            log_id = cursor.lastrowid
            return log_id
            
        except sqlite3.Error as e:
            print(f"Error adding audit log: {e}")
            return 0
    
    # Added for backward compatibility
    def add_audit_log(self, user_id, action, entity_type, entity_id=None, details=None, ip_address=None):
        """Add an entry to the audit log."""
        return self.log_action(action, entity_type, entity_id, details)
        
    def _get_client_ip(self):
        """Get client IP address for audit logs."""
        # In a real application, you would get this from the request
        # For now, just return localhost
        return "127.0.0.1"
    
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
        # In remote mode, return empty list (audit logs not supported remotely)
        if self.mode == "remote":
            print("REMOTE MODE: Audit logs not available in remote mode")
            return []
            
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
        if self.mode == "remote":
            try:
                # Prepare the data to send to the API
                access_data = {
                    'patient_id': shared_access.patient_id,
                    'user_id': shared_access.user_id,
                    'granted_by': shared_access.granted_by,
                    'access_level': shared_access.access_level
                }
                
                # Call the API
                response = self.api_client.add_shared_access(access_data)
                
                if 'error' in response:
                    print(f"API Error adding shared access: {response['error']}")
                    return False
                
                # Update the shared_access object with the new ID from the API
                if 'id' in response:
                    shared_access.id = response['id']
                
                # Log the access grant
                self.log_action(
                    "GRANT", 
                    "shared_access", 
                    shared_access.id, 
                    f"Access granted to user {shared_access.user_id} for patient {shared_access.patient_id}"
                )
                
                return True
            except Exception as e:
                print(f"Error in remote add_shared_access: {e}")
                return False
        else:
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
                self.log_action(
                    "GRANT", 
                    "shared_access", 
                    shared_access.id, 
                    f"Access granted to user {shared_access.user_id} for patient {shared_access.patient_id}"
                )
                
                return True
            except sqlite3.Error as e:
                print(f"Error adding shared access: {e}")
                return False
    
    def update_shared_access(self, shared_access):
        """Update an existing shared access record."""
        if self.mode == "remote":
            try:
                # Prepare the data to send to the API
                access_data = {
                    'access_level': shared_access.access_level
                }
                
                # Call the API
                response = self.api_client.update_shared_access(shared_access.id, access_data)
                
                if 'error' in response:
                    print(f"API Error updating shared access: {response['error']}")
                    return False
                
                # Log the access update
                self.log_action(
                    "UPDATE", 
                    "shared_access", 
                    shared_access.id, 
                    f"Access updated for user {shared_access.user_id} to {shared_access.access_level}"
                )
                
                return True
            except Exception as e:
                print(f"Error in remote update_shared_access: {e}")
                return False
        else:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "UPDATE shared_access SET access_level = ? WHERE id = ?",
                    (shared_access.access_level, shared_access.id)
                )
                self.conn.commit()
                
                # Log the access update
                self.log_action(
                    "UPDATE", 
                    "shared_access", 
                    shared_access.id, 
                    f"Access updated for user {shared_access.user_id} to {shared_access.access_level}"
                )
                
                return True
            except sqlite3.Error as e:
                print(f"Error updating shared access: {e}")
                return False
    
    def delete_shared_access(self, access_id):
        """Delete a shared access record."""
        if self.mode == "remote":
            try:
                # First get the access record for audit logging (need to know user_id and patient_id)
                # This will be returned from the delete call or we need to get it first
                shared_access = None
                
                # Get all shared access records (regardless of patient)
                # This is inefficient but we need the shared_access record to properly log the deletion
                # It's okay to have a brief inefficiency here since deletions are rare operations
                patients = self.get_all_patients()
                for patient in patients:
                    access_records = self.get_shared_access_for_patient(patient.id)
                    for access in access_records:
                        if access.id == access_id:
                            shared_access = access
                            break
                    if shared_access:
                        break
                
                if not shared_access:
                    print(f"Could not find shared access record with ID {access_id}")
                    return False
                
                # Call the API to delete the access
                response = self.api_client.remove_shared_access(access_id)
                
                if 'error' in response:
                    print(f"API Error deleting shared access: {response['error']}")
                    return False
                    
                # Log the access revocation
                self.log_action(
                    "REVOKE", 
                    "shared_access", 
                    access_id, 
                    f"Access revoked for user {shared_access.user_id} to patient {shared_access.patient_id}"
                )
                
                return True
            except Exception as e:
                print(f"Error in remote delete_shared_access: {e}")
                return False
        else:
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
                self.log_action(
                    "REVOKE", 
                    "shared_access", 
                    access_id, 
                    f"Access revoked for user {row['user_id']} to patient {row['patient_id']}"
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
        if self.mode == "remote":
            try:
                response = self.api_client.get_shared_access(patient_id)
                if 'error' in response:
                    print(f"Error getting shared access from API: {response['error']}")
                    return []
                
                if 'shared_access' not in response:
                    print("No shared_access field in API response")
                    return []
                
                access_list = []
                for access_data in response['shared_access']:
                    access = SharedAccess(
                        id=access_data.get('id'),
                        patient_id=access_data.get('patient_id'),
                        user_id=access_data.get('user_id'),
                        granted_by=access_data.get('granted_by'),
                        access_level=access_data.get('access_level')
                    )
                    if 'granted_at' in access_data:
                        access.granted_at = access_data['granted_at']
                    
                    access_list.append(access)
                
                return access_list
            except Exception as e:
                print(f"Error in remote shared access: {e}")
                return []
        else:
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
        if self.mode == "remote":
            try:
                response = self.api_client.get_shared_patients(user_id)
                if 'error' in response:
                    print(f"Error getting shared patients from API: {response['error']}")
                    return []
                
                if 'shared_patients' not in response:
                    print(f"Unexpected response from API: {response}")
                    return []
                
                # Convert API response to Patient objects
                patients = []
                for patient_data in response['shared_patients']:
                    patient = Patient(
                        id=patient_data['id'],
                        first_name=patient_data['first_name'],
                        last_name=patient_data['last_name'],
                        date_of_birth=patient_data['date_of_birth'],
                        user_id=patient_data['user_id']
                    )
                    if 'created_at' in patient_data:
                        patient.created_at = patient_data['created_at']
                    patients.append(patient)
                return patients
                
            except Exception as e:
                print(f"Error in remote get_shared_patients_for_user: {e}")
                return []
            
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
        # In remote mode, use API client
        if self.mode == "remote":
            try:
                print(f"Getting user name in remote mode for user_id: {user_id}")
                response = self.api_client.get_user(user_id)
                
                if 'error' in response:
                    print(f"API error getting user: {response['error']}")
                    return f"User {user_id}"
                
                if 'user' in response:
                    user = response['user']
                    if user.get('name'):
                        return user['name']
                    elif user.get('username'):
                        return user['username']
                
                return f"User {user_id}"
            except Exception as e:
                print(f"Error getting user from API: {e}")
                return f"User {user_id}"
        
        # In local mode, use database
        try:
            # Check connection and reconnect if needed
            if not self.conn:
                success = self._connect()
                if not success:
                    print("Failed to connect to the database")
                    return "Unknown User"
                
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
    
    def authenticate_user(self, username, password):
        """Authenticate a user."""
        if self.mode == "local":
            user = self.get_user_by_username(username)
            if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return user
            return None
        else:
            # Remote mode - Use API client
            try:
                response = self.api_client.login(username, password)
                if response and not response.get('error') and response.get('success'):
                    user_data = response.get('user', {})
                    user = User(
                        id=user_data.get('id'),
                        username=user_data.get('username'),
                        password_hash='',  # We don't store the password in remote mode
                        name=user_data.get('name'),
                        email=user_data.get('email'),
                        role=user_data.get('role', 'provider'),
                        created_at=user_data.get('created_at')
                    )
                    return user
                return None
            except Exception as e:
                print(f"API authentication error: {e}")
                return None
    
    def get_config(self):
        """Expose the configuration in the Database class"""
        return self.config
    
    def __del__(self):
        """Close the database connection when the object is destroyed."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
        except:
            # Ignore errors during cleanup
            pass
    
    # Program Kanban Configuration methods
    def get_program_kanban_config(self, program_id):
        """Get kanban column configuration for a specific program.
        
        Returns a list of column configuration objects or None if not found."""
        if self.mode == "remote":
            try:
                response = self.api_client.get_program_kanban_config(program_id)
                if 'error' in response:
                    print(f"Error getting program kanban config from API: {response['error']}")
                    return None
                
                if 'config' in response:
                    return response['config']
                
                return None
            except Exception as e:
                print(f"Error in remote get_program_kanban_config: {e}")
                return None
        
        try:
            if not self.conn:
                success = self._connect()
                if not success:
                    return None
                
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT column_config FROM program_kanban_config WHERE program_id = ?",
                (program_id,)
            )
            result = cursor.fetchone()
            
            if result:
                import json
                return json.loads(result[0])
            else:
                # Return the default configuration if no program-specific config exists
                return self.config.get("kanban_columns", [
                    {"id": "todo", "title": "To Do"},
                    {"id": "in_progress", "title": "In Progress"},
                    {"id": "done", "title": "Done"}
                ])
        except sqlite3.Error as e:
            print(f"Error getting program kanban config: {e}")
            return None
    
    def save_program_kanban_config(self, program_id, column_config):
        """Save kanban column configuration for a specific program.
        
        Args:
            program_id: ID of the program
            column_config: List of column configuration objects
            
        Returns:
            True if saved successfully, False otherwise
        """
        if self.mode == "remote":
            try:
                response = self.api_client.save_program_kanban_config(program_id, column_config)
                return 'success' in response and response['success']
            except Exception as e:
                print(f"Error in remote save_program_kanban_config: {e}")
                return False
        
        try:
            if not self.conn:
                success = self._connect()
                if not success:
                    return False
            
            import json
            # Convert column_config to JSON string
            config_json = json.dumps(column_config)
            
            cursor = self.conn.cursor()
            # Check if config already exists for this program
            cursor.execute(
                "SELECT id FROM program_kanban_config WHERE program_id = ?",
                (program_id,)
            )
            result = cursor.fetchone()
            
            if result:
                # Update existing config
                cursor.execute(
                    "UPDATE program_kanban_config SET column_config = ?, updated_at = CURRENT_TIMESTAMP WHERE program_id = ?",
                    (config_json, program_id)
                )
            else:
                # Insert new config
                cursor.execute(
                    "INSERT INTO program_kanban_config (program_id, column_config) VALUES (?, ?)",
                    (program_id, config_json)
                )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error saving program kanban config: {e}")
            return False

    def _create_task_from_row(self, row):
        """Helper method to create a Task object from a database row."""
        return Task(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            status=row['status'],
            patient_id=row['patient_id'] if 'patient_id' in row.keys() else None,
            program_id=row['program_id'],
            order_index=row['order_index'] if 'order_index' in row.keys() else 0,
            color=row['color'] if 'color' in row.keys() else "#ffffff",
            priority=row['priority'] if 'priority' in row.keys() else "Medium",
            created_at=row['created_at'] if 'created_at' in row.keys() else None,
            modified_at=row['modified_at'] if 'modified_at' in row.keys() else None,
            version=row['version'] if 'version' in row.keys() else 1
        )
