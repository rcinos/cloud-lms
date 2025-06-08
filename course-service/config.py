# course-service/config.py
# This file defines the configuration settings for the Course Service.
# It loads sensitive information from environment variables, which are typically
# sourced from a .env file in development or Kubernetes Secrets/Azure Key Vault in production.

import os


class Config:
    # Flask's SECRET_KEY for session management and other security features.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-course-secret-key-flask')

    # --- Database Configuration ---
    # Directly use the complete database URL from the environment variable.
    # Provides a default for local development if the env var is not set.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_COURSE',
                                             'postgresql://user:password@localhost:5433/course_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppresses a warning from Flask-SQLAlchemy

    # --- JWT Configuration ---
    # Secret key for signing and verifying JSON Web Tokens.
    # This should ideally be the same as the JWT_SECRET used by the User Service for validation.
    JWT_SECRET = os.environ.get('JWT_SECRET', None)
    # Expiration time for JWT tokens in hours (used for validation, not generation here).
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', 24))

    # --- Cache Configuration (Redis) ---
    # Type of caching backend to use.
    CACHE_TYPE = "RedisCache"
    # URL for the Redis instance.
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')  # Using database 0 for Course Service

    # --- Azure Integration Configurations ---
    # Connection string for Azure Storage Account, used for logging or file storage.
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    # Connection string for Azure Service Bus, used for inter-service communication.
    AZURE_SERVICE_BUS_CONNECTION_STRING = os.environ.get('AZURE_SERVICE_BUS_CONNECTION_STRING')

    # --- Application Insights Configuration ---
    APPLICATIONINSIGHTS_CONNECTION_STRING = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')

    # --- Logging Configuration ---
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # --- User Service URL (for inter-service communication, e.g., validating instructor ID) ---
    USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://localhost:5002')
