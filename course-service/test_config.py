# course-service/test_config.py
"""Test-specific configuration that overrides the main config."""


class TestConfig:
    """Configuration for testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = 'test_secret_key_for_testing'
    JWT_EXPIRATION_HOURS = 24
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    USER_SERVICE_URL = 'http://mock-user-service'

    # Disable all external services
    APPLICATIONINSIGHTS_CONNECTION_STRING = None
    AZURE_STORAGE_ACCOUNT_NAME = None
    AZURE_STORAGE_ACCOUNT_KEY = None
    SERVICE_BUS_CONNECTION_STR = None

    # Flask settings
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'