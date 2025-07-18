# client/src/notvox/utils/constants.py
"""Shared constants for NotVox client"""

from pathlib import Path

# Configuration
DEFAULT_CONFIG = {"server_url": "http://localhost:8080", "timeout": 30}
CONFIG_FILE = Path.home() / ".notvoxrc"

# Defaults
DEFAULT_DURATION = "full"
DEFAULT_HISTORY_LIMIT = 20

# Display constants
MAX_TRACK_DISPLAY_LENGTH = 50

# Status formatting
STATUS_CONFIG = {
    "completed": ("green", "[OK]"),
    "stopped": ("yellow", "[STOP]"),
    "playing": ("cyan", "[PLAY]")
}

# Device type emojis
DEVICE_EMOJIS = {
    'Computer': '💻',
    'Smartphone': '📱',
    'Speaker': '🔊',
    'TV': '📺',
    'AVR': '🎚️',
    'CastVideo': '📺',
    'CastAudio': '🔊'
}