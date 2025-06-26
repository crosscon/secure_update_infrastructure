from flask import Flask, send_from_directory, abort
from werkzeug.utils import safe_join
import threading
import os

FIRMWARE_DIR = "./firmware"

app = Flask(__name__)

@app.route('/<path:filename>')
def serve_file(filename):
    safe_path = safe_join(FIRMWARE_DIR, filename)
    if safe_path is None or not os.path.isfile(safe_path) or os.path.islink(safe_path):
        abort(404)
    return send_from_directory(FIRMWARE_DIR, filename, as_attachment=True)

@app.route('/')
def list_files():
    files = os.listdir(FIRMWARE_DIR)
    links = [f'<a href="/{f}">{f}</a>' for f in files if os.path.isfile(os.path.join(FIRMWARE_DIR, f))]
    return "<h1>Firmware files:</h1>" + "<br>".join(links)

def run_http():
    app.run(host="0.0.0.0", port=80)

def run_https():
    ssl_context = ('cert.pem', 'key.pem')
    app.run(host="0.0.0.0", port=443, ssl_context=ssl_context)

if __name__ == '__main__':
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    # Start HTTP and HTTPS servers in separate threads
    t_http = threading.Thread(target=run_http)
    t_https = threading.Thread(target=run_https)
    t_http.start()
    t_https.start()
    t_http.join()
    t_https.join()
