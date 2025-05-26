# progress-service/app/__init__.py
# This file initializes the Flask application and its extensions for the Progress Service.

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from config import Config  # Import configuration settings
import structlog  # For structured logging
import logging  # Standard Python logging
from shared.logging_config import configure_logging  # Custom logging setup

# New imports for OpenTelemetry and Azure Monitor
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

db = SQLAlchemy()  # Database ORM instance
migrate = Migrate()  # Database migration instance
cache = Cache()  # Caching instance
logger = structlog.get_logger()  # Global logger instance


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Load configuration from Config class

    # Configure logging using the shared utility
    configure_logging(app)

    # --- Configure OpenTelemetry and Application Insights ---
    if app.config.get('APPLICATIONINSIGHTS_CONNECTION_STRING'):
        resource = Resource.create({
            SERVICE_NAME: "progress-service"  # Service name for Application Insights
        })

        exporter = AzureMonitorTraceExporter(
            connection_string=app.config['APPLICATIONINSIGHTS_CONNECTION_STRING']
        )

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument Flask, Requests, and SQLAlchemy for automatic tracing
        FlaskInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()  # Instrument the 'requests' library for outgoing HTTP calls
        SQLAlchemyInstrumentor().instrument(engine=db.engine)  # Instrument SQLAlchemy for database calls

        logger.info("Application Insights instrumentation configured.")
    else:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set. Application Insights will not be enabled.")

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
