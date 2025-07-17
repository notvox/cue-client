#!/usr/bin/env python3
"""
NotVox CLI - Command line interface for NotVox server
"""

import os
import sys
import json
import click
import requests
from pathlib import Path
from datetime import datetime

# Default configuration
DEFAULT_CONFIG = {
    "server_url": "http://localhost:8080",
    "timeout": 30
}

CONFIG_FILE = Path.home() / ".notvoxrc"


class NotVoxClient:
    def __init__(self):
        self.config = self.load_config()
        self.server_url = self.config.get("server_url", DEFAULT_CONFIG["server_url"])
        self.timeout = self.config.get("timeout", DEFAULT_CONFIG["timeout"])
    
    def load_config(self):
        """Load configuration from file or create default"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                click.secho(f"Warning: Could not load config: {e}", fg='yellow')
        
        # Create default config
        self.save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    def save_config(self, config):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            click.secho(f"Error saving config: {e}", fg='red')
    
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request to server"""
        url = f"{self.server_url}{endpoint}"
        try:
            response = requests.request(
                method, url, 
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            click.secho("[ERROR] Could not connect to NotVox server", fg='red')
            click.echo(f"        Server URL: {self.server_url}")
            click.echo("        Is the server running?")
            sys.exit(1)
        except requests.exceptions.Timeout:
            click.secho("[ERROR] Request timed out", fg='red')
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                error_data = response.json()
                click.secho(f"[ERROR] {error_data.get('error', 'Not found')}", fg='red')
            else:
                click.secho(f"[ERROR] HTTP {response.status_code}: {e}", fg='red')
            sys.exit(1)
        except Exception as e:
            click.secho(f"[ERROR] {e}", fg='red')
            sys.exit(1)
    
    def play_track(self, query, duration, quiet=False):
        """Send play command to server"""
        if not quiet:
            click.echo(f"Searching for: {query}")
        
        data = {"query": query, "duration": duration}
        result = self.make_request('POST', '/play', json=data)
        
        if not quiet:
            click.secho(f"[OK] {result['message']}", fg='green')
            click.echo(f"     Duration: {result['duration']}")
            click.echo(f"     Ends at: {self._format_time(result['ends_at'])}")
        
        return result
    
    def stop_playback(self):
        """Stop current playback"""
        result = self.make_request('DELETE', '/stop')
        click.secho(f"[STOP] {result['message']}", fg='yellow')
        return result
    
    def get_status(self):
        """Get current playback status"""
        result = self.make_request('GET', '/status')
        
        if result['status'] == 'idle':
            click.echo("No active session")
        else:
            click.secho(f"[PLAYING] {result['track']}", fg='cyan')
            click.echo(f"          Started: {self._format_time(result['started_at'])}")
            click.echo(f"          Ends at: {self._format_time(result['ends_at'])}")
            click.echo(f"          Remaining: {result['time_remaining']}")
        
        return result
    
    def _format_time(self, iso_time):
        """Format ISO time string to human readable"""
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return dt.strftime("%I:%M %p")


# Create client instance
client = NotVoxClient()


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """NotVox - Network Spotify Control System"""
    pass


@cli.command()
@click.argument('query')
@click.argument('duration')
def cue(query, duration):
    """Play a track for specified duration
    
    Examples:
        notvox cue "Bohemian Rhapsody" 2h
        notvox cue "lofi beats" 30m
        notvox cue "white noise" 8h
    """
    client.play_track(query, duration)


@cli.command()
@click.argument('query')
@click.argument('duration')
def quietly(query, duration):
    """Play a track quietly (minimal output)
    
    Usage: notvox quietly cue "song" 1h
    """
    if query.lower() != 'cue':
        click.secho("Usage: notvox quietly cue <query> <duration>", fg='red')
        sys.exit(1)
    
    # The actual query is in duration, and duration is the next arg
    # This is a bit of a hack to support "quietly cue" syntax
    import sys
    if len(sys.argv) < 5:
        click.secho("Usage: notvox quietly cue <query> <duration>", fg='red')
        sys.exit(1)
    
    actual_query = duration
    actual_duration = sys.argv[4]
    client.play_track(actual_query, actual_duration, quiet=True)


@cli.command()
def stop():
    """Stop current playback"""
    client.stop_playback()


@cli.command()
def status():
    """Show current playback status"""
    client.get_status()


@cli.command()
@click.option('--url', help='NotVox server URL')
@click.option('--timeout', type=int, help='Request timeout in seconds')
def config(url, timeout):
    """Configure NotVox client settings"""
    current_config = client.config.copy()
    
    if url:
        current_config['server_url'] = url
        click.echo(f"Server URL set to: {url}")
    
    if timeout:
        current_config['timeout'] = timeout
        click.echo(f"Timeout set to: {timeout} seconds")
    
    if url or timeout:
        client.save_config(current_config)
        click.secho("[OK] Configuration saved", fg='green')
    else:
        # Show current config
        click.echo("Current configuration:")
        click.echo(f"  Server URL: {current_config['server_url']}")
        click.echo(f"  Timeout: {current_config['timeout']}s")
        click.echo(f"  Config file: {CONFIG_FILE}")


@cli.command()
def health():
    """Check server health"""
    try:
        result = client.make_request('GET', '/health')
        click.secho("[OK] Server is healthy", fg='green')
        click.echo(f"     Spotify connected: {'Yes' if result['spotify_connected'] else 'No'}")
        click.echo(f"     Server time: {client._format_time(result['timestamp'])}")
    except SystemExit:
        # Already handled by make_request
        pass


if __name__ == '__main__':
    cli()