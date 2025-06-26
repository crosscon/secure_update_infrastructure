# SBOM Service

This project provides an API service for Software Bill of Materials (SBOM) processing.

## Installation

### 1. Install Grype

Grype is required for vulnerability scanning.  
Install it using the following command:

```bash
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sudo sh
```

### 2. Install Python Libraries

Install the required Python dependencies:

```bash
pip install fastapi uvicorn python-multipart
```

# Running the API
You can start the API service with:

```bash
uvicorn sbom_service:app --reload --host 10.200.10.10
```
