"""
Comprehensive API Test Script

This script performs a full test of the Medical Patient Manager API,
including authentication, patient data access, and other functionality.
"""

import requests
import json
import os
from config import Config

class ApiTester:
    def __init__(self, base_url=None):
        """Initialize the API tester with a base URL"""
        self.base_url = base_url or Config.get_remote_url()
        
        # Remove trailing slash if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
            
        # Make sure the URL includes the /api prefix
        if not self.base_url.endswith('/api'):
            self.base_url = f"{self.base_url}/api"
            
        print(f"API Tester initialized with base URL: {self.base_url}")
        
        # Session for maintaining login state
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def make_request(self, method, endpoint, data=None, params=None):
        """Make an HTTP request to the API."""
        # Ensure endpoint doesn't start with a slash
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            print(f"\nAPI request: {method} {url}")
            
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PUT':
                response = self.session.put(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            print(f"Status code: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                return response_data, response.status_code
            except json.JSONDecodeError:
                print(f"Response text: {response.text}")
                return {"text": response.text}, response.status_code
                
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return {"error": str(e)}, 0
    
    def test_api_root(self):
        """Test the API root endpoint"""
        print("\n=== Testing API Root ===")
        return self.make_request('GET', '')
    
    def test_health(self):
        """Test the health check endpoint"""
        print("\n=== Testing Health Check ===")
        return self.make_request('GET', 'health')
    
    def test_login(self, username, password):
        """Test login functionality"""
        print(f"\n=== Testing Login for {username} ===")
        return self.make_request('POST', 'login', {
            'username': username,
            'password': password
        })
    
    def test_get_patients(self):
        """Test getting all patients"""
        print("\n=== Testing Get Patients ===")
        return self.make_request('GET', 'patients')
    
    def test_get_patient(self, patient_id):
        """Test getting a specific patient"""
        print(f"\n=== Testing Get Patient {patient_id} ===")
        return self.make_request('GET', f'patients/{patient_id}')
    
    def test_get_programs(self):
        """Test getting all programs"""
        print("\n=== Testing Get Programs ===")
        return self.make_request('GET', 'programs')
    
    def run_all_tests(self, username="admin", password="admin123"):
        """Run all tests in sequence"""
        print(f"Running all API tests against {self.base_url}")
        
        # Test basic API functionality
        self.test_api_root()
        self.test_health()
        
        # Test authentication
        login_data, status_code = self.test_login(username, password)
        if not login_data.get('success'):
            print("⚠️ Login failed. Skipping tests that require authentication.")
            return False
        
        # If login succeeded, test data endpoints
        self.test_get_patients()
        
        # Try to get the first patient (if any exist)
        patients_data, status_code = self.test_get_patients()
        if patients_data and isinstance(patients_data, list) and len(patients_data) > 0:
            first_patient_id = patients_data[0].get('id')
            if first_patient_id:
                self.test_get_patient(first_patient_id)
        
        # Test program data
        self.test_get_programs()
        
        print("\n=== All Tests Completed ===")
        return True

def main():
    """Main entry point for the script"""
    # Use configuration URL if available
    config_url = Config.get_remote_url()
    
    # Allow override from command line
    import argparse
    parser = argparse.ArgumentParser(description='Test the Medical Patient Manager API')
    parser.add_argument('--url', default=config_url, 
                        help=f'API URL (default: {config_url})')
    parser.add_argument('--username', default='admin',
                        help='Username for authentication (default: admin)')
    parser.add_argument('--password', default='admin123',
                        help='Password for authentication (default: admin123)')
    
    args = parser.parse_args()
    
    # Create tester and run tests
    tester = ApiTester(args.url)
    tester.run_all_tests(args.username, args.password)

if __name__ == "__main__":
    main()
