# update_handler.py
#
# A placeholder script that simulates a real firmware update application.
# It is called by updater_client.py.
#
# - It accepts the path to the firmware file as a command-line argument.
# - It exits with a code of 0 for success and a non-zero code for failure.

import sys
import time
import random

def main():
    """Main function for the handler script."""
    print("[Handler] Starting firmware update process.")

    if len(sys.argv) < 2:
        print("[Handler] ERROR: No firmware file path provided.")
        sys.exit(101) # Exit code for missing argument

    firmware_file = sys.argv[1]
    print(f"[Handler] Received firmware file: {firmware_file}")

    # 1. Simulate verification
    print("[Handler] Verifying firmware integrity...")
    time.sleep(1)
    if "-fail-verify" in firmware_file:
        print("[Handler] ERROR: Firmware verification failed (simulated).")
        sys.exit(102) # Exit code for verification failure
    print("[Handler] Verification successful.")
    
    # 2. Simulate installation
    print("[Handler] Applying update...")
    time.sleep(2)
    if "-fail-install" in firmware_file:
        print("[Handler] ERROR: Firmware installation failed (simulated).")
        sys.exit(103) # Exit code for installation failure
    print("[Handler] Installation successful.")
    
    # 3. Simulate a final random failure chance
    if random.random() < 0.1: # 10% chance of a random failure
        print("[Handler] ERROR: A random post-install error occurred (simulated).")
        sys.exit(200)

    print("[Handler] Update process completed successfully.")
    sys.exit(0) # Exit with 0 to indicate success

if __name__ == "__main__":
    main()
