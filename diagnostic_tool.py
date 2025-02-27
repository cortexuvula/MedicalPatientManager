"""
Medical Patient Manager - Diagnostic Tool

This script performs comprehensive diagnostics on the application configuration,
connections, and authentication to help troubleshoot issues.
"""

import os
import json
import requests
import sys
import socket
import sqlite3
from config import Config
import time

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    """Print a section title."""
    print("\n" + "-" * 40)
    print(f"  {title}")
    print("-" * 40)

def check_config():
    """Check configuration settings."""
    print_section("Configuration Check")
    
    # Load config
    config = Config.get_config()
    print(f"Mode: {config.get('mode', 'local')}")
    print(f"Remote URL: {config.get('remote_url', 'Not set')}")
    print(f"Database file: {config.get('db_file', 'patient_manager.db')}")
    
    # Validate URL
    if config.get('mode') == 'remote':
        url = config.get('remote_url', '')
        print(f"\nAnalyzing URL: {url}")
        
        if not url:
            print("❌ Error: Remote URL not set in config")
        elif not url.startswith(('http://', 'https://')):
            print("❌ Error: URL does not start with http:// or https://")
        elif url.endswith('/'):
            print("ℹ️ Note: URL ends with / - this is handled by the API client")
        elif not url.endswith('/api') and not url.endswith('/'):
            print("⚠️ Warning: URL should end with /api or / for proper routing")
            
        # Check API endpoint formats
        api_base = url
        if not api_base.endswith('/api'):
            if api_base.endswith('/'):
                api_base = f"{api_base}api"
            else:
                api_base = f"{api_base}/api"
        
        print(f"API endpoints will be constructed as:")
        print(f"  Health check: {api_base}/health")
        print(f"  Login: {api_base}/login")
        print(f"  Patients: {api_base}/patients")

def check_connectivity(url=None):
    """Check network connectivity to the server."""
    print_section("Connectivity Check")
    
    if not url:
        config = Config.get_config()
        if config.get('mode') != 'remote':
            print("Skipping connectivity check - not in remote mode")
            return
        url = config.get('remote_url', '')
    
    if not url:
        print("❌ Error: No URL provided")
        return
        
    # Clean the URL to get just the hostname and port
    import urllib.parse
    parsed_url = urllib.parse.urlparse(url)
    hostname = parsed_url.hostname
    port = parsed_url.port or 80
    
    print(f"Testing connectivity to {hostname}:{port}")
    
    # Test ping
    try:
        import platform
        if platform.system().lower() == 'windows':
            ping_cmd = f"ping -n 1 {hostname}"
        else:
            ping_cmd = f"ping -c 1 {hostname}"
        
        print(f"\nRunning: {ping_cmd}")
        ping_result = os.system(ping_cmd)
        if ping_result == 0:
            print("✅ Ping successful")
        else:
            print("❌ Ping failed")
    except Exception as e:
        print(f"❌ Ping test error: {e}")
    
    # Test socket connection
    try:
        print(f"\nTesting socket connection to {hostname}:{port}")
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        end_time = time.time()
        if result == 0:
            print(f"✅ Socket connection successful ({(end_time - start_time)*1000:.0f}ms)")
        else:
            print(f"❌ Socket connection failed with code {result}")
        sock.close()
    except Exception as e:
        print(f"❌ Socket test error: {e}")
    
    # Test HTTP connection
    try:
        print(f"\nTesting HTTP connection to {url}")
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()
        print(f"✅ HTTP connection successful ({(end_time - start_time)*1000:.0f}ms)")
        print(f"  Status code: {response.status_code}")
        print(f"  Content type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"  Response size: {len(response.content)} bytes")
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP connection error: {e}")

def check_api(url=None):
    """Check API endpoints."""
    print_section("API Endpoint Check")
    
    if not url:
        config = Config.get_config()
        if config.get('mode') != 'remote':
            print("Skipping API check - not in remote mode")
            return
        url = config.get('remote_url', '')
    
    if not url:
        print("❌ Error: No URL provided")
        return
    
    # Ensure URL has /api suffix
    api_base = url
    if not api_base.endswith('/api'):
        if api_base.endswith('/'):
            api_base = f"{api_base}api"
        else:
            api_base = f"{api_base}/api"
    
    # Test API root
    try:
        print(f"Testing API root: {api_base}")
        response = requests.get(api_base)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                print(f"  Response: {json.dumps(response.json(), indent=2)[:200]}...")
            except:
                print(f"  Response is not JSON: {response.text[:100]}...")
        else:
            print(f"  Response: {response.text[:100]}...")
    except requests.exceptions.RequestException as e:
        print(f"❌ API root error: {e}")
    
    # Test health endpoint
    try:
        health_url = f"{api_base}/health"
        print(f"\nTesting health endpoint: {health_url}")
        response = requests.get(health_url)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                print(f"  Response: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"  Response is not JSON: {response.text[:100]}...")
        else:
            print(f"  Response: {response.text[:100]}...")
    except requests.exceptions.RequestException as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Test login endpoint with test credentials
    try:
        login_url = f"{api_base}/login"
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        print(f"\nTesting login endpoint: {login_url}")
        print(f"  Using test credentials: {login_data['username']}/[HIDDEN]")
        
        response = requests.post(login_url, json=login_data)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                json_resp = response.json()
                success = json_resp.get('success', False)
                user_data = json_resp.get('user', {})
                if success:
                    print(f"  ✅ Login successful")
                    print(f"  User: {user_data.get('username')} (ID: {user_data.get('id')})")
                    print(f"  Role: {user_data.get('role')}")
                    print(f"  Name: {user_data.get('name')}")
                else:
                    print(f"  ❌ Login failed: {json_resp.get('error', 'Unknown error')}")
            except:
                print(f"  Response is not JSON: {response.text[:100]}...")
        else:
            print(f"  Response: {response.text[:100]}...")
    except requests.exceptions.RequestException as e:
        print(f"❌ Login endpoint error: {e}")

def check_local_database():
    """Check local database for user records."""
    print_section("Local Database Check")
    
    db_file = Config.get_config().get('db_file', 'patient_manager.db')
    print(f"Database file: {db_file}")
    
    if not os.path.exists(db_file):
        print(f"❌ Database file not found: {db_file}")
        return
    
    print(f"✅ Database file exists: {os.path.abspath(db_file)}")
    print(f"  File size: {os.path.getsize(db_file):,} bytes")
    
    # Check users table
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Users table does not exist in the database")
            return
        
        # Count users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"  User accounts: {user_count}")
        
        # Check admin user
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        admin = cursor.fetchone()
        if admin:
            print("  ✅ Admin user found")
            print(f"    ID: {admin['id']}")
            print(f"    Name: {admin['name']}")
            print(f"    Email: {admin['email']}")
            print(f"    Password format: {'Bcrypt' if admin['password'].startswith('$2b$') else 'Plain text'}")
        else:
            print("  ❌ Admin user not found")
            
            # List first 5 users
            cursor.execute("SELECT id, username, name FROM users LIMIT 5")
            users = cursor.fetchall()
            if users:
                print("\n  Available users:")
                for user in users:
                    print(f"    - {user['username']} (ID: {user['id']}, Name: {user['name']})")
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if conn:
            conn.close()

def main():
    """Main function that runs all diagnostic checks."""
    print_header("Medical Patient Manager - Diagnostic Tool")
    
    # Check args for URL
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Using provided URL: {url}")
    
    check_config()
    check_connectivity(url)
    check_api(url)
    check_local_database()
    
    print("\n" + "=" * 60)
    print("  Diagnostics Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
