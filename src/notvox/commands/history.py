# client/src/notvox/commands/history.py
"""History and statistics commands"""

from datetime import datetime, timedelta

import click

from ..client import client
from ..utils.formatting import format_duration, format_relative_time, truncate_text
from ..utils.constants import STATUS_CONFIG, MAX_TRACK_DISPLAY_LENGTH, DEFAULT_HISTORY_LIMIT


@click.command()
@click.option('--limit', '-n', default=DEFAULT_HISTORY_LIMIT, help='Number to show')
@click.option('--today', is_flag=True, help='Today only')
@click.option('--this-week', is_flag=True, help='This week only')
@click.option('--combined', '-c', is_flag=True, help='Include Spotify history')
def history(limit, today, this_week, combined):
    """Show playback history"""
    if combined:
        show_combined_history(limit)
    else:
        show_history(limit, today_only=today, this_week=this_week)


def show_history(limit=20, today_only=False, this_week=False):
    """Display playback history"""
    since = None
    if today_only:
        since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    elif this_week:
        since = (datetime.now() - timedelta(days=7)).isoformat()

    history = client.get_history(limit=limit, since=since)
    sessions = history.get("sessions", [])

    if not sessions:
        click.echo("No playback history found.")
        return

    click.echo("Recent playback sessions:\n")

    for i, session in enumerate(sessions, 1):
        # Format track name
        track = truncate_text(session["track_name"], MAX_TRACK_DISPLAY_LENGTH)

        # Format duration
        duration = format_duration(session["duration_seconds"])

        # Format time
        relative_time = format_relative_time(session["start_time"])

        # Format status
        status = session["status"]
        status_color, status_symbol = STATUS_CONFIG.get(status, ("cyan", "[PLAY]"))

        # Play count
        play_count = session.get("play_count", 1)
        play_indicator = f"(played {play_count}x)" if play_count > 1 else ""

        # Display entry
        click.echo(f"[{i}] {track} - {duration}")
        click.echo(f"    Started: {relative_time} {play_indicator}")
        click.secho(f"    Status: {status_symbol} {status}", fg=status_color)
        click.echo()


def show_combined_history(limit=20):
    """Show combined NotVox and Spotify history"""
    # Get NotVox history
    notvox_history = client.get_history(limit=limit)
    notvox_sessions = notvox_history.get("sessions", [])

    # Get Spotify history
    try:
        spotify_history = client.get_spotify_history()
        spotify_tracks = spotify_history.get("tracks", [])
    except:
        spotify_tracks = []

    click.echo("Combined playback history:\n")

    # Show recent NotVox sessions
    if notvox_sessions:
        click.secho("[NotVox History]", fg="cyan", bold=True)
        for i, session in enumerate(notvox_sessions[:10], 1):
            track = truncate_text(session["track_name"], MAX_TRACK_DISPLAY_LENGTH)

            duration = format_duration(session["duration_seconds"])
            relative_time = format_relative_time(session["start_time"])
            play_count = session.get("play_count", 1)

            click.echo(f"{i:2d}. {track} - {duration}")
            play_indicator = f"(played {play_count}x)" if play_count > 1 else ""
            click.echo(f"    {relative_time} {play_indicator}")

    # Show Spotify history
    if spotify_tracks:
        click.echo()
        click.secho("[Spotify History]", fg="green", bold=True)
        for i, track in enumerate(spotify_tracks[:10], 1):
            name = truncate_text(f"{track['name']} - {track['artist']}", MAX_TRACK_DISPLAY_LENGTH)

            play_count = track.get("spotify_play_count", 1)
            relative_time = format_relative_time(track["played_at"])

            click.echo(f"{i:2d}. {name}")
            play_indicator = f"(played {play_count}x recently)" if play_count > 1 else ""
            click.echo(f"    {relative_time} {play_indicator}")

    if not notvox_sessions and not spotify_tracks:
        click.echo("No playback history found.")
    else:
        click.echo()
        click.echo("Lucky mode uses this combined history to pick tracks you'll enjoy!")