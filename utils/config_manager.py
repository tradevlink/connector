import json
import os
from typing import Any, Dict
import shutil

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.config_file = "config.json"
        self.example_config_file = "config.example.json"
        self._config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from config.json if it exists, otherwise create from example."""
        if not os.path.exists(self.config_file):
            self._create_config_from_example()
        
        try:
            with open(self.config_file, 'r') as f:
                content = f.read().strip()
                if not content:  # File exists but is empty
                    self._create_config_from_example()
                else:
                    try:
                        self._config = json.loads(content)
                    except json.JSONDecodeError:
                        print("Error reading config file. Creating from example.")
                        self._create_config_from_example()
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = {}
    
    def _create_config_from_example(self) -> None:
        """Create config.json from config.example.json."""
        try:
            if os.path.exists(self.example_config_file):
                shutil.copy2(self.example_config_file, self.config_file)
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
            else:
                print("Example config file not found. Using empty configuration.")
                self._config = {}
        except Exception as e:
            print(f"Error creating config from example: {e}")
            self._config = {}
    
    def save_config(self) -> None:
        """Save current configuration to config.json."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save to file."""
        self._config[key] = value
        self.save_config()
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update multiple configuration values at once."""
        self._config.update(config_dict)
        self.save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
    
    def delete(self, key: str) -> None:
        """Delete a configuration key if it exists."""
        if key in self._config:
            del self._config[key]
            self.save_config()
