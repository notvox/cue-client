# client/src/notvox/__init__.py
"""
NotVox - Network Spotify Control System
"""

__version__ = "0.1.0"
__author__ = "mfw"
__email__ = "espadonn@outlook.com"

# Make CLI accessible at package level
from .cli import cli

__all__ = ["cli"]


# client/src/notvox/commands/__init__.py
"""NotVox command modules"""

# This can be empty - commands are imported directly in cli.py


# client/src/notvox/utils/__init__.py
"""NotVox utility modules"""

# This can be empty - utils are imported where needed