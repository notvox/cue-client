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
from datetime import datetime, timedelta

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
    
    def play_lucky(self, duration):
        """Play a random track from history or recommendations"""
        click.echo("Finding a lucky pick...")
        
        data = {"duration": duration}
        result = self.make_request('POST', '/lucky', json=data)
        
        source = result['source']
        if source == 'history-notvox':
            source_text = "(From your NotVox history)"
            source_color = 'cyan'
        elif source == 'history-spotify':
            source_text = "(From your Spotify history)"
            source_color = 'green'
        else:
            source_text = "(New recommendation based on your taste)"
            source_color = 'magenta'
        
        click.secho(f"[LUCKY] {result['message']}", fg=source_color)
        click.echo(f"        Duration: {result['duration']}")
        click.echo(f"        Ends at: {self._format_time(result['ends_at'])}")
        click.echo(f"        {source_text}")
        
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
    
    def get_history(self, limit=20, since=None):
        """Get playback history"""
        params = {'limit': limit}
        if since:
            params['since'] = since
        
        result = self.make_request('GET', '/history', params=params)
        return result
    
    def format_duration(self, seconds):
        """Format seconds to human readable duration"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h{minutes}m" if minutes else f"{hours}h"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d{hours}h" if hours else f"{days}d"
    
    def format_relative_time(self, iso_time):
        """Format ISO time to relative time (e.g., '2 hours ago')"""
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt
        
        if delta.total_seconds() < 60:
            return "just now"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")


# Create client instance
client = NotVoxClient()


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version='0.1.0', prog_name='NotVox')
def cli():
    """NotVox - Network Spotify Control System
    
    Control Spotify playback over the network with timed sessions.
    
    Common commands:
    
    \b
      notvox cue "song name" 2h      Play a song for 2 hours
      notvox status                   Check what's currently playing
      notvox stop                     Stop current playback
    
    \b
    Duration formats: 30m, 2h, 1d, 90s
    
    Use 'notvox COMMAND --help' for more information on a command.
    """
    pass


@cli.command()
@click.argument('query', metavar='SEARCH_QUERY')
@click.argument('duration', metavar='DURATION')
@click.option('--lucky', is_flag=True, help='Pick a random song from history or recommendations')
@click.option('--select', '-s', is_flag=True, help='Show search results and select one')
def cue(query, duration, lucky, select):
    """Play a track for specified duration
    
    \b
    Arguments:
      SEARCH_QUERY   Song, artist, or album to search for
      DURATION       How long to play (e.g., 30m, 2h, 1d, 90s)
    
    \b
    Examples:
      notvox cue "Bohemian Rhapsody" 2h
      notvox cue "lofi hip hop" 30m
      notvox cue --select "taylor swift" 45m   # Choose from results
      notvox cue --lucky 2h                    # Random from history
    
    \b
    Duration formats:
      30s  = 30 seconds
      45m  = 45 minutes  
      2h   = 2 hours
      1d   = 1 day
      90   = 90 minutes (no unit defaults to minutes)
    
    \b
    Options:
      --lucky    Pick random track from your history/recommendations
      --select   Show search results and choose one interactively
    """
    if lucky:
        # For lucky mode, duration is in the query position
        client.play_lucky(query)
    elif select:
        client.show_search_results(query, select_mode=True, duration=duration)
    else:
        client.play_track(query, duration)


@cli.group(name='quietly', invoke_without_command=False)
def quietly_group():
    """Run commands with minimal output
    
    Suppress non-essential output for use in scripts or cron jobs.
    
    \b
    Example:
      notvox quietly cue "white noise" 8h
    
    Only errors will be displayed when using quietly.
    """
    pass


@quietly_group.command(name='cue')
@click.argument('query', metavar='SEARCH_QUERY')
@click.argument('duration', metavar='DURATION')
def quietly_cue(query, duration):
    """Play a track quietly (minimal output)
    
    Same as 'notvox cue' but suppresses all output except errors.
    Perfect for scripts, cron jobs, or background automation.
    
    \b
    Arguments:
      SEARCH_QUERY   Song, artist, or album to search for
      DURATION       How long to play (e.g., 30m, 2h, 1d)
    
    \b
    Example:
      notvox quietly cue "rain sounds" 8h
    """
    client.play_track(query, duration, quiet=True)


@cli.command()
def stop():
    """Stop current playback immediately
    
    Stops whatever is currently playing and cancels any remaining time.
    
    \b
    Example:
      notvox stop
    """
    client.stop_playback()


@cli.command()
def status():
    """Show current playback status
    
    Displays information about the currently playing track including
    time remaining and when it will end.
    
    \b
    Example:
      notvox status
    
    \b
    Output includes:
      - Currently playing track
      - Start and end times
      - Time remaining
    """
    client.get_status()


@cli.command()
@click.option('--url', metavar='URL', help='NotVox server URL (e.g., http://192.168.1.100:8080)')
@click.option('--timeout', metavar='SECONDS', type=int, help='Request timeout in seconds (default: 30)')
def config(url, timeout):
    """Configure NotVox client settings
    
    View or modify the NotVox client configuration. Settings are saved
    to ~/.notvoxrc and persist between sessions.
    
    \b
    Examples:
      notvox config                         Show current configuration
      notvox config --url http://pi:8080    Set server URL
      notvox config --timeout 60            Set 60 second timeout
    
    \b
    Configuration file location: ~/.notvoxrc
    """
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
@click.option('--limit', '-n', default=20, help='Number of sessions to show')
@click.option('--today', is_flag=True, help='Show only today\'s sessions')
@click.option('--this-week', is_flag=True, help='Show only this week\'s sessions')
@click.option('--combined', '-c', is_flag=True, help='Show combined NotVox + Spotify history')
def history(limit, today, this_week, combined):
    """Show playback history
    
    Display recent playback sessions with duration, status, and play counts.
    
    \b
    Examples:
      notvox history              Show last 20 NotVox sessions
      notvox history --combined   Show NotVox + Spotify history
      notvox history --today      Show today's sessions only
      notvox history --limit 5    Show last 5 sessions
    
    \b
    Status indicators:
      [OK]   - Completed full duration
      [STOP] - Stopped manually
      [PLAY] - Currently playing
    
    Combined mode shows your Spotify listening history alongside NotVox
    sessions to give a complete picture of your music habits.
    """
    if combined:
        client.show_combined_history(limit=limit)
    else:
        client.show_history(limit=limit, today_only=today, this_week=this_week)


@cli.command()
@click.argument('duration', metavar='DURATION')
def lucky(duration):
    """Play a random track based on your taste
    
    Picks a track from your listening history (70% chance) or
    discovers something new based on your preferences (30% chance).
    
    \b
    Arguments:
      DURATION    How long to play (e.g., 30m, 2h, 1d)
    
    \b
    Examples:
      notvox lucky 2h      # Random 2-hour session
      notvox lucky 30m     # Quick random pick
    
    Songs played in the last 24 hours are excluded to avoid repetition.
    """
    client.play_lucky(duration)


@cli.command()
@click.argument('query', metavar='SEARCH_QUERY')
def search(query):
    """Search for tracks without playing
    
    Display search results with track details and popularity ratings.
    
    \b
    Arguments:
      SEARCH_QUERY   Song, artist, or album to search for
    
    \b
    Examples:
      notvox search "taylor swift"
      notvox search "jazz piano"
    
    \b
    Popularity indicators:
      [***] Very popular (80+)
      [** ] Popular (60-79)
      [*  ] Moderate (40-59)
      [   ] Lesser known (<40)
    """
    client.show_search_results(query, select_mode=False)


@cli.command()
@click.argument('duration', metavar='DURATION')
def extend(duration):
    """Extend or reduce current playback session
    
    Add or subtract time from the currently playing track.
    Use negative durations to reduce time.
    
    \b
    Arguments:
      DURATION    Time to add/subtract (e.g., 30m, -10m, 1h)
    
    \b
    Examples:
      notvox extend 30m     # Add 30 minutes
      notvox extend -10m    # Reduce by 10 minutes
      notvox extend 1h      # Add 1 hour
    """
    client.extend_session(duration)


@cli.command()
@click.option('--duration', '-d', metavar='DURATION', help='Override original duration')
@click.option('--select', '-s', is_flag=True, help='Choose from recent stopped sessions')
def resume(duration, select):
    """Resume a previously stopped session
    
    Resume the last stopped session or choose from recent ones.
    
    \b
    Examples:
      notvox resume                    # Resume last stopped session
      notvox resume --duration 1h      # Resume with new duration
      notvox resume --select           # Choose which session to resume
    
    By default, resumes with the original duration unless overridden.
    """
    client.resume_session(duration=duration, select=select)


@cli.command()
def health():
    """Check server health and connection
    
    Tests the connection to the NotVox server and displays its status,
    including whether Spotify is properly authenticated.
    
    \b
    Example:
      notvox health
    
    \b
    Shows:
      - Server connectivity status
      - Spotify authentication status
      - Server timestamp
    """
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