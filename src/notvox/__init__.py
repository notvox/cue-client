"""
NotVox - Network Spotify Control System
"""

__version__ = "0.1.0"
__author__ = "mfw"
__email__ = "espadonn@outlook.com"

# Make CLI accessible at package level
from .cli import cli

__all__ = ["cli"]