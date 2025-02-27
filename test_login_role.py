from database import Database
from security import verify_password

# Create database connection
db = Database()

# Try to get the admin user
username = "admin"
print(f"Looking up user with username '{username}'")
user = db.get_user_by_username(username)

if user:
    print(f"Found user: {user.username}")
    print(f"User role: {user.role}")
    print(f"Is admin? {user.is_admin()}")
else:
    print(f"User '{username}' not found.")
