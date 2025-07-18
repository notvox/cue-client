# client/src/notvox/commands/playback.py
"""Playback related commands"""

from typing import Optional

import click

from ..client import client
from ..utils.formatting import (
    format_track_duration_ms, get_popularity_indicator, truncate_text
)
from ..utils.constants import MAX_TRACK_DISPLAY_LENGTH


# Custom group for cue command
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
                show_search_results(query, select_mode=True, duration=duration)
            else:
                client.play_track(query, duration)
        else:
            click.echo(self.get_help(ctx))


@click.group(name='cue', cls=CueGroup, invoke_without_command=True, 
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
        show_search_results(track_name, select_mode=True, duration=duration)
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


# Standalone commands
@click.command()
def stop():
    """Stop current playback immediately"""
    client.stop_playback()


@click.command()
def status():
    """Show current playback status"""
    client.get_status()


@click.command()
@click.argument('duration')
def extend(duration):
    """Extend or reduce current playback session"""
    client.extend_session(duration)


@click.command()
def skip():
    """Skip to next track in queue"""
    client.skip_track()


@click.command()
@click.argument('duration', required=False)
def lucky(duration):
    """Play a random track based on your taste"""
    client.play_lucky(duration)


@click.command()
@click.argument('query')
def search(query):
    """Search for tracks without playing"""
    show_search_results(query, select_mode=False)


@click.command()
@click.option('--duration', '-d', help='Override duration')
@click.option('--select', '-s', is_flag=True, help='Choose session')
def resume(duration, select):
    """Resume a previously stopped session"""
    if select:
        show_resume_selection(duration)
    else:
        client.resume_session(duration=duration)


# Shortcut commands
@click.command()
@click.argument('genre_name')
@click.argument('duration', required=False, default='1h')
def genre(genre_name, duration):
    """Quick play music by genre (shortcut for 'cue genre')"""
    query = f"genre:{genre_name}"
    client.play_track(query, duration)


@click.command()
@click.argument('song_name')
@click.argument('duration', required=False, default='1h')
def radio(song_name, duration):
    """Create a radio station (shortcut for 'cue radio')"""
    query = f"radio:{song_name}"
    client.play_track(query, duration)


# Quietly group
@click.group(name='quietly', invoke_without_command=False)
def quietly_group():
    """Run commands with minimal output"""
    pass


@quietly_group.command(name='cue')
@click.argument('query')
@click.argument('duration', required=False)
def quietly_cue(query, duration):
    """Play a track quietly (minimal output)"""
    client.play_track(query, duration, quiet=True)


# Helper functions
def show_search_results(query: str, select_mode: bool = False, duration: Optional[str] = None):
    """Display search results, optionally allow selection"""
    results = client.search_tracks(query, limit=10 if select_mode else 5)
    tracks = results.get("tracks", [])

    if not tracks:
        click.secho(f"[ERROR] No tracks found for '{query}'", fg="red")
        return None

    click.echo(f"\nSearch results for: {query}\n")

    for i, track in enumerate(tracks, 1):
        # Format duration
        track_duration = format_track_duration_ms(track["duration_ms"])
        
        # Popularity indicator
        pop_indicator = get_popularity_indicator(track["popularity"])

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
                    client.play_track_uri(selected["uri"], track_name, duration)
                    return selected
                else:
                    click.secho(f"Please enter a number between 1 and {len(tracks)}", fg="yellow")
            except (ValueError, EOFError, KeyboardInterrupt):
                click.echo("\nCancelled.")
                return None

    return tracks


def show_resume_selection(duration: Optional[str] = None):
    """Show recent stopped sessions to choose from"""
    history = client.get_history(limit=10)
    stopped_sessions = [s for s in history.get("sessions", []) if s["status"] == "stopped"]

    if not stopped_sessions:
        click.secho("[ERROR] No stopped sessions to resume", fg="red")
        return None

    click.echo("Recent stopped sessions:\n")
    for i, session in enumerate(stopped_sessions[:5], 1):
        track = truncate_text(session["track_name"], MAX_TRACK_DISPLAY_LENGTH)
        from ..utils.formatting import format_relative_time, format_duration
        relative_time = format_relative_time(session["start_time"])
        original_duration = format_duration(session["duration_seconds"])

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
                client.resume_session(session_id=selected["id"], duration=duration)
                return
            else:
                click.secho(f"Please enter a number between 1 and {len(stopped_sessions)}", fg="yellow")
        except (ValueError, EOFError, KeyboardInterrupt):
            click.echo("\nCancelled.")
            return None