"""
Script to add missing columns to the patients table in the server database
"""
import sqlite3
import os

DB_PATH = 'patient_manager.db'

def add_missing_columns():
    """Add missing columns to the patients table"""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(patients)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # Define missing columns
    missing_columns = [
        ("dob", "TEXT"),  # Alias for date_of_birth
        ("gender", "TEXT"),
        ("phone", "TEXT"),
        ("email", "TEXT"),
        ("address", "TEXT"),
        ("insurance_provider", "TEXT"),
        ("insurance_id", "TEXT"),
        ("notes", "TEXT")
    ]
    
    # Add missing columns
    added_count = 0
    for col_name, col_type in missing_columns:
        if col_name not in column_names:
            try:
                print(f"Adding column {col_name} ({col_type}) to patients table...")
                cursor.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_type}")
                added_count += 1
            except sqlite3.Error as e:
                print(f"Error adding column {col_name}: {e}")
    
    # Create triggers to synchronize dob with date_of_birth
    try:
        # Create trigger to copy date_of_birth to dob when inserting
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS sync_dob_insert AFTER INSERT ON patients
            BEGIN
                UPDATE patients SET dob = NEW.date_of_birth WHERE id = NEW.id AND NEW.date_of_birth IS NOT NULL;
            END;
        """)
        
        # Create trigger to copy dob to date_of_birth when inserting
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS sync_date_of_birth_insert AFTER INSERT ON patients
            BEGIN
                UPDATE patients SET date_of_birth = NEW.dob WHERE id = NEW.id AND NEW.dob IS NOT NULL;
            END;
        """)
        
        # Create trigger to sync dob when date_of_birth is updated
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS sync_dob_update AFTER UPDATE OF date_of_birth ON patients
            BEGIN
                UPDATE patients SET dob = NEW.date_of_birth WHERE id = NEW.id AND NEW.date_of_birth IS NOT NULL;
            END;
        """)
        
        # Create trigger to sync date_of_birth when dob is updated
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS sync_date_of_birth_update AFTER UPDATE OF dob ON patients
            BEGIN
                UPDATE patients SET date_of_birth = NEW.dob WHERE id = NEW.id AND NEW.dob IS NOT NULL;
            END;
        """)
        
        print("Created synchronization triggers between dob and date_of_birth")
    except sqlite3.Error as e:
        print(f"Error creating triggers: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"Added {added_count} missing columns to the patients table")
    print("Database schema update complete!")

if __name__ == "__main__":
    add_missing_columns()
