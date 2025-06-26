# suit_server.py
#
# A SUIT compliant (RFC 9019) status and firmware update server.
# It uses Flask for API endpoints and WebSockets for real-time device communication.

import os
import sqlite3
import hashlib
import json
import asyncio
import threading
from datetime import datetime

from flask import Flask, request, jsonify, g
import websockets
from werkzeug.utils import secure_filename

# --- Configuration ---
DATABASE = 'suit_server.db'
UPLOAD_FOLDER = 'firmware_files'
ALLOWED_EXTENSIONS = {'bin', 'suit'}
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
WEBSOCKET_HOST = '0.0.0.0'
WEBSOCKET_PORT = 8765

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dictionary to hold active websocket connections for each device
# Key: device_id (MAC address), Value: websocket object
connected_clients = {}

# --- Database Utilities ---

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with app.app_context():
        db = get_db()
        with open('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    print("Database initialized.")

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Flask API Endpoints ---

@app.route('/devices', methods=['GET'])
def get_devices():
    """Lists all devices registered in the database."""
    db = get_db()
    cur = db.execute('SELECT device_id, last_ip, current_version, status, last_seen FROM devices')
    devices = [dict(row) for row in cur.fetchall()]
    return jsonify(devices)

@app.route('/devices/clear', methods=['DELETE'])
def clear_devices():
    """Deletes all devices from the database."""
    try:
        db = get_db()
        db.execute('DELETE FROM devices')
        db.commit()
        # Also clear the connected clients dictionary to prevent stale connections
        # Note: This doesn't close the connections, just removes them from tracking.
        # The connections will close on their own or when the server restarts.
        connected_clients.clear()
        print("All devices cleared from the database and active connections dictionary.")
        return jsonify({"success": "All devices have been cleared from the database."}), 200
    except Exception as e:
        print(f"Error clearing devices: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/firmwares', methods=['GET'])
def get_firmwares():
    """Lists all available firmwares in the database."""
    db = get_db()
    cur = db.execute('SELECT id, file_name, version, hash FROM firmwares')
    firmwares = [dict(row) for row in cur.fetchall()]
    return jsonify(firmwares)

@app.route('/add_firmware', methods=['POST'])
def add_firmware():
    """Adds a new firmware file to the server and database."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    version = request.form.get('version')
    if not version:
        return jsonify({"error": "Firmware version is required"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Calculate file hash (SHA-256)
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        file_hash = hasher.hexdigest()

        # Add to database
        try:
            db = get_db()
            db.execute(
                'INSERT INTO firmwares (file_name, version, hash) VALUES (?, ?, ?)',
                (filename, version, file_hash)
            )
            db.commit()

            # After adding new firmware, check connected clients for potential updates
            asyncio.run_coroutine_threadsafe(check_all_devices_for_updates(), websocket_loop)
            
            return jsonify({"success": f"Firmware '{filename}' uploaded successfully.", "hash": file_hash}), 201
        except sqlite3.IntegrityError:
            os.remove(filepath) # Clean up file if DB entry fails
            return jsonify({"error": "Firmware with this version or filename already exists."}), 409
        except Exception as e:
            os.remove(filepath) # Clean up
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "File type not allowed"}), 400

@app.route('/delete_firmware/<int:firmware_id>', methods=['DELETE'])
def delete_firmware(firmware_id):
    """Deletes a firmware from the database and the filesystem."""
    db = get_db()
    cur = db.execute('SELECT file_name FROM firmwares WHERE id = ?', (firmware_id,))
    firmware = cur.fetchone()
    
    if firmware is None:
        return jsonify({"error": "Firmware not found"}), 404

    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], firmware['file_name'])
        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete record from database
        db.execute('DELETE FROM firmwares WHERE id = ?', (firmware_id,))
        db.commit()
        
        return jsonify({"success": f"Firmware ID {firmware_id} deleted."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- WebSocket Server Logic ---

async def initiate_update(device_id, firmware_id):
    """Initiates the firmware update process for a specific device."""
    if device_id not in connected_clients:
        print(f"Update failed: Device {device_id} not connected.")
        return

    websocket = connected_clients[device_id]
    
    with app.app_context():
        db = get_db()
        firmware = db.execute('SELECT * FROM firmwares WHERE id = ?', (firmware_id,)).fetchone()
        if not firmware:
            print(f"Update failed: Firmware with ID {firmware_id} not found.")
            return

        firmware_path = os.path.join(app.config['UPLOAD_FOLDER'], firmware['file_name'])
        if not os.path.exists(firmware_path):
            print(f"Update failed: Firmware file {firmware['file_name']} not found.")
            return
            
        file_size = os.path.getsize(firmware_path)

        print(f"Initiating update for {device_id} to version {firmware['version']}")

        update_command = {
            "command": "update",
            "version": firmware['version'],
            "hash": firmware['hash'],
            "size": file_size
        }
        await websocket.send(json.dumps(update_command))

        with open(firmware_path, 'rb') as f:
            while chunk := f.read(4096):
                await websocket.send(chunk)
        
        print(f"Firmware {firmware['file_name']} sent to {device_id}")

async def check_device_for_updates(device_id, current_version):
    """Checks if a newer firmware is available for a device."""
    print(f"Checking for updates for {device_id} (current version: {current_version})")
    with app.app_context():
        db = get_db()
        latest_firmware = db.execute('SELECT * FROM firmwares ORDER BY id DESC LIMIT 1').fetchone()

        if latest_firmware and latest_firmware['version'] != current_version:
            print(f"New firmware version {latest_firmware['version']} found for {device_id}.")
            asyncio.create_task(initiate_update(device_id, latest_firmware['id']))
        else:
            print(f"Device {device_id} is up to date.")

async def check_all_devices_for_updates():
    """Iterates through all connected clients and checks for updates."""
    print("Checking all connected devices for pending updates...")
    connected_ids = list(connected_clients.keys())
    for device_id in connected_ids:
        with app.app_context():
            db = get_db()
            device_info = db.execute('SELECT current_version FROM devices WHERE device_id = ?', (device_id,)).fetchone()
            if device_info:
                await check_device_for_updates(device_id, device_info['current_version'])


async def handle_device_connection(websocket):
    """Handles a new WebSocket connection from a device."""
    device_id = None
    try:
        message = await websocket.recv()
        data = json.loads(message)
        device_id = data.get('device_id')
        current_version = data.get('current_version')
        client_ip = websocket.remote_address[0]

        if not device_id:
            await websocket.close(code=1008, reason="Device ID is required")
            return

        connected_clients[device_id] = websocket
        print(f"Device connected: {device_id} from {client_ip}")

        with app.app_context():
            db = get_db()
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            db.execute(
                """INSERT OR REPLACE INTO devices (device_id, last_ip, current_version, status, last_seen)
                   VALUES (?, ?, ?, ?, ?)""",
                (device_id, client_ip, current_version, 'connected', now)
            )
            db.commit()

        await check_device_for_updates(device_id, current_version)

        async for message in websocket:
            try:
                status_data = json.loads(message)
                if 'status' in status_data:
                    new_status = status_data['status']
                    new_version = status_data.get('version', current_version)
                    print(f"Received status from {device_id}: {new_status}")
                    
                    with app.app_context():
                        db = get_db()
                        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                        db.execute(
                            """UPDATE devices SET status = ?, current_version = ?, last_seen = ? 
                               WHERE device_id = ?""",
                            (new_status, new_version, now, device_id)
                        )
                        db.commit()
            except json.JSONDecodeError:
                print(f"Received non-JSON message from {device_id}: {message}")
            except Exception as e:
                print(f"Error processing status from {device_id}: {e}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection with {device_id or 'unknown device'} closed: {e.reason}")
    except Exception as e:
        print(f"An error occurred with {device_id or 'unknown device'}: {e}")
    finally:
        if device_id and device_id in connected_clients:
            del connected_clients[device_id]
            print(f"Device disconnected: {device_id}")
            with app.app_context():
                 db = get_db()
                 db.execute("UPDATE devices SET status = 'disconnected' WHERE device_id = ?", (device_id,))
                 db.commit()

# --- Main Execution ---

async def main():
    """Main async function to start the WebSocket server."""
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    
    server = await websockets.serve(handle_device_connection, WEBSOCKET_HOST, WEBSOCKET_PORT)
    print(f"WebSocket server started on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    await server.wait_closed()

if __name__ == '__main__':
    websocket_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(websocket_loop)

    flask_thread = threading.Thread(target=lambda: app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False))
    flask_thread.daemon = True
    flask_thread.start()
    print(f"Flask API server started on http://{FLASK_HOST}:{FLASK_PORT}")

    try:
        websocket_loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Servers shutting down.")
