# device_simulator.py
#
# A script to simulate an IoT device connecting to the SUIT server.
# It can report its status and receive firmware updates.

import asyncio
import websockets
import json
import hashlib
import time
import random

# --- Configuration ---
SERVER_URI = "ws://localhost:8765"
# Simulate different devices by changing the MAC address
DEVICE_ID = "DE:AD:BE:EF:" + ":".join([f"{random.randint(0, 255):02X}" for _ in range(2)])
INITIAL_VERSION = "1.0.0"

async def send_status(websocket, status, version):
    """Sends a status update to the server."""
    message = {"status": status, "version": version}
    await websocket.send(json.dumps(message))
    print(f"Sent status: {status}")

async def run_device():
    """Main function to run the device simulation."""
    current_version = INITIAL_VERSION
    
    async with websockets.connect(SERVER_URI) as websocket:
        # 1. Announce ourselves to the server
        print(f"Device {DEVICE_ID} connecting with version {current_version}...")
        initial_message = {
            "device_id": DEVICE_ID,
            "current_version": current_version
        }
        await websocket.send(json.dumps(initial_message))

        # 2. Main loop to listen for commands from the server
        while True:
            try:
                # Wait for a message from the server.
                message = await websocket.recv()

                # Check if the message is a JSON command or binary data
                if isinstance(message, str):
                    command_data = json.loads(message)
                    if command_data.get("command") == "update":
                        print("Received 'update' command.")
                        new_version = command_data['version']
                        expected_hash = command_data['hash']
                        file_size = command_data['size']
                        
                        # Start receiving the firmware file
                        await send_status(websocket, "downloading", current_version)
                        
                        received_data = bytearray()
                        bytes_received = 0
                        while bytes_received < file_size:
                            chunk = await websocket.recv()
                            received_data.extend(chunk)
                            bytes_received += len(chunk)
                            print(f"Downloading... {bytes_received}/{file_size} bytes")

                        print("Download complete. Verifying hash...")
                        
                        # Verify integrity
                        actual_hash = hashlib.sha256(received_data).hexdigest()
                        
                        if actual_hash == expected_hash:
                            print("Hash verification successful.")
                            await send_status(websocket, "installing", current_version)
                            time.sleep(3) # Simulate installation time
                            
                            # Simulate a random chance of failure
                            if random.random() > 0.1: # 90% success rate
                                current_version = new_version
                                await send_status(websocket, "success", current_version)
                                print(f"Update to version {current_version} successful!")
                            else:
                                await send_status(websocket, "failed:install", current_version)
                                print("Simulated installation failure.")

                        else:
                            print(f"Hash mismatch! Expected {expected_hash}, got {actual_hash}")
                            await send_status(websocket, "failed:hash", current_version)
                
            except websockets.exceptions.ConnectionClosed:
                print("Connection to server closed.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break

if __name__ == "__main__":
    try:
        asyncio.run(run_device())
    except KeyboardInterrupt:
        print("\nDevice simulator stopped.")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running at {SERVER_URI}?")
