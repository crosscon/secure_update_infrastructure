# Verification server

This project provides a minimal implementation of a verification server.

## Steps for setting up the server

1. Install Python dependencies:
   ```bash
   pip install fastapi uvicorn python-multipart
   ```

2. Install proof checkers:
   * ethos: see instructions at https://github.com/cvc5/ethos

3. Run the service:
   ```bash
   uvicorn verif_service:app --reload --host <ip address>
   ```
   replacing `<ip address>` with the appropriate value


