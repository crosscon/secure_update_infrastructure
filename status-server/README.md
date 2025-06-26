# SUIT-Compliant Firmware Update Server

This project implements a SUIT (Software Updates for IoT - RFC 9019) compliant status and firmware update server in Python. It provides a complete ecosystem for managing and deploying firmware updates to connected IoT devices.

The system consists of a central server, a command-line management tool, and a client application designed to run on an IoT device.

## Table of Contents

- [Project Components](#project-components)
- [Features](#features)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
  - [Step 1: Start the Server](#step-1-start-the-server)
  - [Step 2: Start the Device Client](#step-2-start-the-device-client)
  - [Step 3: Manage the Server with the CLI](#step-3-manage-the-server-with-the-cli)
- [Testing Failure Scenarios](#testing-failure-scenarios)

## Project Components

This project is composed of several key scripts that work together:

| File                  | Description                                                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `suit_server.py`      | The core application. It runs a Flask web server for API endpoints and a WebSocket server for real-time, bidirectional communication with devices. It manages device status and firmware information in an SQLite database. |
| `updater_client.py`   | The client application intended to run on an actual IoT device. It retrieves its unique MAC address, reports its status, and handles firmware updates by calling an external handler script. |
| `update_handler.py`   | A placeholder script that simulates a real-world firmware installation utility. It is called by the `updater_client` to verify and apply a downloaded firmware file. It reports success or failure via its exit code. |
| `server_cli.py`       | A user-friendly command-line interface (CLI) for managing the server. It allows an administrator to view devices, list firmwares, and add or delete firmware files. |
| `schema.sql`          | The SQL schema used to initialize the SQLite database (`suit_server.db`) with the necessary tables for devices and firmwares. |
| `device_simulator.py` | (Optional) A basic device simulator that can be used for initial testing. It lacks filesystem interaction and external script calls. |

## Features

- **RESTful API:** Endpoints to list devices, list firmwares, upload new firmware, and delete firmware.
- **Real-Time Communication:** Uses WebSockets for persistent connections, allowing the server to push updates to devices instantly.
- **Database Storage:** Persistently stores device and firmware data in a local SQLite database.
- **Decoupled Update Logic:** The device client delegates the actual update process to an external script, mimicking a production environment.
- **User-Friendly Management:** A rich CLI tool provides color-coded, tabular views of server data and simplifies management tasks.
- **Dependency-Free MAC Retrieval:** The device client uses Python's built-in modules to get the device's MAC address, avoiding extra dependencies.

## Installation

1.  **Clone or download the project files** into a single directory.

2.  **Install the required Python dependencies.** It is recommended to use a virtual environment.

    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

    # Install the necessary packages
    pip install flask websockets requests rich
    ```

## Usage Guide

Follow these steps to run the full system. Each command should be run in a separate terminal window.

### Step 1: Start the Server

First, launch the main server application. This will create the `suit_server.db` database file and the `firmware_files/` directory if they don't exist.

```bash
python3 suit_server.py
```

You should see output indicating that both the Flask and WebSocket servers have started successfully.

```
Flask API server started on [http://0.0.0.0:5000](http://0.0.0.0:5000)
WebSocket server started on ws://0.0.0.0:8765
Database initialized.
```

### Step 2: Start the Device Client

Next, start the client application. It will automatically determine its MAC address, read its current version from `version.info` (or create the file), and connect to the server.

```bash
python3 updater_client.py
```

The server terminal will show a "Device connected" message.

### Step 3: Manage the Server with the CLI

Now you can use the `server_cli.py` tool to interact with the server.

1.  **List Connected Devices:**
    See the status of the client you just started.

    ```bash
    python3 server_cli.py devices
    ```

2.  **Add New Firmware:**
    First, create a dummy binary file to act as your firmware. Then, use the `add` command to upload it.

    ```bash
    # Create a dummy firmware file
    echo "This is the binary payload for version 1.0.1" > my_firmware_v1.0.1.bin

    # Upload the firmware using the CLI
    python3 server_cli.py add my_firmware_v1.0.1.bin 1.0.1
    ```

    As soon as you run the `add` command, the server will detect the new firmware and push an update to the connected `updater_client`. Watch the client's terminal to see the download and installation process.

3.  **Check Status After Update:**
    Run the `devices` command again. You will see the device's version and status have been updated. The "success" status will be colored green.

    ```bash
    python3 server_cli.py devices
    ```

4.  **List Available Firmwares:**
    See a list of all firmwares you have uploaded.

    ```bash
    python3 server_cli.py firmwares
    ```

5.  **Delete a Firmware:**
    Use the ID from the firmware list to delete a firmware.

    ```bash
    # Assuming the firmware you added has an ID of 1
    python3 server_cli.py delete 1
    ```

## Testing Failure Scenarios

The `update_handler.py` script is designed to easily simulate update failures. To test this, rename your firmware file to include a specific flag before uploading it with the CLI tool.

-   **To simulate a verification failure:**
    -   File name: `firmware-fail-verify.bin`
    -   The handler will exit with code `102`.

-   **To simulate an installation failure:**
    -   File name: `firmware-fail-install.bin`
    -   The handler will exit with code `103`.

When you run `server_cli.py devices` after a failed update, the device's status will be shown in red (e.g., `failed:install_code_103`).
