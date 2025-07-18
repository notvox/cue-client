# client/src/notvox/commands/devices.py
"""Volume and device management commands"""

import click

from ..client import client
from ..utils.constants import DEVICE_EMOJIS


@click.command()
@click.argument('level', required=False)
def volume(level):
    """Set or get volume (0-100 or +/-10)"""
    if not level:
        # Get current volume
        try:
            result = client.get_volume()
            click.echo(f"Current volume: {result['volume']}%")
        except SystemExit:
            pass
    else:
        # Set volume
        client.set_volume(level)


@click.group(name='device', invoke_without_command=True)
@click.pass_context
def device_group(ctx):
    """Manage Spotify devices"""
    if ctx.invoked_subcommand is None:
        # Show devices if no subcommand
        show_devices()


@device_group.command(name='list')
def device_list():
    """List all available devices"""
    show_devices(detailed=True)


@device_group.command(name='switch')
@click.argument('device_name')
def device_switch(device_name):
    """Switch playback to a different device"""
    client.transfer_device(device_name)


@device_group.command(name='transfer')
@click.argument('device_name')
def device_transfer(device_name):
    """Transfer playback to device (alias for switch)"""
    client.transfer_device(device_name)


# Quick volume shortcuts
@click.command(name='vol')
@click.argument('level')
def vol(level):
    """Quick volume control (shortcut for volume)"""
    client.set_volume(level)


@click.command(name='louder')
@click.argument('amount', default=10)
def louder(amount):
    """Increase volume"""
    client.set_volume(f'+{amount}')


@click.command(name='quieter')
@click.argument('amount', default=10)
def quieter(amount):
    """Decrease volume"""
    client.set_volume(f'-{amount}')


@click.command(name='mute')
def mute():
    """Mute playback (set volume to 0)"""
    data = {'volume': '0'}
    result = client.set_volume('0')
    click.secho(f"[MUTED] Volume: 0%", fg='yellow')


# Helper functions
def show_devices(detailed=False):
    """Display available devices"""
    result = client.get_devices()
    devices = result.get('devices', [])
    active = result.get('active_device')

    if not devices:
        click.echo("No Spotify devices found")
        return

    click.echo("Available Spotify devices:\n")
    
    if detailed:
        for i, device in enumerate(devices, 1):
            active = '🟢' if device['is_active'] else '⚪'
            click.echo(f"{active} [{i}] {device['name']}")
            click.echo(f"      Type: {device['type']}")
            click.echo(f"      Volume: {device['volume']}%")
            click.echo(f"      ID: {device['id'][:8]}...")
            click.echo()
    else:
        for device in devices:
            status = "[ACTIVE]" if device['is_active'] else "        "
            type_emoji = DEVICE_EMOJIS.get(device['type'], '🎵')
            
            click.echo(f"{status} {type_emoji}  {device['name']}")
            click.echo(f"         Type: {device['type']} | Volume: {device['volume']}%")
            if device['is_restricted']:
                click.echo(f"         ⚠️  Restricted device")
            click.echo()