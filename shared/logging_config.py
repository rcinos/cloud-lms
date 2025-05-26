# shared/logging_config.py
# This module provides a centralized function to configure structured logging
# using structlog, integrating with standard Python logging and potentially Azure Storage.

import logging
import structlog
from datetime import datetime
import json
import os
from azure.storage.blob import BlobServiceClient  # For Azure Blob Storage logging


# Define a custom processor for sending logs to Azure Blob Storage
# NOTE: This is a simplified example. For production, you'd typically use
# a more robust logging handler (e.g., Azure Monitor integration via OpenCensus/OpenTelemetry)
# or batch logs to reduce API calls.
class AzureBlobLogProcessor:
    def __init__(self, connection_string, container_name="olms-logs"):
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = None
        if self.connection_string:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                # Ensure the container exists
                container_client = self.blob_service_client.get_container_client(self.container_name)
                if not container_client.exists():
                    container_client.create_container()
                logging.info(f"Azure Blob Storage logging configured for container: {container_name}")
            except Exception as e:
                logging.error(f"Failed to initialize Azure Blob Storage client: {e}")
                self.blob_service_client = None  # Disable if initialization fails

    def __call__(self, logger, method_name, event_dict):
        if self.blob_service_client:
            try:
                # Create a unique blob name (e.g., service-name/YYYY-MM-DD/HH-MM-SS-UUID.json)
                service_name = event_dict.get('service', 'unknown-service')
                log_time = datetime.utcnow()
                blob_name = f"{service_name}/{log_time.strftime('%Y-%m-%d')}/{log_time.isoformat()}-{os.urandom(4).hex()}.json"

                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                log_entry = json.dumps(event_dict, default=str)  # Use default=str for non-serializable types
                blob_client.upload_blob(log_entry.encode('utf-8'), overwrite=True)
            except Exception as e:
                # Log error to console if Azure Storage upload fails
                logging.error(f"Failed to upload log to Azure Blob Storage: {e}", exc_info=True)
        return event_dict  # Always return event_dict for the next processor


def configure_logging(app):
    """
    Configures structured logging for the Flask application using structlog.
    Logs are output to the console and, if configured, to Azure Blob Storage.
    Args:
        app (Flask): The Flask application instance.
    """
    # 1. Configure standard Python logging
    logging.basicConfig(
        format="%(message)s",  # structlog takes care of formatting
        level=app.config.get('LOG_LEVEL', 'INFO'),
        handlers=[logging.StreamHandler()]  # Output to console
    )

    # 2. Suppress Azure SDK network logs in development mode
    # Only show them in production for debugging purposes
    is_production = not app.debug and app.config.get('ENV', '').lower() == 'production'

    if not is_production:
        # Suppress verbose Azure SDK logs in development
        azure_loggers = [
            'azure.core.pipeline.policies.http_logging_policy',
            'azure.storage.blob',
            'azure.storage.common',
            'azure.identity',
            'urllib3.connectionpool',
            'requests.packages.urllib3.connectionpool'
        ]

        for logger_name in azure_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    # 3. Configure structlog processors
    processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # Add ISO timestamp in UTC
        structlog.processors.StackInfoRenderer(),  # Add stack info on error/exception
        structlog.processors.format_exc_info,  # Format exception info
        structlog.processors.JSONRenderer() if not app.debug else structlog.dev.ConsoleRenderer(),
        # JSON for prod, pretty console for dev
    ]

    # Add Azure Blob Storage processor if connection string is available
    azure_storage_conn_str = app.config.get('AZURE_STORAGE_CONNECTION_STRING')
    if azure_storage_conn_str:
        azure_blob_processor = AzureBlobLogProcessor(azure_storage_conn_str)
        processors.insert(-1, azure_blob_processor)  # Insert before JSON/Console renderer

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )