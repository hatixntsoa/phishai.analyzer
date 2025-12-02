from routes.main import main as main_blueprint
from api.predictor import app as fastapi_app
from flask import Flask

import threading
import uvicorn
import time

def run_fastapi():
    print("Starting FastAPI predictor API on http://0.0.0.0:8000 ...")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="error")

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config.Config')

    app.register_blueprint(main_blueprint)

    return app

if __name__ == '__main__':
    threading.Thread(target=run_fastapi, daemon=True).start()
    time.sleep(2)

    print("Starting Flask frontend on http://0.0.0.0:6047 ...")
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=6047, use_reloader=False)
