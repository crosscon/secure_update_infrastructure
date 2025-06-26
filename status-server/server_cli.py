# server_cli.py
#
# A command-line interface (CLI) for interacting with the SUIT status server.
# It provides commands to list devices and firmwares, and to add or delete firmwares.

import argparse
import sys
import os
import requests
from rich.console import Console
from rich.table import Table

# --- Configuration ---
SERVER_BASE_URL = "http://localhost:5000"

def list_devices(args):
    """Fetches and displays the list of devices from the server."""
    console = Console()
    try:
        response = requests.get(f"{SERVER_BASE_URL}/devices")
        response.raise_for_status() # Raise an exception for bad status codes
        devices = response.json()

        if not devices:
            console.print("[yellow]No devices found in the database.[/yellow]")
            return

        table = Table(title="Registered Devices")
        table.add_column("Device ID (MAC)", style="cyan", no_wrap=True)
        table.add_column("Last IP", style="magenta")
        table.add_column("Current Version", style="green")
        table.add_column("Status") # Style is now applied per-row
        table.add_column("Last Seen (UTC)", style="blue")
        
        for device in devices:
            status = device['status']
            status_style = "yellow" # Default color
            if 'success' in status.lower():
                status_style = "green"
            elif 'fail' in status.lower():
                status_style = "red"
            
            table.add_row(
                device['device_id'],
                device['last_ip'],
                device['current_version'],
                f"[{status_style}]{status}[/{status_style}]",
                device['last_seen']
            )
        
        console.print(table)

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error connecting to server: {e}[/bold red]")
        sys.exit(1)

def list_firmwares(args):
    """Fetches and displays the list of available firmwares."""
    console = Console()
    try:
        response = requests.get(f"{SERVER_BASE_URL}/firmwares")
        response.raise_for_status()
        firmwares = response.json()
        
        if not firmwares:
            console.print("[yellow]No firmwares found in the database.[/yellow]")
            return

        table = Table(title="Available Firmwares")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("File Name", style="magenta")
        table.add_column("Version", style="green")
        table.add_column("SHA-256 Hash", style="blue")

        for fw in firmwares:
            table.add_row(
                str(fw['id']),
                fw['file_name'],
                fw['version'],
                fw['hash']
            )

        console.print(table)

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error connecting to server: {e}[/bold red]")
        sys.exit(1)

def add_firmware(args):
    """Adds a new firmware file by uploading it to the server."""
    console = Console()
    filepath = args.file
    version = args.version

    if not os.path.exists(filepath):
        console.print(f"[bold red]Error: File not found at '{filepath}'[/bold red]")
        sys.exit(1)
        
    files = {'file': (os.path.basename(filepath), open(filepath, 'rb'))}
    data = {'version': version}
    
    console.print(f"Uploading [cyan]'{filepath}'[/cyan] as version [green]'{version}'[/green]...")
    
    try:
        response = requests.post(f"{SERVER_BASE_URL}/add_firmware", files=files, data=data)
        response.raise_for_status()
        result = response.json()
        console.print(f"[bold green]Success:[/bold green] {result.get('success', 'Firmware added.')}")
        if 'hash' in result:
             console.print(f"  [blue]Hash:[/blue] {result['hash']}")

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error during upload: {e}[/bold red]")
        if e.response:
            try:
                console.print(f"  [red]Server says:[/red] {e.response.json().get('error', e.response.text)}")
            except ValueError:
                pass
        sys.exit(1)

def delete_firmware(args):
    """Deletes a firmware from the server using its ID."""
    console = Console()
    firmware_id = args.id
    
    console.print(f"Attempting to delete firmware with ID [cyan]{firmware_id}[/cyan]...")

    try:
        response = requests.delete(f"{SERVER_BASE_URL}/delete_firmware/{firmware_id}")
        response.raise_for_status()
        result = response.json()
        console.print(f"[bold green]Success:[/bold green] {result.get('success', 'Firmware deleted.')}")

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error during deletion: {e}[/bold red]")
        if e.response:
            try:
                console.print(f"  [red]Server says:[/red] {e.response.json().get('error', e.response.text)}")
            except ValueError:
                pass
        sys.exit(1)

def clear_devices(args):
    """Deletes all devices from the server's database."""
    console = Console()
    
    if not args.yes:
        confirmation = console.input("[bold yellow]Are you sure you want to delete ALL devices? This cannot be undone. (y/N) [/bold yellow]")
        if confirmation.lower() != 'y':
            console.print("[green]Operation cancelled.[/green]")
            return

    console.print("Sending request to clear all devices...")

    try:
        response = requests.delete(f"{SERVER_BASE_URL}/devices/clear")
        response.raise_for_status()
        result = response.json()
        console.print(f"[bold green]Success:[/bold green] {result.get('success', 'All devices cleared.')}")

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error during operation: {e}[/bold red]")
        if e.response:
            try:
                console.print(f"  [red]Server says:[/red] {e.response.json().get('error', e.response.text)}")
            except ValueError:
                pass
        sys.exit(1)

def clear_firmwares(args):
    """Deletes all firmwares from the server's database and filesystem."""
    console = Console()
    
    if not args.yes:
        confirmation = console.input("[bold yellow]Are you sure you want to delete ALL firmwares? This cannot be undone. (y/N) [/bold yellow]")
        if confirmation.lower() != 'y':
            console.print("[green]Operation cancelled.[/green]")
            return

    console.print("Sending request to clear all firmwares...")

    try:
        response = requests.delete(f"{SERVER_BASE_URL}/firmwares/clear")
        response.raise_for_status()
        result = response.json()
        console.print(f"[bold green]Success:[/bold green] {result.get('success', 'All firmwares cleared.')}")

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error during operation: {e}[/bold red]")
        if e.response:
            try:
                console.print(f"  [red]Server says:[/red] {e.response.json().get('error', e.response.text)}")
            except ValueError:
                pass
        sys.exit(1)

def main():
    """Main function to parse arguments and call the appropriate handler."""
    parser = argparse.ArgumentParser(
        description="A CLI to manage the SUIT status server.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')

    # --- 'devices' command ---
    parser_devices = subparsers.add_parser(
        "devices",
        help="List all registered devices.",
        description="Retrieves and displays a list of all devices that have connected to the server."
    )
    parser_devices.set_defaults(func=list_devices)

    # --- 'firmwares' command ---
    parser_firmwares = subparsers.add_parser(
        "firmwares",
        help="List all available firmwares.",
        description="Retrieves and displays a list of all firmwares available on the server."
    )
    parser_firmwares.set_defaults(func=list_firmwares)

    # --- 'add' command ---
    parser_add = subparsers.add_parser(
        "add",
        help="Add a new firmware to the server.",
        description="Uploads a new firmware file to the server database."
    )
    parser_add.add_argument("file", help="The path to the firmware file to upload.")
    parser_add.add_argument("version", help="The version string for this firmware (e.g., '1.0.1').")
    parser_add.set_defaults(func=add_firmware)
    
    # --- 'delete' command ---
    parser_delete = subparsers.add_parser(
        "delete",
        help="Delete a firmware from the server.",
        description="Removes a firmware from the server database and filesystem using its ID."
    )
    parser_delete.add_argument("id", type=int, help="The ID of the firmware to delete.")
    parser_delete.set_defaults(func=delete_firmware)

    # --- 'clear-devices' command ---
    parser_clear_devices = subparsers.add_parser(
        "clear-devices",
        help="Clear all devices from the database.",
        description="Deletes all device records from the server's database. This is irreversible."
    )
    parser_clear_devices.add_argument("-y", "--yes", action="store_true", help="Bypass the confirmation prompt.")
    parser_clear_devices.set_defaults(func=clear_devices)

    # --- 'clear-firmwares' command ---
    parser_clear_firmwares = subparsers.add_parser(
        "clear-firmwares",
        help="Clear all firmwares from the database.",
        description="Deletes all firmware records and files from the server. This is irreversible."
    )
    parser_clear_firmwares.add_argument("-y", "--yes", action="store_true", help="Bypass the confirmation prompt.")
    parser_clear_firmwares.set_defaults(func=clear_firmwares)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
