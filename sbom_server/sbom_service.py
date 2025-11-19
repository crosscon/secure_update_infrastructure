import os
import subprocess
import json
import uuid
import base64
from fastapi import FastAPI, File, UploadFile
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from hashlib import sha256


app = FastAPI()

# Path of grype executable
GRYPE_PATH = "/usr/bin/grype"

# Directory to store temporary SBOM files
TEMP_DIR = "/tmp/sbom_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# Path of private key file (in PEM format)
PRIV_KEY = "/root/private_key.pem"

def scan_sbom_with_grype(sbom_path: str) -> dict:
    """
    Runs Grype on the given SBOM file and returns the parsed JSON output.
    """
    try:
        # Run Grype command and capture output
        result = subprocess.run(
            [GRYPE_PATH, sbom_path, "--add-cpes-if-none", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise Exception(e.stderr)

def sign_message(message: bytes) -> dict:
    """
    Sign a string using the server private key
    """
    with open(PRIV_KEY, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )

    sgn_bytes = private_key.sign(
        message,
        padding.PSS(
            mgf = padding.MGF1(algorithm = hashes.SHA256()),
            salt_length = padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    msg_b64 = base64.b64encode(message).decode("ascii")
    sgn_b64 = base64.b64encode(sgn_bytes).decode("ascii")

    return (msg_b64, sgn_b64)

    
@app.post("/verify-sbom")
async def verify_sbom(file: UploadFile = File(...)):
    """
    Endpoint to upload SBOM and return the number of vulnerabilities found.
    """
    try:
        # Save SBOM to a temporary file
        sbom_filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
        sbom_path = os.path.join(TEMP_DIR, sbom_filename)

        with open(sbom_path, "wb") as sbom_file:
            sbom_file.write(await file.read())

        # Calculate SHA-256 hash of the SBOM file
        with open(sbom_path, "rb") as sbom_file:
            sbom_data = sbom_file.read()
            sbom_hash = sha256(sbom_data).digest()

        # Scan SBOM using Grype
        vulnerabilities_report = scan_sbom_with_grype(sbom_path)

        # Clean up temporary file
        os.remove(sbom_path)

        # Extract and return the number of vulnerabilities
        if "matches" in vulnerabilities_report:
            vulnerability_count = len(vulnerabilities_report["matches"])
        else:
            vulnerability_count = 0

        report = sbom_hash + b"\x01" + vulnerability_count.to_bytes(4, byteorder="little")

    except Exception as e:
        report = sbom_hash + b"\x00" + str(e).encode()

    # Prepare and sign the report
    signed_report = sign_message(report)

    return f"{signed_report[0]}.{signed_report[1]}".encode()
