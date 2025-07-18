# client/src/notvox/commands/config.py
"""Configuration and health check commands"""

import click

from ..client import client
from ..utils.constants import CONFIG_FILE
from ..utils.formatting import format_time


@click.command()
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


@click.command()
def health():
    """Check server health and connection"""
    try:
        result = client.health_check()
        click.secho("[OK] Server is healthy", fg='green')
        click.echo(f"     Spotify connected: {'Yes' if result['spotify_connected'] else 'No'}")
        click.echo(f"     Server time: {format_time(result['timestamp'])}")
    except SystemExit:
        pass