# course-service/tests/test_config.py
# Test-specific configuration that overrides the main config

import os
import tempfile
from unittest.mock import patch, MagicMock


class TestConfig:
    """Configuration for testing."""

    # Flask settings
    TESTING = True
    SECRET_KEY = 'test-secret-key'

    # Database settings - use SQLite for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_SECRET = 'test-jwt-secret'
    JWT_EXPIRATION_HOURS = 24

    # Cache settings - disable caching for tests
    CACHE_TYPE = 'NullCache'
    CACHE_REDIS_URL = None

    # Azure services - disable for tests
    AZURE_STORAGE_CONNECTION_STRING = None
    AZURE_SERVICE_BUS_CONNECTION_STRING = None
    APPLICATIONINSIGHTS_CONNECTION_STRING = None

    # Encryption key for tests (32-byte URL-safe base64-encoded key)
    ENCRYPTION_KEY = 'test-encryption-key-32-bytes-long-12345'

    # Logging
    LOG_LEVEL = 'ERROR'  # Reduce log noise during tests

    # External services
    USER_SERVICE_URL = 'http://test-user-service'


def setup_test_environment():
    """Set up environment variables for testing."""
    test_env = {
        'TESTING': 'True',
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL_COURSE': 'sqlite:///:memory:',
        'JWT_SECRET': 'test-jwt-secret',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        'USER_SERVICE_URL': 'http://test-user-service',
        'ENCRYPTION_KEY': 'test-encryption-key-32-bytes-long-12345'
    }

    # Clear problematic environment variables
    problematic_vars = [
        'AZURE_SERVICE_BUS_CONNECTION_STRING',
        'APPLICATIONINSIGHTS_CONNECTION_STRING',
        'AZURE_STORAGE_CONNECTION_STRING'
    ]

    for var in problematic_vars:
        if var in os.environ:
            del os.environ[var]

    # Set test environment variables
    for key, value in test_env.items():
        os.environ[key] = value

    return test_env


def cleanup_test_environment(test_env_vars):
    """Clean up test environment variables."""
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


def mock_shared_modules():
    """Create patches for shared modules that require Azure services."""
    patches = []

    # Mock message queue functions
    mock_publish = patch('shared.message_queue.publish_message')
    mock_consume = patch('shared.message_queue.consume_messages')
    patches.extend([mock_publish, mock_consume])

    # Mock Azure blob logging processor
    mock_blob_processor = patch('shared.logging_config.AzureBlobLogProcessor')
    patches.append(mock_blob_processor)

    # Start all patches
    mocks = {}
    for p in patches:
        mock_obj = p.start()
        mocks[p.attribute] = mock_obj

    return mocks, patches


def cleanup_mocks(patches):
    """Clean up mock patches."""
    for p in patches:
        p.stop()