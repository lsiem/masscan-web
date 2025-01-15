import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
import dramatiq
from dramatiq.brokers.redis import RedisBroker

from .models.scan import Scan
from .routes import scan_routes

# Configure logging
def setup_logging(app: Flask) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "masscan_web.log"

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

# Configure Dramatiq
redis_broker = RedisBroker(host="localhost")
dramatiq.set_broker(redis_broker)

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.update(test_config)

    # Initialize extensions
    CORS(app, resources={r"/*": {"origins": "*"}})
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["100 per day", "10 per hour"]
    )

    # Setup logging
    setup_logging(app)

    # Initialize database
    Scan.init_db()

    # Register blueprints
    app.register_blueprint(scan_routes.bp)

    # Add security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    return app, socketio

app, socketio = create_app()
