import os
import subprocess
import json
import uuid
from fastapi import FastAPI, File, UploadFile

app = FastAPI()

# Directory to store temporary SBOM files
TEMP_DIR = "/tmp/sbom_files"
os.makedirs(TEMP_DIR, exist_ok=True)

def scan_sbom_with_grype(sbom_path: str) -> dict:
    """
    Runs Grype on the given SBOM file and returns the parsed JSON output.
    """
    try:
        # Run Grype command and capture output
        result = subprocess.run(
            ["/root/bin/grype", sbom_path, "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {"error": f"Grype scan failed: {e.stderr}"}

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

        # Scan SBOM using Grype
        vulnerabilities_report = scan_sbom_with_grype(sbom_path)

        # Clean up temporary file
        os.remove(sbom_path)

        # Extract and return the number of vulnerabilities
        if "matches" in vulnerabilities_report:
            vulnerability_count = len(vulnerabilities_report["matches"])
        else:
            vulnerability_count = 0

        return {"status": "success", "vulnerability_count": vulnerability_count}

    except Exception as e:
        return {"status": "error", "message": str(e)}
