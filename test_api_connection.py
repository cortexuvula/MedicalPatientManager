import requests
import sys
import argparse

def test_api_connection(server_url):
    """Test the connection to the API server."""
    if not server_url.startswith('http'):
        server_url = f"http://{server_url}"
    
    if not server_url.endswith('/api'):
        if server_url.endswith('/'):
            server_url = f"{server_url}api"
        else:
            server_url = f"{server_url}/api"
    
    print(f"Testing connection to: {server_url}")
    
    try:
        response = requests.get(server_url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Connection successful!")
            print("API Response:")
            print(response.json())
            return True
        else:
            print(f"Connection failed with status code: {response.status_code}")
            print("Response content:")
            print(response.text)
            return False
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test API connection')
    parser.add_argument('server_url', nargs='?', default='192.168.1.97:5000', 
                        help='Server URL (default: 192.168.1.97:5000)')
    
    args = parser.parse_args()
    
    success = test_api_connection(args.server_url)
    
    if not success:
        sys.exit(1)
