# Medical Patient Manager

A Python application for managing multiple medical patients and their associated treatment programs using a Kanban-style interface.

## Features

- Add and manage multiple patients
- Create program categories for each patient (Diabetes Management, CKD Management, Pain Management, etc.)
- Kanban board interface for visualizing patient progress
- Task management within each program
- Data persistence for patient records

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```

## Usage

1. Add a new patient using the "Add Patient" button
2. Select a patient to view their programs
3. Add programs to a patient's profile
4. Use the Kanban board to track progress within each program

## Network Configuration

The Medical Patient Manager can be run in two modes:

1. **Local Mode**: The default mode, where the application uses a local SQLite database file.
2. **Remote Mode**: Connects to a server running on another computer to access the database remotely.

### Setting up the Server

To make the database accessible over the network:

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. On the computer that will act as the server:
   - Run the `run_server.bat` file or execute:
     ```
     python server.py --host 0.0.0.0 --port 5000
     ```
   - This will start a Flask server on port 5000 that exposes the database via a REST API
   - Make note of the server's IP address (you can find it by running `ipconfig` in a command prompt)

3. On client computers:
   - Launch the application
   - Click the "Configuration" button on the login screen
   - Select "Remote Mode"
   - Enter the server URL in the format: `http://<server_ip>:5000/` (replace `<server_ip>` with the actual IP address of the server)
   - Click Save and restart the application
   - Use the test credentials: username: `admin`, password: `admin123`

### Testing the Connection

The server provides a web interface for testing the connection:

1. On any computer with a web browser, navigate to `http://<server_ip>:5000/`
2. The page will show the server status and allow you to test the connection
3. You can use the test credentials (username: `admin`, password: `admin123`) to verify login works

### Troubleshooting Network Issues

If you're having trouble connecting to the server:

1. **Verify the server is running**:
   - Check that the server console shows `Running on http://0.0.0.0:5000/`
   - Navigate to `http://<server_ip>:5000/` in a web browser on the server computer

2. **Check URL format**:
   - Make sure you're using `http://<server_ip>:5000/` (with trailing slash)
   - The application will automatically add the `/api` prefix to API requests

3. **Test with utilities**:
   - Run `python test_api_connection.py` to check API connectivity
   - Run `python test_login.py` to test authentication

4. **Note about Remote Mode Limitations**:
   - When running in remote mode, audit logging is limited
   - Audit log events are logged to the console but not stored in a database
   - The Audit Log Viewer will not display logs from remote sessions
   - This is by design due to the distributed nature of the application in remote mode

5. **Check network connectivity**:
   - Ping the server from the client machine
   - Try telnet to the server on port 5000
   - Check if any VPN or proxy settings might be interfering

6. **Debug logs**:
   - Run the server with the `--debug` flag for more detailed logs:
     ```
     python server.py --host 0.0.0.0 --port 5000 --debug
     ```

### Firewall Configuration

You may need to configure your firewall to allow connections to port 5000 on the server computer:

1. Open Windows Defender Firewall with Advanced Security
2. Create a new Inbound Rule
3. Select "Port" and specify TCP port 5000
4. Allow the connection
5. Apply the rule to Domain, Private, and Public networks (or just the ones you need)
6. Name the rule (e.g., "Medical Patient Manager Server")

### Security Considerations

- The default server implementation does not use HTTPS. For production use, it's recommended to set up SSL/TLS.
- The server uses basic authentication with username/password. Consider implementing token-based authentication for better security.
- Only expose the server to trusted networks. Do not expose it directly to the internet without proper security measures.

## License

MIT
