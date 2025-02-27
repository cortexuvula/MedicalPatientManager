"""
A simple script to inspect the database schema in the patient_manager.db file
"""
import sqlite3
import os

DB_PATH = 'patient_manager.db'

def inspect_database():
    """Inspect the database schema"""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Found {len(tables)} tables in the database:")
    
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"Columns in {table_name}:")
        for col in columns:
            print(f"  - {col['name']} ({col['type']})")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Row count: {count}")
    
    conn.close()

if __name__ == "__main__":
    inspect_database()
