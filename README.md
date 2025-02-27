# Medical Patient Manager

A Python application for managing multiple medical patients and their associated treatment programs using a Kanban-style interface.

## Features

- **Patient Management**: Add, edit, and manage multiple patients
- **Program Categories**: Create customized program categories for each patient (Diabetes Management, CKD Management, Pain Management, etc.)
- **Kanban Interface**: Visualize patient progress through a Kanban board
- **Task Management**: Create and track tasks within each program
- **Data Persistence**: Choose between local or remote data storage
- **Configuration**: Simple UI for switching between local and remote modes
- **Multi-User Support**: When in remote mode, multiple users can access the system simultaneously
- **Customizable UI**: Personalize Kanban board with custom column titles and add up to 5 columns
- **Flexible Workflow**: Rearrange Kanban columns to match your workflow

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

## Configuration

The application can run in either local or remote mode:

1. **Local Mode**: Uses a local SQLite database for data storage (default)
2. **Remote Mode**: Uses a remote API server for data storage

To configure the application:

1. Copy `config.template.json` to `config.json`
2. Edit `config.json` to set your preferred configuration:
   ```json
   {
       "mode": "local",
       "remote_url": "http://your-api-server.com/api",
       "db_file": "patient_manager.db"
   }
   ```
3. You can also access configuration settings from the application's "File > Configuration" menu

## Usage

1. Add a new patient using the "Add Patient" button
2. Select a patient to view their programs
3. Add programs to a patient's profile
4. Use the Kanban board to track progress within each program
5. Customize Kanban columns by clicking the "Customize Columns" button:
   - Edit existing column titles
   - Add new columns (up to 5 total columns)
   - Remove columns (minimum 3 columns required)
   - Rearrange columns using the up/down arrows

## Server Setup

To make the database accessible over the network (remote mode):

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
   - Go to "File > Configuration" or click the "Configuration" button on the login screen
   - Select "Remote Mode"
   - Enter the server URL in the format: `http://<server_ip>:5000/api` (replace `<server_ip>` with the actual IP address of the server)
   - Click Save and restart the application when prompted
   - Use the default test credentials: username: `admin`, password: `admin123`

## Testing the Connection

The server provides a web interface for testing the connection:

1. On any computer with a web browser, navigate to `http://<server_ip>:5000/`
2. The page will show the server status and allow you to test the connection
3. You can use the test credentials (username: `admin`, password: `admin123`) to verify login works

## Troubleshooting

If you're having trouble connecting to the server:

1. **Verify the server is running**:
   - Check that the server console shows `Running on http://0.0.0.0:5000/`
   - Navigate to `http://<server_ip>:5000/` in a web browser on the server computer

2. **Check URL format**:
   - Make sure you're using the correct format: `http://<server_ip>:5000/api`
   - The trailing `/api` is required for the client application

3. **Firewall settings**:
   - Ensure that port 5000 is open on the server's firewall
   - For Windows: Control Panel > System and Security > Windows Defender Firewall > Advanced Settings > Inbound Rules

4. **Network connectivity**:
   - Verify that the client computer can reach the server by pinging it: `ping <server_ip>`
   - Check that both machines are on the same network or have proper routing between networks

## Security Considerations

- **Default Mode**: The application defaults to local mode for security. Remote mode should only be enabled when needed.
- **Network Security**: The default server implementation does not use HTTPS. For production use, set up SSL/TLS.
- **Authentication**: The server uses basic authentication. For higher security, implement token-based authentication.
- **Network Exposure**: Only expose the server to trusted networks. Never expose it directly to the internet without proper security measures.
- **Configuration Security**: The `config.json` file contains connection information and is excluded from version control for security reasons.

## License

MIT
