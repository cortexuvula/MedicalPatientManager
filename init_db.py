"""
Database initialization script for Medical Patient Manager.
Run this script to recreate the database with the correct schema.
"""
import os
from database import Database
from security import hash_password

# Delete existing database file if it exists
db_file = 'patient_manager.db'
if os.path.exists(db_file):
    print(f"Deleting existing database file: {db_file}")
    os.remove(db_file)
    
# Create new database with proper schema
print("Creating new database...")
db = Database(db_file)

# Verify tables were created
conn = db.conn
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Database tables created:")
for table in tables:
    print(f"- {table[0]}")

print("\nDatabase initialization complete!")
print("You can now run the application using: python run.py")
