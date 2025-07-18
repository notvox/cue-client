# client/src/notvox/client.py
"""NotVox Client - handles server communication"""

import json
import sys
from typing import Optional, Dict, Any

import click
import requests

from .utils.constants import DEFAULT_CONFIG, CONFIG_FILE, DEFAULT_DURATION
from .utils.formatting import format_time, format_duration, format_relative_time


class NotVoxClient:
    """Client for communicating with NotVox server"""
    
    def __init__(self):
        self.config = self.load_config()
        self.server_url = self.config.get("server_url", DEFAULT_CONFIG["server_url"])
        self.timeout = self.config.get("timeout", DEFAULT_CONFIG["timeout"])

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                click.secho(f"Warning: Could not load config: {e}", fg="yellow")

        # Create default config
        self.save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            click.secho(f"Error saving config: {e}", fg="red")

    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to server"""
        url = f"{self.server_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            click.secho("[ERROR] Could not connect to NotVox server", fg="red")
            click.echo(f"        Server URL: {self.server_url}")
            click.echo("        Is the server running?")
            sys.exit(1)
        except requests.exceptions.Timeout:
            click.secho("[ERROR] Request timed out", fg="red")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                error_data = response.json()
                click.secho(f"[ERROR] {error_data.get('error', 'Not found')}", fg="red")
            else:
                click.secho(f"[ERROR] HTTP {response.status_code}: {e}", fg="red")
            sys.exit(1)
        except Exception as e:
            click.secho(f"[ERROR] {e}", fg="red")
            sys.exit(1)

    # Core playback methods
    def play_track(self, query: str, duration: Optional[str] = None, quiet: bool = False) -> Dict[str, Any]:
        """Send play command to server"""
        if not quiet:
            click.echo(f"Searching for: {query}")

        if duration is None:
            duration = DEFAULT_DURATION

        data = {"query": query, "duration": duration}
        result = self.make_request("POST", "/play", json=data)

        if not quiet:
            click.secho(f"[OK] {result['message']}", fg="green")
            if duration != "full":
                click.echo(f"     Duration: {result['duration']}")
            click.echo(f"     Ends at: {format_time(result['ends_at'])}")

        return result

    def play_lucky(self, duration: Optional[str] = None) -> Dict[str, Any]:
        """Play a random track from history or recommendations"""
        click.echo("Finding a lucky pick...")

        if duration is None:
            duration = DEFAULT_DURATION

        data = {"duration": duration}
        result = self.make_request("POST", "/lucky", json=data)

        source = result["source"]
        source_colors = {
            "history-notvox": ("cyan", "(From your NotVox history)"),
            "history-spotify": ("green", "(From your Spotify history)"),
        }
        color, text = source_colors.get(source, ("magenta", "(New recommendation based on your taste)"))

        click.secho(f"[LUCKY] {result['message']}", fg=color)
        if duration != "full":
            click.echo(f"        Duration: {result['duration']}")
        click.echo(f"        Ends at: {format_time(result['ends_at'])}")
        click.echo(f"        {text}")

        return result

    def stop_playback(self) -> Dict[str, Any]:
        """Stop current playback"""
        result = self.make_request("DELETE", "/stop")
        click.secho(f"[STOP] {result['message']}", fg="yellow")
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        result = self.make_request("GET", "/status")

        if result["status"] == "idle":
            click.echo("No active session")
        else:
            click.secho(f"[PLAYING] {result['track']}", fg="cyan")
            click.echo(f"          Started: {format_time(result['started_at'])}")
            click.echo(f"          Ends at: {format_time(result['ends_at'])}")
            click.echo(f"          Remaining: {result['time_remaining']}")

        return result

    def extend_session(self, duration_str: str) -> Dict[str, Any]:
        """Extend or reduce current session"""
        data = {"duration": duration_str}
        result = self.make_request("POST", "/extend", json=data)

        action = "extended" if not duration_str.startswith("-") else "reduced"
        click.secho(f"[OK] Session {action} by {duration_str}", fg="green")
        click.echo(f"     New end time: {format_time(result['new_end_time'])}")

        return result

    def skip_track(self) -> Dict[str, Any]:
        """Skip current track"""
        result = self.make_request("POST", "/skip")
        click.secho(f"[SKIP] {result['message']}", fg="yellow")
        return result

    # Search methods
    def search_tracks(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for tracks"""
        params = {"q": query, "limit": limit}
        result = self.make_request("GET", "/search", params=params)
        return result

    def play_track_uri(self, uri: str, name: str, duration: Optional[str] = None) -> Dict[str, Any]:
        """Play a specific track by URI"""
        if duration is None:
            duration = DEFAULT_DURATION
            
        data = {"uri": uri, "name": name, "duration": duration}
        result = self.make_request("POST", "/play-uri", json=data)

        click.secho(f"[OK] {result['message']}", fg="green")
        if duration != "full":
            click.echo(f"     Duration: {result['duration']}")
        click.echo(f"     Ends at: {format_time(result['ends_at'])}")

        return result

    # History methods
    def get_history(self, limit: int = 20, since: Optional[str] = None) -> Dict[str, Any]:
        """Get playback history"""
        params = {"limit": limit}
        if since:
            params["since"] = since

        result = self.make_request("GET", "/history", params=params)
        return result

    def get_spotify_history(self) -> Dict[str, Any]:
        """Get recently played from Spotify"""
        result = self.make_request("GET", "/spotify-history")
        return result

    # Queue methods
    def add_to_queue(self, query: str, duration: Optional[str] = None) -> Dict[str, Any]:
        """Add track to queue"""
        if duration is None:
            duration = DEFAULT_DURATION
            
        data = {"query": query, "duration": duration}
        result = self.make_request("POST", "/queue/add", json=data)

        if result.get("position") == 1 and "started playing" in result.get("message", ""):
            click.secho(f"[OK] {result['message']}", fg="green")
        else:
            click.secho(f"[QUEUED] {result['message']}", fg="cyan")
            click.echo(f"         Position in queue: #{result['position']}")
            if duration != "full":
                click.echo(f"         Duration: {result['duration']}")

        return result

    def get_queue(self) -> Dict[str, Any]:
        """Get current queue"""
        result = self.make_request("GET", "/queue")
        return result

    def remove_from_queue(self, queue_id: int) -> Dict[str, Any]:
        """Remove item from queue"""
        result = self.make_request("DELETE", f'/queue/{queue_id}')
        return result

    def clear_queue(self) -> Dict[str, Any]:
        """Clear entire queue"""
        result = self.make_request("DELETE", "/queue/clear")
        click.secho(f"[OK] {result['message']}", fg="green")
        return result

    # Session methods
    def resume_session(self, session_id: Optional[int] = None, duration: Optional[str] = None) -> Dict[str, Any]:
        """Resume a session"""
        data = {}
        if session_id:
            data["session_id"] = session_id
        if duration:
            data["duration"] = duration

        result = self.make_request("POST", "/resume", json=data)
        click.secho(f"[OK] {result['message']}", fg="green")
        click.echo(f"     Duration: {result['duration']}")
        click.echo(f"     Ends at: {format_time(result['ends_at'])}")
        return result

    # Mode methods
    def get_modes(self) -> Dict[str, Any]:
        """Get all available modes"""
        return self.make_request("GET", "/modes")

    def get_mode(self, mode_name: str) -> Dict[str, Any]:
        """Get specific mode configuration"""
        return self.make_request("GET", f"/mode/{mode_name}")

    def get_current_mode(self) -> Dict[str, Any]:
        """Get current active mode"""
        return self.make_request("GET", "/mode/current")

    def start_mode(self, mode_name: str, duration: Optional[str] = None, volume: Optional[int] = None) -> Dict[str, Any]:
        """Start a specific mode"""
        data = {"mode": mode_name}
        if duration:
            data["duration"] = duration
        if volume:
            data["volume"] = volume

        result = self.make_request("POST", "/mode/start", json=data)

        click.secho(f"[MODE] {result['message']}", fg="green")
        if "track" in result:
            click.echo(f"       Now playing: {result['track']}")
        click.echo(f"       Duration: {result['duration']}")
        click.echo(f"       Ends at: {format_time(result['ends_at'])}")

        return result

    def stop_mode(self) -> Dict[str, Any]:
        """Stop current mode and playback"""
        result = self.make_request("POST", "/mode/stop")
        click.secho(f"[STOP] {result['message']}", fg="yellow")
        return result

    def create_mode(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new custom mode"""
        data = {"name": name, "config": config}
        result = self.make_request("POST", "/mode/create", json=data)

        click.secho(f"[OK] Created mode '{name}'", fg="green")
        click.echo(f"     Description: {config['description']}")
        click.echo(f"     Duration: {config['duration']}")
        click.echo(f"     Volume: {config['volume']}")

        return result

    def update_mode(self, mode_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing mode"""
        data = {"updates": updates}
        result = self.make_request("PUT", f"/mode/{mode_name}", json=data)
        click.secho(f"[OK] Updated mode '{mode_name}'", fg="green")
        return result

    def delete_mode(self, mode_name: str) -> Dict[str, Any]:
        """Delete a custom mode"""
        result = self.make_request("DELETE", f"/mode/{mode_name}")
        click.secho(f"[OK] {result['message']}", fg="green")
        return result

    # Volume & Device methods
    def get_volume(self) -> Dict[str, Any]:
        """Get current volume"""
        return self.make_request("GET", "/volume")

    def set_volume(self, volume: str) -> Dict[str, Any]:
        """Set volume"""
        data = {"volume": volume}
        result = self.make_request("POST", "/volume", json=data)
        click.secho(f"[OK] Volume set to {result['volume']}%", fg="green")
        return result

    def get_devices(self) -> Dict[str, Any]:
        """Get available Spotify devices"""
        return self.make_request("GET", "/devices")

    def transfer_device(self, device_name: str) -> Dict[str, Any]:
        """Transfer playback to a specific device"""
        data = {"device": device_name}
        result = self.make_request("POST", "/device/transfer", json=data)

        device = result.get("device", {})
        click.secho(f"[OK] {result['message']}", fg="green")
        if device.get("type"):
            click.echo(f"     Device type: {device.get('type', 'Unknown')}")
            click.echo(f"     Volume: {device.get('volume', 0)}%")

        return result

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        return self.make_request("GET", "/health")


# Global client instance
client = NotVoxClient()