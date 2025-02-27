from models import User

# Test creating a user with admin role
admin_user = User(
    id=1,
    username="admin",
    password_hash="hashed_password",
    name="Admin User",
    email="admin@example.com",
    role="admin"
)

print(f"Admin user created with role: {admin_user.role}")
print(f"Is admin? {admin_user.is_admin()}")

# Test creating a user with provider role
provider_user = User(
    id=2,
    username="provider",
    password_hash="hashed_password",
    name="Provider User",
    email="provider@example.com",
    role="provider"
)

print(f"Provider user created with role: {provider_user.role}")
print(f"Is admin? {provider_user.is_admin()}")

# Test creating a user with no role (should default to provider)
default_user = User(
    id=3,
    username="default",
    password_hash="hashed_password",
    name="Default User",
    email="default@example.com"
)

print(f"Default user created with role: {default_user.role}")
print(f"Is admin? {default_user.is_admin()}")
