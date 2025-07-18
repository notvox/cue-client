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
from .modes import ModeManager

# Default configuration
DEFAULT_CONFIG = {"server_url": "http://localhost:8080", "timeout": 30}
CONFIG_FILE = Path.home() / ".notvoxrc"

# Default duration when none specified
DEFAULT_DURATION = "full"


class NotVoxClient:
    def __init__(self):
        self.config = self.load_config()
        self.server_url = self.config.get("server_url", DEFAULT_CONFIG["server_url"])
        self.timeout = self.config.get("timeout", DEFAULT_CONFIG["timeout"])

    def load_config(self):
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

    def save_config(self, config):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            click.secho(f"Error saving config: {e}", fg="red")

    def make_request(self, method, endpoint, **kwargs):
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

    def play_track(self, query, duration=None, quiet=False):
        """Send play command to server"""
        if not quiet:
            click.echo(f"Searching for: {query}")

        # Use default duration if not specified
        if duration is None:
            duration = DEFAULT_DURATION

        data = {"query": query, "duration": duration}
        result = self.make_request("POST", "/play", json=data)

        if not quiet:
            click.secho(f"[OK] {result['message']}", fg="green")
            if duration != "full":
                click.echo(f"     Duration: {result['duration']}")
            click.echo(f"     Ends at: {self._format_time(result['ends_at'])}")

        return result

    def play_lucky(self, duration=None):
        """Play a random track from history or recommendations"""
        click.echo("Finding a lucky pick...")

        # Use default duration if not specified
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
        click.echo(f"        Ends at: {self._format_time(result['ends_at'])}")
        click.echo(f"        {text}")

        return result

    def stop_playback(self):
        """Stop current playback"""
        result = self.make_request("DELETE", "/stop")
        click.secho(f"[STOP] {result['message']}", fg="yellow")
        return result

    def get_status(self):
        """Get current playback status"""
        result = self.make_request("GET", "/status")

        if result["status"] == "idle":
            click.echo("No active session")
        else:
            click.secho(f"[PLAYING] {result['track']}", fg="cyan")
            click.echo(f"          Started: {self._format_time(result['started_at'])}")
            click.echo(f"          Ends at: {self._format_time(result['ends_at'])}")
            click.echo(f"          Remaining: {result['time_remaining']}")

        return result

    def _format_time(self, iso_time):
        """Format ISO time string to human readable"""
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return dt.strftime("%I:%M %p")

    def get_history(self, limit=20, since=None):
        """Get playback history"""
        params = {"limit": limit}
        if since:
            params["since"] = since

        result = self.make_request("GET", "/history", params=params)
        return result

    def show_history(self, limit=20, today_only=False, this_week=False):
        """Display playback history"""
        since = None
        if today_only:
            since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif this_week:
            since = (datetime.now() - timedelta(days=7)).isoformat()

        history = self.get_history(limit=limit, since=since)
        sessions = history.get("sessions", [])

        if not sessions:
            click.echo("No playback history found.")
            return

        click.echo("Recent playback sessions:\n")

        # Status formatting config
        status_config = {
            "completed": ("green", "[OK]"),
            "stopped": ("yellow", "[STOP]"),
            "playing": ("cyan", "[PLAY]")
        }

        for i, session in enumerate(sessions, 1):
            # Format track name
            track = session["track_name"]
            if len(track) > 50:
                track = track[:47] + "..."

            # Format duration
            duration = self.format_duration(session["duration_seconds"])

            # Format time
            relative_time = self.format_relative_time(session["start_time"])

            # Format status
            status = session["status"]
            status_color, status_symbol = status_config.get(status, ("cyan", "[PLAY]"))

            # Play count
            play_count = session.get("play_count", 1)
            play_indicator = f"(played {play_count}x)" if play_count > 1 else ""

            # Display entry
            click.echo(f"[{i}] {track} - {duration}")
            click.echo(f"    Started: {relative_time} {play_indicator}")
            click.secho(f"    Status: {status_symbol} {status}", fg=status_color)
            click.echo()

    def format_duration(self, seconds):
        """Format seconds to human readable duration"""
        intervals = [
            (86400, 'd', 'days'),
            (3600, 'h', 'hours'),
            (60, 'm', 'minutes'),
            (1, 's', 'seconds')
        ]
        
        for divisor, suffix, _ in intervals:
            if seconds >= divisor:
                value = seconds // divisor
                remainder = seconds % divisor
                
                # For days and hours, show the next unit if there's a remainder
                if suffix in ['d', 'h'] and remainder >= intervals[intervals.index((divisor, suffix, _)) + 1][0]:
                    next_value = remainder // intervals[intervals.index((divisor, suffix, _)) + 1][0]
                    next_suffix = intervals[intervals.index((divisor, suffix, _)) + 1][1]
                    return f"{value}{suffix}{next_value}{next_suffix}"
                else:
                    return f"{value}{suffix}"
        
        return "0s"

    def format_relative_time(self, iso_time):
        """Format ISO time to relative time (e.g., '2 hours ago')"""
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt

        seconds = delta.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return dt.strftime("%b %d, %Y")

    def extend_session(self, duration_str):
        """Extend or reduce current session"""
        data = {"duration": duration_str}
        result = self.make_request("POST", "/extend", json=data)

        action = "extended" if not duration_str.startswith("-") else "reduced"
        click.secho(f"[OK] Session {action} by {duration_str}", fg="green")
        click.echo(f"     New end time: {self._format_time(result['new_end_time'])}")

        return result

    def search_tracks(self, query, limit=5):
        """Search for tracks"""
        params = {"q": query, "limit": limit}
        result = self.make_request("GET", "/search", params=params)
        return result

    def play_track_uri(self, uri, name, duration=None):
        """Play a specific track by URI"""
        if duration is None:
            duration = DEFAULT_DURATION
            
        data = {"uri": uri, "name": name, "duration": duration}
        result = self.make_request("POST", "/play-uri", json=data)

        click.secho(f"[OK] {result['message']}", fg="green")
        if duration != "full":
            click.echo(f"     Duration: {result['duration']}")
        click.echo(f"     Ends at: {self._format_time(result['ends_at'])}")

        return result

    def show_search_results(self, query, select_mode=False, duration=None):
        """Display search results, optionally allow selection"""
        results = self.search_tracks(query, limit=10 if select_mode else 5)
        tracks = results.get("tracks", [])

        if not tracks:
            click.secho(f"[ERROR] No tracks found for '{query}'", fg="red")
            return None

        click.echo(f"\nSearch results for: {query}\n")

        for i, track in enumerate(tracks, 1):
            # Format duration from milliseconds
            duration_min = track["duration_ms"] // 60000
            duration_sec = (track["duration_ms"] % 60000) // 1000
            track_duration = f"{duration_min}:{duration_sec:02d}"

            # Popularity indicator
            pop = track["popularity"]
            pop_indicator = "[***]" if pop >= 80 else "[** ]" if pop >= 60 else "[*  ]" if pop >= 40 else "[   ]"

            click.echo(f"[{i}] {track['name']} - {track['artist']}")
            click.echo(f"    Album: {track['album']} ({track_duration}) {pop_indicator}")
            click.echo()

        if select_mode:
            # Interactive selection
            while True:
                try:
                    choice = click.prompt("\nSelect track number (or 0 to cancel)", type=int)
                    if choice == 0:
                        click.echo("Cancelled.")
                        return None
                    elif 1 <= choice <= len(tracks):
                        selected = tracks[choice - 1]
                        track_name = f"{selected['name']} by {selected['artist']}"
                        self.play_track_uri(selected["uri"], track_name, duration)
                        return selected
                    else:
                        click.secho(f"Please enter a number between 1 and {len(tracks)}", fg="yellow")
                except (ValueError, EOFError, KeyboardInterrupt):
                    click.echo("\nCancelled.")
                    return None

        return tracks

    def resume_session(self, duration=None, select=False):
        """Resume a previous session"""
        if select:
            # Show recent stopped sessions to choose from
            history = self.get_history(limit=10)
            stopped_sessions = [s for s in history.get("sessions", []) if s["status"] == "stopped"]

            if not stopped_sessions:
                click.secho("[ERROR] No stopped sessions to resume", fg="red")
                return None

            click.echo("Recent stopped sessions:\n")
            for i, session in enumerate(stopped_sessions[:5], 1):
                track = session["track_name"]
                if len(track) > 50:
                    track = track[:47] + "..."
                relative_time = self.format_relative_time(session["start_time"])
                original_duration = self.format_duration(session["duration_seconds"])

                click.echo(f"[{i}] {track}")
                click.echo(f"    Stopped: {relative_time} (was {original_duration})")
                click.echo()

            while True:
                try:
                    choice = click.prompt("\nSelect session to resume (or 0 to cancel)", type=int)
                    if choice == 0:
                        click.echo("Cancelled.")
                        return None
                    elif 1 <= choice <= len(stopped_sessions):
                        selected = stopped_sessions[choice - 1]
                        data = {"session_id": selected["id"]}
                        if duration:
                            data["duration"] = duration

                        result = self.make_request("POST", "/resume", json=data)
                        click.secho(f"[OK] {result['message']}", fg="green")
                        click.echo(f"     Duration: {result['duration']}")
                        click.echo(f"     Ends at: {self._format_time(result['ends_at'])}")
                        return result
                    else:
                        click.secho(f"Please enter a number between 1 and {len(stopped_sessions)}", fg="yellow")
                except (ValueError, EOFError, KeyboardInterrupt):
                    click.echo("\nCancelled.")
                    return None
        else:
            # Resume last stopped session
            data = {}
            if duration:
                data["duration"] = duration

            result = self.make_request("POST", "/resume", json=data)
            click.secho(f"[OK] {result['message']}", fg="green")
            click.echo(f"     Duration: {result['duration']}")
            click.echo(f"     Ends at: {self._format_time(result['ends_at'])}")
            return result

    def get_spotify_history(self):
        """Get recently played from Spotify"""
        result = self.make_request("GET", "/spotify-history")
        return result

    def show_combined_history(self, limit=20):
        """Show combined NotVox and Spotify history"""
        # Get NotVox history
        notvox_history = self.get_history(limit=limit)
        notvox_sessions = notvox_history.get("sessions", [])

        # Get Spotify history
        try:
            spotify_history = self.get_spotify_history()
            spotify_tracks = spotify_history.get("tracks", [])
        except:
            spotify_tracks = []

        click.echo("Combined playback history:\n")

        # Show recent NotVox sessions
        if notvox_sessions:
            click.secho("[NotVox History]", fg="cyan", bold=True)
            for i, session in enumerate(notvox_sessions[:10], 1):
                track = session["track_name"]
                if len(track) > 50:
                    track = track[:47] + "..."

                duration = self.format_duration(session["duration_seconds"])
                relative_time = self.format_relative_time(session["start_time"])
                play_count = session.get("play_count", 1)

                click.echo(f"{i:2d}. {track} - {duration}")
                play_indicator = f"(played {play_count}x)" if play_count > 1 else ""
                click.echo(f"    {relative_time} {play_indicator}")

        # Show Spotify history
        if spotify_tracks:
            click.echo()
            click.secho("[Spotify History]", fg="green", bold=True)
            for i, track in enumerate(spotify_tracks[:10], 1):
                name = f"{track['name']} - {track['artist']}"
                if len(name) > 50:
                    name = name[:47] + "..."

                play_count = track.get("spotify_play_count", 1)
                relative_time = self.format_relative_time(track["played_at"])

                click.echo(f"{i:2d}. {name}")
                play_indicator = f"(played {play_count}x recently)" if play_count > 1 else ""
                click.echo(f"    {relative_time} {play_indicator}")

        if not notvox_sessions and not spotify_tracks:
            click.echo("No playback history found.")
        else:
            click.echo()
            click.echo("Lucky mode uses this combined history to pick tracks you'll enjoy!")

    def add_to_queue(self, query, duration=None):
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

    def get_queue(self):
        """Get current queue"""
        result = self.make_request("GET", "/queue")
        return result

    def show_queue(self):
        """Display current queue"""
        queue_data = self.get_queue()
        queue_items = queue_data.get("queue", [])

        if not queue_items:
            click.echo("Queue is empty.")
            return

        click.echo("Current queue:\n")

        total_seconds = 0
        for i, item in enumerate(queue_items, 1):
            track = item["track_name"]
            if len(track) > 50:
                track = track[:47] + "..."

            duration = self.format_duration(item["duration_seconds"])
            total_seconds += item["duration_seconds"]

            click.echo(f"[{i}] {track} - {duration}")

        click.echo(f"\nTotal queue time: {self.format_duration(total_seconds)}")

        if queue_data.get("currently_playing_from_queue"):
            click.echo("\n(Currently playing track is from queue)")

    def remove_from_queue(self, position):
        """Remove item from queue by position"""
        # First get the queue to find the ID
        queue_data = self.get_queue()
        queue_items = queue_data.get("queue", [])

        if position < 1 or position > len(queue_items):
            click.secho(f"[ERROR] Invalid position. Queue has {len(queue_items)} items.", fg="red")
            return None

        item = queue_items[position - 1]
        result = self.make_request("DELETE", f'/queue/{item["id"]}')

        click.secho(f"[OK] Removed '{item['track_name']}' from queue", fg="green")
        return result

    def clear_queue(self):
        """Clear entire queue"""
        result = self.make_request("DELETE", "/queue/clear")
        click.secho(f"[OK] {result['message']}", fg="green")
        return result

    def skip_track(self):
        """Skip current track"""
        result = self.make_request("POST", "/skip")
        click.secho(f"[SKIP] {result['message']}", fg="yellow")
        return result


# Create client instance
client = NotVoxClient()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="0.1.0", prog_name="NotVox")
def cli():
    """NotVox - Network Spotify Control System

    Control Spotify playback over the network with timed sessions.

    Common commands:

    \b
      notvox cue "song name"         Play a song (full track)
      notvox cue "song name" 2h      Play a song for 2 hours
      notvox queue add "song"        Add to queue (full track)
      notvox status                  Check what's currently playing
      notvox skip                    Skip to next in queue
      notvox stop                    Stop current playback

    \b
    Duration formats: 30m, 2h, 1d, 90s, full (default)

    Use 'notvox COMMAND --help' for more information on a command.
    """
    pass


# HACKY FIX: Create a custom group that doesn't consume arguments
class CueGroup(click.Group):
    """Custom group for cue command that handles arguments properly"""
    
    def invoke(self, ctx):
        # If we have a subcommand, let it handle everything
        if ctx.invoked_subcommand:
            return super().invoke(ctx)
        
        # Otherwise, handle direct cue command
        args = ctx.args
        if len(args) >= 1:
            query = args[0]
            duration = args[1] if len(args) >= 2 else None
            
            # Check for flags
            if '--lucky' in args or ctx.params.get('lucky'):
                client.play_lucky(duration)
            elif '--select' in args or '-s' in args or ctx.params.get('select'):
                client.show_search_results(query, select_mode=True, duration=duration)
            else:
                client.play_track(query, duration)
        else:
            click.echo(self.get_help(ctx))


@cli.group(name='cue', cls=CueGroup, invoke_without_command=True, 
           context_settings={'ignore_unknown_options': True, 'allow_extra_args': True})
@click.option('--lucky', is_flag=True, help='Pick a random song')
@click.option('--select', '-s', is_flag=True, help='Select from results')
@click.pass_context
def cue_group(ctx, lucky, select):
    """Play music for a specified duration

    Quick usage:
      notvox cue "song name"           # Play full track
      notvox cue "song name" 2h        # Play for 2 hours

    Or use subcommands for specific content types:
      notvox cue playlist "Chill Vibes"      # Play full playlist
      notvox cue album "Dark Side of the Moon" 45m
      notvox cue artist "Bon Iver"           # Play all top tracks
      notvox cue radio "Clair de Lune" 2h
      notvox cue genre jazz                  # Continuous jazz
    """
    # Context is handled by the custom group class
    pass


@cue_group.command(name='track')
@click.argument('track_name')
@click.argument('duration', required=False)
@click.option('--select', '-s', is_flag=True, help='Select from results')
def cue_track(track_name, duration, select):
    """Play a specific track"""
    if select:
        client.show_search_results(track_name, select_mode=True, duration=duration)
    else:
        client.play_track(track_name, duration)


@cue_group.command(name='playlist')
@click.argument('playlist_name')
@click.argument('duration', required=False)
def cue_playlist(playlist_name, duration):
    """Play a playlist"""
    query = f"playlist:{playlist_name}"
    client.play_track(query, duration)


@cue_group.command(name='album')
@click.argument('album_name')
@click.argument('duration', required=False)
def cue_album(album_name, duration):
    """Play an album"""
    query = f"album:{album_name}"
    client.play_track(query, duration)


@cue_group.command(name='artist')
@click.argument('artist_name')
@click.argument('duration', required=False)
def cue_artist(artist_name, duration):
    """Play an artist's top tracks"""
    query = f"artist:{artist_name}"
    client.play_track(query, duration)


@cue_group.command(name='radio')
@click.argument('seed_song')
@click.argument('duration', required=False)
def cue_radio(seed_song, duration):
    """Create a radio station based on a song"""
    query = f"radio:{seed_song}"
    client.play_track(query, duration)


@cue_group.command(name='genre')
@click.argument('genre_name')
@click.argument('duration', required=False)
def cue_genre(genre_name, duration):
    """Play music by genre"""
    query = f"genre:{genre_name}"
    client.play_track(query, duration)


# Keep the standalone shortcuts for convenience
@cli.command()
@click.argument('genre_name')
@click.argument('duration', required=False, default='1h')
def genre(genre_name, duration):
    """Quick play music by genre (shortcut for 'cue genre')"""
    query = f"genre:{genre_name}"
    client.play_track(query, duration)


@cli.command()
@click.argument('song_name')
@click.argument('duration', required=False, default='1h')
def radio(song_name, duration):
    """Create a radio station (shortcut for 'cue radio')"""
    query = f"radio:{song_name}"
    client.play_track(query, duration)


@cli.group(name='quietly', invoke_without_command=False)
def quietly_group():
    """Run commands with minimal output"""
    pass


@quietly_group.command(name='cue')
@click.argument('query')
@click.argument('duration', required=False)
def quietly_cue(query, duration):
    """Play a track quietly (minimal output)"""
    client.play_track(query, duration, quiet=True)


@cli.command()
def stop():
    """Stop current playback immediately"""
    client.stop_playback()


@cli.command()
def status():
    """Show current playback status"""
    client.get_status()


@cli.command()
@click.option('--url', help='Server URL')
@click.option('--timeout', type=int, help='Request timeout')
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
        click.echo("Current configuration:")
        click.echo(f"  Server URL: {current_config['server_url']}")
        click.echo(f"  Timeout: {current_config['timeout']}s")
        click.echo(f"  Config file: {CONFIG_FILE}")


@cli.command()
@click.option('--limit', '-n', default=20, help='Number to show')
@click.option('--today', is_flag=True, help='Today only')
@click.option('--this-week', is_flag=True, help='This week only')
@click.option('--combined', '-c', is_flag=True, help='Include Spotify history')
def history(limit, today, this_week, combined):
    """Show playback history"""
    if combined:
        client.show_combined_history(limit=limit)
    else:
        client.show_history(limit=limit, today_only=today, this_week=this_week)


@cli.command()
@click.argument('duration', required=False)
def lucky(duration):
    """Play a random track based on your taste"""
    client.play_lucky(duration)


@cli.command()
@click.argument('query')
def search(query):
    """Search for tracks without playing"""
    client.show_search_results(query, select_mode=False)


@cli.command()
@click.argument('duration')
def extend(duration):
    """Extend or reduce current playback session"""
    client.extend_session(duration)


@cli.command()
@click.option('--duration', '-d', help='Override duration')
@click.option('--select', '-s', is_flag=True, help='Choose session')
def resume(duration, select):
    """Resume a previously stopped session"""
    client.resume_session(duration=duration, select=select)


@cli.group(name='queue', invoke_without_command=True)
@click.pass_context
def queue_group(ctx):
    """Manage playback queue"""
    if ctx.invoked_subcommand is None:
        client.show_queue()


@queue_group.command(name='add')
@click.argument('query')
@click.argument('duration', required=False)
def queue_add(query, duration):
    """Add a track to the queue"""
    client.add_to_queue(query, duration)


@queue_group.command(name='remove')
@click.argument('position', type=int)
def queue_remove(position):
    """Remove a track from the queue"""
    client.remove_from_queue(position)


@queue_group.command(name='clear')
@click.confirmation_option(prompt='Clear entire queue?')
def queue_clear():
    """Clear all tracks from the queue"""
    client.clear_queue()


@cli.command()
def skip():
    """Skip to next track in queue"""
    client.skip_track()


@cli.command()
def health():
    """Check server health and connection"""
    try:
        result = client.make_request('GET', '/health')
        click.secho("[OK] Server is healthy", fg='green')
        click.echo(f"     Spotify connected: {'Yes' if result['spotify_connected'] else 'No'}")
        click.echo(f"     Server time: {client._format_time(result['timestamp'])}")
    except SystemExit:
        pass


# MODE COMMANDS
@cli.group(name='mode', invoke_without_command=True)
@click.pass_context
def mode_group(ctx):
    """Manage NotVox playback modes"""
    if ctx.invoked_subcommand is None:
        # Show current mode if no subcommand
        result = client.make_request('GET', '/mode/current')
        mode = result.get('mode')
        if mode:
            click.secho(f"[CURRENT MODE] {mode}", fg='cyan')
            if 'config' in result:
                config = result['config']
                click.echo(f"  Description: {config.get('description', 'N/A')}")
                click.echo(f"  Duration: {config.get('duration', 'N/A')}")
                click.echo(f"  Volume: {config.get('volume', 'N/A')}")
        else:
            click.echo("No active mode")


@mode_group.command(name='list')
def mode_list():
    """List all available modes"""
    result = client.make_request('GET', '/modes')
    modes = result.get('modes', {})

    if not modes:
        click.echo("No modes available")
        return

    click.echo("Available modes:\n")
    for name, config in modes.items():
        click.secho(f"[{name}]", fg='cyan', bold=True)
        click.echo(f"  {config['description']}")
        click.echo(f"  Duration: {config['duration']} | Volume: {config['volume']}")
        click.echo()


@mode_group.command(name='start')
@click.argument('mode_name')
@click.option('--duration', '-d', help='Override default duration')
@click.option('--volume', '-v', type=int, help='Override default volume')
def mode_start(mode_name, duration, volume):
    """Start a specific mode"""
    data = {'mode': mode_name}
    if duration:
        data['duration'] = duration
    if volume:
        data['volume'] = volume

    result = client.make_request('POST', '/mode/start', json=data)

    click.secho(f"[MODE] {result['message']}", fg='green')
    if 'track' in result:
        click.echo(f"       Now playing: {result['track']}")
    click.echo(f"       Duration: {result['duration']}")
    click.echo(f"       Ends at: {client._format_time(result['ends_at'])}")


@mode_group.command(name='stop')
def mode_stop():
    """Stop current mode and playback"""
    result = client.make_request('POST', '/mode/stop')
    click.secho(f"[STOP] {result['message']}", fg='yellow')


@mode_group.command(name='create')
@click.argument('name')
@click.option('--based-on', help='Base new mode on existing mode')
@click.option('--duration', default='1h', help='Default duration')
@click.option('--volume', default=50, help='Default volume')
@click.option('--description', help='Mode description')
def mode_create(name, based_on, duration, volume, description):
    """Create a custom mode"""
    config = {
        'duration': duration,
        'volume': volume,
        'description': description or f"Custom {name} mode"
    }

    if based_on:
        # Get base mode config first
        base_result = client.make_request('GET', f'/mode/{based_on}')
        if 'config' in base_result:
            base_config = base_result['config']
            base_config.update(config)
            config = base_config

    data = {'name': name, 'config': config}
    result = client.make_request('POST', '/mode/create', json=data)

    click.secho(f"[OK] Created mode '{name}'", fg='green')
    click.echo(f"     Description: {config['description']}")
    click.echo(f"     Duration: {config['duration']}")
    click.echo(f"     Volume: {config['volume']}")


@mode_group.command(name='config')
@click.argument('mode_name')
@click.option('--duration', help='Set default duration')
@click.option('--volume', type=int, help='Set default volume')
@click.option('--description', help='Set description')
def mode_config(mode_name, duration, volume, description):
    """Configure an existing mode"""
    updates = {}
    if duration:
        updates['duration'] = duration
    if volume is not None:
        updates['volume'] = volume
    if description:
        updates['description'] = description

    if not updates:
        # Just show current config
        result = client.make_request('GET', f'/mode/{mode_name}')
        if 'config' in result:
            config = result['config']
            click.echo(f"\nMode '{mode_name}' configuration:")
            for key, value in config.items():
                click.echo(f"  {key}: {value}")
    else:
        # Update config
        data = {'updates': updates}
        result = client.make_request('PUT', f'/mode/{mode_name}', json=data)
        click.secho(f"[OK] Updated mode '{mode_name}'", fg='green')


@mode_group.command(name='delete')
@click.argument('mode_name')
@click.confirmation_option(prompt='Delete this mode?')
def mode_delete(mode_name):
    """Delete a custom mode"""
    result = client.make_request('DELETE', f'/mode/{mode_name}')
    click.secho(f"[OK] {result['message']}", fg='green')


# Quick access commands at top level
@cli.command()
@click.option('--duration', '-d', help='Override default duration')
def focus(duration):
    """Quick start focus mode"""
    data = {'mode': 'focus'}
    if duration:
        data['duration'] = duration

    result = client.make_request('POST', '/mode/start', json=data)
    click.secho(f"[FOCUS MODE] {result['message']}", fg='cyan')
    if 'track' in result:
        click.echo(f"             Now playing: {result['track']}")
    click.echo(f"             Duration: {result['duration']}")


@cli.command()
@click.option('--duration', '-d', help='Override default duration')
def party(duration):
    """Quick start party mode"""
    data = {'mode': 'party'}
    if duration:
        data['duration'] = duration

    result = client.make_request('POST', '/mode/start', json=data)
    click.secho(f"[PARTY MODE] {result['message']}", fg='magenta')
    if 'track' in result:
        click.echo(f"             Now playing: {result['track']}")
    click.echo(f"             Duration: {result['duration']}")


@cli.command()
@click.option('--duration', '-d', help='Override default duration')
def workout(duration):
    """Quick start workout mode"""
    data = {'mode': 'workout'}
    if duration:
        data['duration'] = duration

    result = client.make_request('POST', '/mode/start', json=data)
    click.secho(f"[WORKOUT MODE] {result['message']}", fg='red')
    if 'track' in result:
        click.echo(f"               Now playing: {result['track']}")
    click.echo(f"               Duration: {result['duration']}")


@cli.command()
@click.option('--duration', '-d', help='Override default duration')
def sleep(duration):
    """Quick start sleep mode"""
    data = {'mode': 'sleep'}
    if duration:
        data['duration'] = duration

    result = client.make_request('POST', '/mode/start', json=data)
    click.secho(f"[SLEEP MODE] {result['message']}", fg='blue')
    if 'track' in result:
        click.echo(f"             Now playing: {result['track']}")
    click.echo(f"             Duration: {result['duration']}")


# VOLUME & DEVICE COMMANDS
@cli.command()
@click.argument('level', required=False)
def volume(level):
    """Set or get volume (0-100 or +/-10)"""
    if not level:
        # Get current volume
        try:
            result = client.make_request('GET', '/volume')
            click.echo(f"Current volume: {result['volume']}%")
        except SystemExit:
            pass
    else:
        # Set volume
        data = {'volume': level}
        result = client.make_request('POST', '/volume', json=data)
        click.secho(f"[OK] Volume set to {result['volume']}%", fg='green')


@cli.group(name='device', invoke_without_command=True)
@click.pass_context
def device_group(ctx):
    """Manage Spotify devices"""
    if ctx.invoked_subcommand is None:
        # Show devices if no subcommand
        result = client.make_request('GET', '/devices')
        devices = result.get('devices', [])
        active = result.get('active_device')

        if not devices:
            click.echo("No Spotify devices found")
            return

        click.echo("Available Spotify devices:\n")
        for device in devices:
            status = "[ACTIVE]" if device['is_active'] else "        "
            type_emoji = {
                'Computer': '💻',
                'Smartphone': '📱',
                'Speaker': '🔊',
                'TV': '📺',
                'AVR': '🎚️',
                'CastVideo': '📺',
                'CastAudio': '🔊'
            }.get(device['type'], '🎵')

            click.echo(f"{status} {type_emoji}  {device['name']}")
            click.echo(f"         Type: {device['type']} | Volume: {device['volume']}%")
            if device['is_restricted']:
                click.echo(f"         ⚠️  Restricted device")
            click.echo()


@device_group.command(name='list')
def device_list():
    """List all available devices"""
    result = client.make_request('GET', '/devices')
    devices = result.get('devices', [])

    if not devices:
        click.echo("No Spotify devices found")
        return

    click.echo("Available Spotify devices:\n")
    for i, device in enumerate(devices, 1):
        active = '🟢' if device['is_active'] else '⚪'
        click.echo(f"{active} [{i}] {device['name']}")
        click.echo(f"      Type: {device['type']}")
        click.echo(f"      Volume: {device['volume']}%")
        click.echo(f"      ID: {device['id'][:8]}...")
        click.echo()


@device_group.command(name='switch')
@click.argument('device_name')
def device_switch(device_name):
    """Switch playback to a different device"""
    data = {'device': device_name}
    result = client.make_request('POST', '/device/transfer', json=data)

    device = result.get('device', {})
    click.secho(f"[OK] {result['message']}", fg='green')
    click.echo(f"     Device type: {device.get('type', 'Unknown')}")
    click.echo(f"     Volume: {device.get('volume', 0)}%")


@device_group.command(name='transfer')
@click.argument('device_name')
def device_transfer(device_name):
    """Transfer playback to device (alias for switch)"""
    data = {'device': device_name}
    result = client.make_request('POST', '/device/transfer', json=data)

    device = result.get('device', {})
    click.secho(f"[OK] {result['message']}", fg='green')


# Quick volume shortcuts
@cli.command(name='vol')
@click.argument('level')
def vol(level):
    """Quick volume control (shortcut for volume)"""
    data = {'volume': level}
    result = client.make_request('POST', '/volume', json=data)
    click.secho(f"[OK] Volume: {result['volume']}%", fg='green')


@cli.command(name='louder')
@click.argument('amount', default=10)
def louder(amount):
    """Increase volume"""
    data = {'volume': f'+{amount}'}
    result = client.make_request('POST', '/volume', json=data)
    click.secho(f"[OK] Volume increased to {result['volume']}%", fg='green')


@cli.command(name='quieter')
@click.argument('amount', default=10)
def quieter(amount):
    """Decrease volume"""
    data = {'volume': f'-{amount}'}
    result = client.make_request('POST', '/volume', json=data)
    click.secho(f"[OK] Volume decreased to {result['volume']}%", fg='green')


@cli.command(name='mute')
def mute():
    """Mute playback (set volume to 0)"""
    data = {'volume': '0'}
    result = client.make_request('POST', '/volume', json=data)
    click.secho(f"[MUTED] Volume: 0%", fg='yellow')


if __name__ == '__main__':
    cli()