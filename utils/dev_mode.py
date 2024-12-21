"""Module for managing development mode configuration."""

# Global development mode flag
_DEV_MODE = False

def set_dev_mode(enabled: bool):
    """Set the development mode flag."""
    global _DEV_MODE
    _DEV_MODE = enabled

def is_dev_mode() -> bool:
    """Check if development mode is enabled."""
    return _DEV_MODE
