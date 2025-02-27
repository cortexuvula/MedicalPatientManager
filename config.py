import json
import os

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
