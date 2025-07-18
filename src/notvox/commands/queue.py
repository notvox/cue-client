# client/src/notvox/commands/queue.py
"""Queue management commands"""

import click

from ..client import client
from ..utils.formatting import format_duration, truncate_text
from ..utils.constants import MAX_TRACK_DISPLAY_LENGTH


@click.group(name='queue', invoke_without_command=True)
@click.pass_context
def queue_group(ctx):
    """Manage playback queue"""
    if ctx.invoked_subcommand is None:
        show_queue()


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
    # First get the queue to find the ID
    queue_data = client.get_queue()
    queue_items = queue_data.get("queue", [])

    if position < 1 or position > len(queue_items):
        click.secho(f"[ERROR] Invalid position. Queue has {len(queue_items)} items.", fg="red")
        return None

    item = queue_items[position - 1]
    client.remove_from_queue(item["id"])
    click.secho(f"[OK] Removed '{item['track_name']}' from queue", fg="green")


@queue_group.command(name='clear')
@click.confirmation_option(prompt='Clear entire queue?')
def queue_clear():
    """Clear all tracks from the queue"""
    client.clear_queue()


def show_queue():
    """Display current queue"""
    queue_data = client.get_queue()
    queue_items = queue_data.get("queue", [])

    if not queue_items:
        click.echo("Queue is empty.")
        return

    click.echo("Current queue:\n")

    total_seconds = 0
    for i, item in enumerate(queue_items, 1):
        track = truncate_text(item["track_name"], MAX_TRACK_DISPLAY_LENGTH)
        duration = format_duration(item["duration_seconds"])
        total_seconds += item["duration_seconds"]

        click.echo(f"[{i}] {track} - {duration}")

    click.echo(f"\nTotal queue time: {format_duration(total_seconds)}")

    if queue_data.get("currently_playing_from_queue"):
        click.echo("\n(Currently playing track is from queue)")