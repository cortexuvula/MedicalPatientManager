"""
A script to inspect the tasks table in the database
"""
import sqlite3

def inspect_tasks_table():
    conn = sqlite3.connect('patient_manager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check table schema
    print("Tasks table schema:")
    cursor.execute("PRAGMA table_info(tasks)")
    for col in cursor.fetchall():
        print(f"  - {col['name']} ({col['type']})")
    
    # Count rows
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    print(f"Number of tasks: {count}")
    
    # Sample tasks
    if count > 0:
        print("\nSample tasks:")
        cursor.execute("SELECT * FROM tasks LIMIT 5")
        tasks = cursor.fetchall()
        for task in tasks:
            print(f"  ID: {task['id']}")
            print(f"  Name: {task['name']}")
            print(f"  Status: {task['status']}")
            print(f"  Program ID: {task['program_id']}")
            print()
    
    conn.close()

if __name__ == "__main__":
    inspect_tasks_table()
