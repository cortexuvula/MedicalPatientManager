import json
import requests
from config import Config

class ApiClient:
    """Client for interacting with the remote API."""
    
    def __init__(self):
        """Initialize the API client with the remote URL from config."""
        self.base_url = Config.get_remote_url()
        # Remove trailing slash if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
            
        # Make sure the URL includes the /api prefix
        if not self.base_url.endswith('/api'):
            self.base_url = f"{self.base_url}/api"
            
        print(f"API Client initialized with base URL: {self.base_url}")
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make an HTTP request to the API."""
        # Ensure endpoint doesn't start with a slash
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
            
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            # Log the request for debugging
            print(f"API request: {method} {url}")
            
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check for HTTP errors and handle them
            if response.status_code >= 400:
                print(f"API error: {response.status_code} - {response.text}")
                return {
                    'error': f"HTTP {response.status_code}: {response.text}",
                    'status_code': response.status_code
                }
            
            try:
                return response.json()
            except json.JSONDecodeError:
                print(f"API response is not valid JSON: {response.text}")
                return {
                    'error': 'Invalid JSON response',
                    'text': response.text
                }
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            print(f"API request error: {error_msg}")
            return {'error': error_msg}
    
    # Convenience methods
    def get(self, endpoint, params=None):
        """Convenience method for GET requests."""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint, data=None):
        """Convenience method for POST requests."""
        return self._make_request('POST', endpoint, data=data)
    
    def put(self, endpoint, data=None):
        """Convenience method for PUT requests."""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint):
        """Convenience method for DELETE requests."""
        return self._make_request('DELETE', endpoint)
    
    # Test connection
    def test_connection(self):
        """Test the connection to the API server."""
        return self._make_request('GET', 'health')  # Use the health endpoint
    
    # Authentication
    def login(self, username, password):
        """Login to the API."""
        try:
            response = self._make_request('POST', 'login', data={
                'username': username,
                'password': password
            })
            print(f"Login response: {response}")
            return response
        except Exception as e:
            print(f"Login error: {e}")
            return {'success': False, 'error': str(e)}
    
    # Patients
    def get_patients(self):
        """Get all patients."""
        return self._make_request('GET', 'patients')
    
    def get_patient(self, patient_id):
        """Get a specific patient."""
        return self._make_request('GET', f'patients/{patient_id}')
    
    def add_patient(self, patient_data):
        """Add a new patient."""
        return self._make_request('POST', 'patients', data=patient_data)
    
    def update_patient(self, patient_id, patient_data):
        """Update a patient."""
        return self._make_request('PUT', f'patients/{patient_id}', data=patient_data)
    
    def delete_patient(self, patient_id):
        """Delete a patient."""
        return self._make_request('DELETE', f'patients/{patient_id}')
    
    # Programs
    def get_programs(self, patient_id):
        """Get all programs for a patient."""
        return self._make_request('GET', 'programs', params={'patient_id': patient_id})
    
    def get_program(self, program_id):
        """Get a specific program."""
        return self._make_request('GET', f'programs/{program_id}')
    
    def add_program(self, program_data):
        """Add a new program."""
        return self._make_request('POST', 'programs', data=program_data)
    
    def update_program(self, program_id, program_data):
        """Update a program."""
        return self._make_request('PUT', f'programs/{program_id}', data=program_data)
    
    def delete_program(self, program_id):
        """Delete a program."""
        return self._make_request('DELETE', f'programs/{program_id}')
    
    # Shared patients
    def get_shared_patients(self, user_id):
        """Get patients shared with a user."""
        return self._make_request('GET', 'shared_patients', params={'user_id': user_id})
    
    # Tasks
    def add_task(self, task_data):
        """Add a new task."""
        return self._make_request('POST', 'tasks', data=task_data)
    
    def get_tasks(self, program_id):
        """Get all tasks for a program."""
        return self._make_request('GET', 'tasks', params={'program_id': program_id})
    
    # Users
    def get_user(self, user_id):
        """Get a user by ID."""
        return self._make_request('GET', f'users/{user_id}')
    
    def get_users(self):
        """Get all users."""
        return self._make_request('GET', 'users')
    
    # Shared Access
    def get_shared_access(self, patient_id):
        """Get all shared access records for a patient."""
        return self._make_request('GET', 'shared_access', params={'patient_id': patient_id})
        
    def add_shared_access(self, access_data):
        """Add a new shared access record."""
        return self._make_request('POST', 'shared_access', data=access_data)
    
    def update_shared_access(self, access_id, access_data):
        """Update a shared access record."""
        return self._make_request('PUT', f'shared_access/{access_id}', data=access_data)
        
    def remove_shared_access(self, access_id):
        """Remove a shared access record."""
        try:
            return self._make_request('DELETE', f'shared_access/{access_id}')
        except Exception as e:
            print(f"Error in API remove_shared_access: {e}")
            return {'error': str(e)}
    
    # Add methods for users, etc. as needed
