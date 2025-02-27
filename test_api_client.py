from api_client import ApiClient
from config import Config
import json

def test_api_client_with_url(url):
    """Test API client with a specific URL"""
    print(f"\nTesting with URL: {url}")
    # Update config temporarily
    original_config = Config.get_config()
    Config.update_config({"remote_url": url})
    
    # Create API client
    client = ApiClient()
    
    # Test basic API connection
    print("\nTesting API connection...")
    response = client.test_connection()
    print(f"Connection response: {json.dumps(response, indent=2)}")
    
    # Test login
    print("\nTesting login...")
    login_response = client.login("admin", "admin123")
    # Remove sensitive info for printing
    if login_response and 'user' in login_response:
        login_success = login_response.get('success', False)
        username = login_response.get('user', {}).get('username', 'unknown')
        print(f"Login {'successful' if login_success else 'failed'} for user: {username}")
    else:
        print(f"Login failed: {json.dumps(login_response, indent=2)}")
    
    # Restore original config
    Config.update_config(original_config)
    return response, login_response

if __name__ == "__main__":
    # Test with various URL formats
    urls = [
        "http://192.168.1.97:5000",
        "http://192.168.1.97:5000/",
        "http://192.168.1.97:5000/api",
        "http://192.168.1.97:5000/api/"
    ]
    
    results = {}
    for url in urls:
        conn_response, login_response = test_api_client_with_url(url)
        results[url] = {
            "connection_success": not conn_response.get('error'),
            "login_success": login_response.get('success', False)
        }
    
    # Print summary
    print("\n=== SUMMARY ===")
    for url, result in results.items():
        conn_status = "✓" if result["connection_success"] else "✗"
        login_status = "✓" if result["login_success"] else "✗"
        print(f"URL: {url}")
        print(f"  Connection: {conn_status}")
        print(f"  Login: {login_status}")
