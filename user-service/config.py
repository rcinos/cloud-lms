# user-service/config.py
# This file defines the configuration settings for the User Service.
# It loads sensitive information from environment variables, which are typically
# sourced from a .env file in development or Kubernetes Secrets/Azure Key Vault in production.

import os
from urllib.parse import quote_plus  # Used for URL encoding database passwords


class Config:
    # Flask's SECRET_KEY for session management and other security features.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-flask')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    IS_PRODUCTION = (FLASK_ENV == 'production') or (FLASK_ENV == 'staging')

    # --- Database Configuration ---
    # Directly use the complete database URL from the environment variable.
    # This is more robust as it allows for complex connection strings.
    # Provides a default for local development if the env var is not set.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_USER', 'postgresql://user:password@localhost:5434/user_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppresses a warning from Flask-SQLAlchemy

    # --- JWT Configuration ---
    # Secret key for signing and verifying JSON Web Tokens.
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-key')
    # Expiration time for JWT tokens in hours.
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))

    # --- Cache Configuration (Redis) ---
    # Type of caching backend to use.
    CACHE_TYPE = "RedisCache"
    # URL for the Redis instance.
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')

    # --- Encryption Key for PII Data ---
    # Key used by the shared encryption utility to encrypt/decrypt PII.
    # This must be a 32-byte URL-safe base64-encoded key for Fernet.
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

    # --- Azure Integration Configurations ---
    # Connection string for Azure Storage Account, used for logging or file storage.
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    # Connection string for Azure Service Bus, used for inter-service communication.
    AZURE_SERVICE_BUS_CONNECTION_STRING = os.environ.get('AZURE_SERVICE_BUS_CONNECTION_STRING')

    # --- Logging Configuration ---
    # Log level for structlog and standard Python logging.
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    if FLASK_ENV == 'development' and LOG_LEVEL == 'INFO': # Only default to DEBUG if not explicitly set to INFO or higher
        LOG_LEVEL = 'DEBUG'