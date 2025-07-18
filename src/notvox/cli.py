# client/src/notvox/cli.py
"""NotVox CLI - Main entry point"""

import click

from .commands.playback import (
    cue_group, stop, status, extend, skip, lucky, search, resume,
    genre, radio, quietly_group
)
from .commands.queue import queue_group
from .commands.modes import (
    mode_group, focus, party, workout, sleep
)
from .commands.devices import (
    volume, device_group, vol, louder, quieter, mute
)
from .commands.history import history
from .commands.config import config, health


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


# Register all commands
cli.add_command(cue_group)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(extend)
cli.add_command(skip)
cli.add_command(lucky)
cli.add_command(search)
cli.add_command(resume)
cli.add_command(genre)
cli.add_command(radio)
cli.add_command(quietly_group)

# Queue commands
cli.add_command(queue_group)

# Mode commands
cli.add_command(mode_group)
cli.add_command(focus)
cli.add_command(party)
cli.add_command(workout)
cli.add_command(sleep)

# Device commands
cli.add_command(volume)
cli.add_command(device_group)
cli.add_command(vol)
cli.add_command(louder)
cli.add_command(quieter)
cli.add_command(mute)

# History & config commands
cli.add_command(history)
cli.add_command(config)
cli.add_command(health)


if __name__ == '__main__':
    cli()