import os
from flask import Flask, request, jsonify, redirect, send_from_directory
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import bcrypt
from security import hash_password
import argparse

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable Cross-Origin Resource Sharing

# Database path
DB_PATH = 'patient_manager.db'

def dict_factory(cursor, row):
    """Convert SQLite Row to dictionary"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    """Get database connection with row factory set to return dictionaries"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

@app.route('/', methods=['GET'])
def root():
    """Root endpoint that serves the configuration page"""
    print("Root endpoint accessed - serving configuration page")
    return send_from_directory('static', 'index.html')

@app.route('/api', methods=['GET'])
def api_root():
    """Root API endpoint that provides information about available endpoints"""
    print(f"API root endpoint accessed")
    api_info = {
        "name": "Medical Patient Manager API",
        "version": "1.0",
        "endpoints": [
            {"path": "/api/health", "methods": ["GET"], "description": "Health check endpoint"},
            {"path": "/api/login", "methods": ["POST"], "description": "User authentication"},
            {"path": "/api/patients", "methods": ["GET", "POST"], "description": "Retrieve or create patients"},
            {"path": "/api/patients/<id>", "methods": ["GET", "PUT", "DELETE"], "description": "Retrieve, update, or delete a specific patient"},
            {"path": "/api/programs", "methods": ["GET", "POST"], "description": "Retrieve or create programs"},
            {"path": "/api/programs/<id>", "methods": ["GET", "PUT", "DELETE"], "description": "Retrieve, update, or delete a specific program"},
            {"path": "/api/shared_patients", "methods": ["GET"], "description": "Get patients shared with a specific user"},
            {"path": "/api/tasks", "methods": ["GET", "POST"], "description": "Retrieve or create tasks"},
            {"path": "/api/tasks/<task_id>", "methods": ["GET", "PUT", "DELETE"], "description": "Retrieve, update, or delete a specific task"},
            {"path": "/api/users/<int:user_id>", "methods": ["GET"], "description": "Get user information by ID"},
            {"path": "/api/users", "methods": ["GET"], "description": "Get all users"},
            {"path": "/api/shared_access", "methods": ["GET", "POST"], "description": "Get or create shared access records"},
            {"path": "/api/shared_access/<int:access_id>", "methods": ["PUT", "DELETE"], "description": "Update or delete a shared access record"}
        ]
    }
    return jsonify(api_info), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API is running"""
    print(f"Health check endpoint accessed")
    return jsonify({"status": "OK", "message": "Server is running"}), 200

@app.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Detailed logging for debugging login issues
    print(f"Login attempt: username={username}")
    
    if not username or not password:
        print(f"Login failed: Missing username or password")
        return jsonify({"error": "Username and password are required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query the database for the user
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        print(f"Login failed: User {username} not found")
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Check if password matches
    stored_password = user.get('password')
    
    # Debug info about stored password format (be careful not to log actual passwords)
    print(f"Stored password format check: starts with '$2b$'={stored_password.startswith('$2b$') if stored_password else 'No password'}")
    
    # Try to compare using bcrypt
    try:
        # If stored password is hashed (starts with $2b$)
        if stored_password.startswith('$2b$'):
            password_matches = bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
        else:
            # For unhashed passwords (legacy/test accounts)
            password_matches = (password == stored_password)
            
        if password_matches:
            print(f"Login successful: User {username}")
            # Remove password from user object before returning
            user.pop('password', None)
            return jsonify({"success": True, "user": user}), 200
        else:
            print(f"Login failed: Incorrect password for {username}")
            return jsonify({"error": "Invalid username or password"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Login error occurred"}), 500

@app.route('/api/patients', methods=['GET'])
def get_patients():
    """Get all patients"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM patients')
        patients = cursor.fetchall()
        return jsonify({'patients': patients}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get a specific patient"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
        patient = cursor.fetchone()
        
        if patient:
            return jsonify({'patient': patient}), 200
        else:
            return jsonify({'error': 'Patient not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/patients', methods=['POST'])
def add_patient():
    """Add a new patient"""
    data = request.json
    
    print(f"Received add_patient request with data: {json.dumps(data, indent=2)}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_id = data.get('user_id', 1)  # Default to admin user if not provided
        
        print(f"Inserting patient with user_id: {user_id}, created_at: {current_time}")
        
        cursor.execute('''
            INSERT INTO patients (first_name, last_name, dob, gender, phone, email, address, 
                               insurance_provider, insurance_id, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('first_name'), data.get('last_name'), data.get('dob'),
            data.get('gender'), data.get('phone'), data.get('email'),
            data.get('address'), data.get('insurance_provider'),
            data.get('insurance_id'), data.get('notes'), user_id, current_time
        ))
        
        conn.commit()
        new_id = cursor.lastrowid
        print(f"Successfully added patient with ID: {new_id}")
        
        return jsonify({'success': True, 'id': new_id}), 201
    except Exception as e:
        conn.rollback()
        print(f"ERROR adding patient: {str(e)}")
        # Print table schema for debugging
        try:
            print("Current patients table schema:")
            cursor.execute("PRAGMA table_info(patients)")
            schema = cursor.fetchall()
            for col in schema:
                print(f"  - {col}")
        except Exception as schema_error:
            print(f"Error fetching schema: {schema_error}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """Update a patient"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE patients 
            SET first_name = ?, last_name = ?, dob = ?, gender = ?, phone = ?, 
                email = ?, address = ?, insurance_provider = ?, insurance_id = ?, notes = ?
            WHERE id = ?
        ''', (
            data.get('first_name'), data.get('last_name'), data.get('dob'),
            data.get('gender'), data.get('phone'), data.get('email'),
            data.get('address'), data.get('insurance_provider'),
            data.get('insurance_id'), data.get('notes'), patient_id
        ))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Patient not found'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/patients/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    """Delete a patient"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Patient not found'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/programs', methods=['GET'])
def get_programs():
    """Get all programs for a patient"""
    patient_id = request.args.get('patient_id')
    
    if not patient_id:
        return jsonify({'error': 'Missing patient_id parameter'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM programs WHERE patient_id = ?", (patient_id,))
        programs = cursor.fetchall()
        conn.close()
        
        return jsonify({'programs': programs}), 200
    except Exception as e:
        print(f"Error getting programs: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/programs', methods=['POST'])
def add_program():
    """Add a new program"""
    data = request.json
    
    # Validate required fields
    if not data or 'name' not in data or 'patient_id' not in data:
        return jsonify({'error': 'Missing required fields (name, patient_id)'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO programs (name, patient_id) VALUES (?, ?)",
            (data['name'], data['patient_id'])
        )
        conn.commit()
        program_id = cursor.lastrowid
        
        # Get the newly created program
        cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
        program = cursor.fetchone()
        conn.close()
        
        return jsonify({'success': True, 'program': program}), 201
    except Exception as e:
        print(f"Error adding program: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/programs/<int:program_id>', methods=['GET'])
def get_program(program_id):
    """Get a specific program by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
        program = cursor.fetchone()
        
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        # Convert to dictionary for JSON response
        program_dict = {
            'id': program['id'],
            'name': program['name'],
            'patient_id': program['patient_id'],
            'created_at': program.get('created_at', '')
        }
        
        return jsonify({'program': program_dict}), 200
    except Exception as e:
        print(f"Error getting program {program_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/programs/<int:program_id>', methods=['PUT'])
def update_program(program_id):
    """Update a program"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get request data
        data = request.get_json()
        
        # Check if program exists
        cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
        program = cursor.fetchone()
        
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        # Update the program
        cursor.execute("UPDATE programs SET name = ? WHERE id = ?", 
                      (data.get('name', program['name']), program_id))
        conn.commit()
        
        print(f"Successfully updated program with ID: {program_id}")
        
        # Get the updated program
        cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
        updated_program = cursor.fetchone()
        
        return jsonify(dict(updated_program)), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating program: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/programs/<int:program_id>', methods=['DELETE'])
def delete_program(program_id):
    """Delete a program"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if program exists
        cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
        program = cursor.fetchone()
        
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        # Delete associated tasks first
        cursor.execute("DELETE FROM tasks WHERE program_id = ?", (program_id,))
        
        # Delete the program
        cursor.execute("DELETE FROM programs WHERE id = ?", (program_id,))
        conn.commit()
        
        print(f"Successfully deleted program with ID: {program_id}")
        return jsonify({'success': True}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error deleting program: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks for a program"""
    program_id = request.args.get('program_id')
    
    if not program_id:
        return jsonify({'error': 'Missing program_id parameter'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE program_id = ?", (program_id,))
        tasks = cursor.fetchall()
        
        return jsonify({'tasks': tasks}), 200
    except Exception as e:
        print(f"Error getting tasks: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Add a new task"""
    data = request.json
    
    # Validate required fields
    if not data or 'name' not in data or 'program_id' not in data:
        return jsonify({'error': 'Missing required fields (name, program_id)'}), 400
    
    # Default values for optional fields
    description = data.get('description', '')
    status = data.get('status', 'To Do')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (name, description, status, program_id) VALUES (?, ?, ?, ?)",
            (data['name'], description, status, data['program_id'])
        )
        conn.commit()
        task_id = cursor.lastrowid
        
        # Get the newly created task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        return jsonify({'success': True, 'task': task}), 201
    except Exception as e:
        print(f"Error adding task: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        if task:
            return jsonify({'task': task}), 200
        else:
            return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        print(f"Error getting task: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    data = request.json
    
    # Validate required fields
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing required field (name)'}), 400
    
    # Get current timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First check if task exists
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Update task
        cursor.execute('''
            UPDATE tasks 
            SET name = ?, description = ?, status = ?
            WHERE id = ?
        ''', (
            data.get('name'), 
            data.get('description', ''), 
            data.get('status', 'To Do'),
            task_id
        ))
        
        conn.commit()
        
        # Get updated task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        updated_task = cursor.fetchone()
        
        print(f"Successfully updated task with ID: {task_id}")
        return jsonify({'success': True, 'task': updated_task}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating task: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if task exists
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Delete the task
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        
        print(f"Successfully deleted task with ID: {task_id}")
        return jsonify({'success': True}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error deleting task: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/shared_patients', methods=['GET'])
def get_shared_patients():
    """Get patients shared with a specific user"""
    print("GET /api/shared_patients endpoint accessed")
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400
    
    try:
        conn = get_db_connection()
        # Query for patients shared with this user
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.* 
            FROM patients p
            JOIN shared_access sa ON p.id = sa.patient_id
            WHERE sa.user_id = ?
            """,
            (user_id,)
        )
        
        shared_patients = cursor.fetchall()
        conn.close()
        
        return jsonify({'shared_patients': shared_patients}), 200
    except Exception as e:
        print(f"Error getting shared patients: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the user, excluding password
        cursor.execute(
            "SELECT id, username, name, email, role, created_at FROM users WHERE id = ?", 
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Convert to dictionary and return
        return jsonify({'user': dict(user)}), 200
    except Exception as e:
        print(f"Error getting user: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all users, excluding passwords
        cursor.execute(
            "SELECT id, username, name, email, role, created_at FROM users ORDER BY username"
        )
        users = cursor.fetchall()
        
        # Convert to list of dictionaries
        users_list = [dict(user) for user in users]
        
        return jsonify({'users': users_list}), 200
    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Shared Access API endpoints
@app.route('/api/shared_access', methods=['GET'])
def get_shared_access():
    """Get shared access records for a patient."""
    try:
        patient_id = request.args.get('patient_id', type=int)
        if not patient_id:
            return jsonify({'error': 'Missing patient_id parameter'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM shared_access WHERE patient_id = ?",
            (patient_id,)
        )
        rows = cursor.fetchall()
        
        shared_access = []
        for row in rows:
            shared_access.append({
                'id': row['id'],
                'patient_id': row['patient_id'],
                'user_id': row['user_id'],
                'granted_by': row['granted_by'],
                'access_level': row['access_level'],
                'granted_at': row['granted_at'] if 'granted_at' in row.keys() else None
            })
        
        return jsonify({'shared_access': shared_access})
    except Exception as e:
        print(f"Error getting shared access: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shared_access', methods=['POST'])
def add_shared_access():
    """Add a new shared access record."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'user_id', 'granted_by', 'access_level']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO shared_access 
               (patient_id, user_id, granted_by, access_level) 
               VALUES (?, ?, ?, ?)""",
            (data['patient_id'], data['user_id'], data['granted_by'], data['access_level'])
        )
        conn.commit()
        
        # Get the newly created record
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM shared_access WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        
        return jsonify({
            'id': row['id'],
            'patient_id': row['patient_id'],
            'user_id': row['user_id'],
            'granted_by': row['granted_by'],
            'access_level': row['access_level'],
            'granted_at': row['granted_at'] if 'granted_at' in row.keys() else None
        })
    except Exception as e:
        print(f"Error adding shared access: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shared_access/<int:access_id>', methods=['PUT'])
def update_shared_access(access_id):
    """Update a shared access record."""
    try:
        data = request.get_json()
        
        # Validate the access record exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shared_access WHERE id = ?", (access_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Shared access record not found'}), 404
        
        # Update the record
        cursor.execute(
            """UPDATE shared_access 
               SET access_level = ? 
               WHERE id = ?""",
            (data['access_level'], access_id)
        )
        conn.commit()
        
        # Return the updated record
        cursor.execute("SELECT * FROM shared_access WHERE id = ?", (access_id,))
        row = cursor.fetchone()
        
        return jsonify({
            'id': row['id'],
            'patient_id': row['patient_id'],
            'user_id': row['user_id'],
            'granted_by': row['granted_by'],
            'access_level': row['access_level'],
            'granted_at': row['granted_at'] if 'granted_at' in row.keys() else None
        })
    except Exception as e:
        print(f"Error updating shared access: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shared_access/<int:access_id>', methods=['DELETE'])
def delete_shared_access(access_id):
    """Delete a shared access record."""
    try:
        # Validate the access record exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shared_access WHERE id = ?", (access_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Shared access record not found'}), 404
        
        # Delete the record
        cursor.execute("DELETE FROM shared_access WHERE id = ?", (access_id,))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Shared access record deleted'})
    except Exception as e:
        print(f"Error deleting shared access: {e}")
        return jsonify({'error': str(e)}), 500

# Main entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Medical Patient Manager Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--port', default=5000, type=int, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Print server information
    print(f"Starting Medical Patient Manager Server on {args.host}:{args.port}")
    print(f"Database path: {os.path.abspath(DB_PATH)}")
    
    # Run the Flask app
    app.run(host=args.host, port=args.port, debug=args.debug)
