# client/src/notvox/commands/modes.py
"""Mode management commands"""

import click

from ..client import client


@click.group(name='mode', invoke_without_command=True)
@click.pass_context
def mode_group(ctx):
    """Manage NotVox playback modes"""
    if ctx.invoked_subcommand is None:
        # Show current mode if no subcommand
        result = client.get_current_mode()
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
    result = client.get_modes()
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
    client.start_mode(mode_name, duration, volume)


@mode_group.command(name='stop')
def mode_stop():
    """Stop current mode and playback"""
    client.stop_mode()


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
        base_result = client.get_mode(based_on)
        if 'config' in base_result:
            base_config = base_result['config']
            base_config.update(config)
            config = base_config

    client.create_mode(name, config)


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
        result = client.get_mode(mode_name)
        if 'config' in result:
            config = result['config']
            click.echo(f"\nMode '{mode_name}' configuration:")
            for key, value in config.items():
                click.echo(f"  {key}: {value}")
    else:
        # Update config
        client.update_mode(mode_name, updates)


@mode_group.command(name='delete')
@click.argument('mode_name')
@click.confirmation_option(prompt='Delete this mode?')
def mode_delete(mode_name):
    """Delete a custom mode"""
    client.delete_mode(mode_name)


# Quick access mode commands
@click.command()
@click.option('--duration', '-d', help='Override default duration')
def focus(duration):
    """Quick start focus mode"""
    client.start_mode('focus', duration)
    click.secho(f"[FOCUS MODE] Started", fg='cyan')


@click.command()
@click.option('--duration', '-d', help='Override default duration')
def party(duration):
    """Quick start party mode"""
    client.start_mode('party', duration)
    click.secho(f"[PARTY MODE] Started", fg='magenta')


@click.command()
@click.option('--duration', '-d', help='Override default duration')
def workout(duration):
    """Quick start workout mode"""
    client.start_mode('workout', duration)
    click.secho(f"[WORKOUT MODE] Started", fg='red')


@click.command()
@click.option('--duration', '-d', help='Override default duration')
def sleep(duration):
    """Quick start sleep mode"""
    client.start_mode('sleep', duration)
    click.secho(f"[SLEEP MODE] Started", fg='blue')