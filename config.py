import os
import json

class Config:
    """Configuration manager for the Medical Patient Manager application."""
    
    DEFAULT_CONFIG = {
        "mode": "local",  # 'local' or 'remote'
        "remote_url": "http://localhost:5000/api",
        "db_file": "patient_manager.db",
        "kanban_columns": [
            {"id": "todo", "title": "To Do"},
            {"id": "in_progress", "title": "In Progress"},
            {"id": "done", "title": "Done"}
        ]
    }
    
    CONFIG_FILE = "config.json"
    
    @classmethod
    def load_config(cls):
        """Load configuration from file or create default if not exists."""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            else:
                cls.save_config(cls.DEFAULT_CONFIG)
                return cls.DEFAULT_CONFIG
        except Exception as e:
            print(f"Error loading config: {e}")
            return cls.DEFAULT_CONFIG
    
    @classmethod
    def save_config(cls, config):
        """Save configuration to file."""
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @classmethod
    def get_config(cls):
        """Get the current configuration."""
        return cls.load_config()
    
    @classmethod
    def update_config(cls, updates):
        """Update configuration with the provided values."""
        config = cls.load_config()
        config.update(updates)
        return cls.save_config(config)
    
    @classmethod
    def is_remote_mode(cls):
        """Check if the application is in remote mode."""
        config = cls.load_config()
        return config.get("mode") == "remote"
    
    @classmethod
    def get_remote_url(cls):
        """Get the remote API URL."""
        config = cls.load_config()
        return config.get("remote_url")
    
    @classmethod
    def get_db_file(cls):
        """Get the database file path."""
        config = cls.load_config()
        return config.get("db_file")
        
    @classmethod
    def save_remembered_credentials(cls, username, password):
        """Save remembered username and password for auto-login.
        
        Note: Password is stored with basic encryption - not secure for highly sensitive systems.
        """
        import base64
        config = cls.load_config()
        config["remembered_username"] = username
        
        # Basic encryption (not truly secure, but better than plaintext)
        if password:
            encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            config["remembered_password"] = encoded_password
        
        return cls.save_config(config)
    
    @classmethod
    def clear_remembered_credentials(cls):
        """Clear any remembered login credentials."""
        config = cls.load_config()
        if "remembered_username" in config:
            del config["remembered_username"]
        if "remembered_password" in config:
            del config["remembered_password"]
        return cls.save_config(config)
    
    @classmethod
    def get_remembered_credentials(cls):
        """Get the remembered username and password if any.
        
        Returns:
            tuple: (username, password) or ("", "") if none saved
        """
        import base64
        config = cls.load_config()
        username = config.get("remembered_username", "")
        encoded_password = config.get("remembered_password", "")
        
        password = ""
        if encoded_password:
            try:
                password = base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
            except:
                # If there's any error decoding, return empty password
                password = ""
                
        return (username, password)
