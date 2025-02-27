import sqlite3
import bcrypt
import os

def create_test_user(db_file, username, password, name="Test User", email="test@example.com"):
    """Create a test user in the database."""
    try:
        # Check if the database file exists
        if not os.path.exists(db_file):
            print(f"Database file not found: {db_file}")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Update existing user
            cursor.execute(
                "UPDATE users SET password = ?, name = ?, email = ? WHERE username = ?",
                (hashed_password, name, email, username)
            )
            print(f"Updated existing user: {username}")
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (username, password, name, email, role) VALUES (?, ?, ?, ?, ?)",
                (username, hashed_password, name, email, "admin")
            )
            print(f"Created new user: {username}")
        
        # Commit changes
        conn.commit()
        
        # Verify the user was created
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            print(f"User exists in database: {username}")
            return True
        else:
            print(f"Failed to find user after creation: {username}")
            return False
    
    except Exception as e:
        print(f"Error creating test user: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create a test user in the database')
    parser.add_argument('--db', default='patient_manager.db', help='Database file path')
    parser.add_argument('--username', default='testuser', help='Username for the test user')
    parser.add_argument('--password', default='password123', help='Password for the test user')
    
    args = parser.parse_args()
    
    success = create_test_user(args.db, args.username, args.password)
    
    if success:
        print("Test user created successfully")
    else:
        print("Failed to create test user")
