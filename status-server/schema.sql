-- schema.sql
--
-- Defines the database schema for the SUIT server.

-- Table to store information about each connected device
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,          -- Unique device identifier (e.g., MAC address)
    last_ip TEXT NOT NULL,               -- Last known IP address of the device
    current_version TEXT,                -- Current firmware version on the device
    status TEXT NOT NULL,                -- Last reported status (e.g., 'connected', 'updating', 'success', 'failed')
    last_seen TIMESTAMP NOT NULL         -- Timestamp of the last communication
);

-- Table to store metadata about available firmware
CREATE TABLE IF NOT EXISTS firmwares (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique ID for the firmware
    file_name TEXT NOT NULL UNIQUE,      -- The name of the firmware file
    version TEXT NOT NULL UNIQUE,        -- The version string of the firmware (e.g., '1.0.1')
    hash TEXT NOT NULL,                  -- SHA-256 hash of the firmware file for integrity checks
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- When the firmware was added
);