# progress-service/app/__init__.py
# This file initializes the Flask application and its extensions for the Progress Service.
# Simplified to match user service approach (no OpenTelemetry/Application Insights)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from config import Config  # Import configuration settings
import structlog  # For structured logging
import logging  # Standard Python logging
from shared.logging_config import configure_logging  # Custom logging setup

db = SQLAlchemy()  # Database ORM instance
migrate = Migrate()  # Database migration instance
cache = Cache()  # Caching instance
logger = structlog.get_logger()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Load configuration from Config class

    # Configure logging using the shared utility
    configure_logging(app)

    # Initialize Flask extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    # Import and register blueprints (routes)
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Import and register Flask CLI commands for background tasks (e.g., message consumption)
    from app.commands import consume_progress_events_command
    app.cli.add_command(consume_progress_events_command)

    return app