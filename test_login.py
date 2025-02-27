import requests
import json
import argparse

def test_login(server_url, username, password):
    """Test login functionality."""
    # Format the server URL
    if not server_url.startswith('http'):
        server_url = f"http://{server_url}"
    
    if server_url.endswith('/'):
        server_url = server_url[:-1]
    
    if not server_url.endswith('/api'):
        server_url = f"{server_url}/api"
    
    login_url = f"{server_url}/login"
    
    print(f"Testing login at: {login_url}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    try:
        # Make the login request
        response = requests.post(
            login_url,
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Try to parse JSON response
        try:
            response_data = response.json()
            print("Response:")
            print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError:
            print("Response is not JSON:")
            print(response.text)
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test API login')
    parser.add_argument('server_url', help='Server URL (e.g., 192.168.1.97:5000)')
    parser.add_argument('username', help='Username to test')
    parser.add_argument('password', help='Password to test')
    
    args = parser.parse_args()
    
    test_login(args.server_url, args.username, args.password)
