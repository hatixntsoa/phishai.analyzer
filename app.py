from routes.main import main as main_blueprint
from api.predictor import app as fastapi_app
from flask import Flask

import threading
import uvicorn
import time

import socket


def is_port_in_use(port: int = 8000, host: str = "127.0.0.1") -> bool:
    """Check if something is already listening on the port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

def run_fastapi():
    if is_port_in_use(8000):
        print("PhishAI Backend API already running on http://0.0.0.0:8000")
        return

    print("Starting PhishAI Backend API on http://0.0.0.0:8000 ...")

    def start_uvicorn():
        uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="error")

    thread = threading.Thread(target=start_uvicorn, daemon=True)
    thread.start()
    time.sleep(2)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config.Config')
    app.register_blueprint(main_blueprint)
    return app

if __name__ == "__main__":
    run_fastapi()
    flask_app = create_app()

    print("Starting PhishAI Analyzer on http://localhost:6047")
    flask_app.run(
        host="0.0.0.0",
        port=6047,
        debug=False,
        use_reloader=False
    )
