import os
import subprocess
import uuid
import base64
import gzip
from fastapi import FastAPI, File, UploadFile
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from hashlib import sha256


app = FastAPI()

# Path of ethos launcher
ETHOS_PATH = "/opt/ethos/"
ETHOS_SCRIPT = os.path.join(ETHOS_PATH, "ethos")

# Timeout (in seconds) for ethos subprocess
TIMEOUT = 3600    # 1 hour

# Path of private key file (in PEM format)
PRIV_KEY = "/root/private_key.pem"

def verify_proof_certificate(proof_path: str) -> dict:
    """
    Runs Ethos on the given proof certificate and returns the parsed JSON output.
    """
    try:
        # Run Ethos command and capture output
        result = subprocess.run(
            [ETHOS_SCRIPT, proof_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=TIMEOUT
         )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise Exception(e.stderr)
    except subprocess.TimeoutExpired as e:
        raise Exception("Proof checker timeout")

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

    
@app.post("/verify-proof")
async def verify_proof(file: UploadFile = File(...)):
    """
    Endpoint to upload a proof certificate and return the result of checker
    """
    try:
        # Read uploaded bytes
        uploaded_bytes = await file.read()

        # Compute the SHA-256 hash of the uploaded proof
        proof_hash = sha256(uploaded_bytes).digest()

        try:
            decompressed = gzip.decompress(uploaded_bytes)
        except OSError as e:
            raise Exception(f"Invalid gzip archive: {e}")

        proof_filename = f"{uuid.uuid4()}.cpc"
        proof_path = os.path.join(ETHOS_PATH, proof_filename)

        with open(proof_path, "wb") as proof_file:
            proof_file.write(decompressed)

        # Check proof certificate
        pc_result = verify_proof_certificate(proof_path)
        # If no exception is raised, the certificate has been verified correctly
        # Note: here we could parse ethos output to identify trust steps

        report = proof_hash + b"\x01"

        # Clean up temporary file
        os.remove(proof_path)

    except Exception as e:
        report = proof_hash + b"\x00" + str(e).encode()

    # Prepare and sign the report
    signed_report = sign_message(report)

    return f"{signed_report[0]}.{signed_report[1]}"
