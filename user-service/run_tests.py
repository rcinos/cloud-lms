#!/usr/bin/env python3
# user-service/run_tests.py
# Simple test runner script that ensures proper test environment setup

import os
import sys
import subprocess
from cryptography.fernet import Fernet


def setup_test_environment():
    """Set up environment variables for testing."""
    # Generate a test encryption key
    # NOTE: For pytest, conftest.py's app fixture will set ENCRYPTION_KEY.
    # This setting here is primarily for running tests directly via this script
    # without pytest's fixtures, or for non-pytest scripts that need the key.
    # To avoid conflicts with pytest, we'll let conftest.py manage it for pytest runs.
    test_encryption_key = Fernet.generate_key().decode()

    test_env = {
        'TESTING': 'True',
        'DATABASE_URL_USER': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET': 'test-jwt-secret',
        'JWT_EXPIRATION_HOURS': '24',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        # 'ENCRYPTION_KEY': test_encryption_key # Removed this to avoid conflict with conftest.py
    }

    # Clear problematic environment variables
    problematic_vars = [
        'AZURE_SERVICE_BUS_CONNECTION_STRING',
        'AZURE_STORAGE_CONNECTION_STRING'
    ]

    for var in problematic_vars:
        if var in os.environ:
            del os.environ[var]

    # Set test environment variables
    for key, value in test_env.items():
        os.environ[key] = value

    # Explicitly set ENCRYPTION_KEY here if not running with pytest fixtures
    # This ensures that if `run_tests.py` is executed directly without pytest,
    # the encryption key is still available.
    if 'ENCRYPTION_KEY' not in os.environ:
        os.environ['ENCRYPTION_KEY'] = test_encryption_key


    return test_env


def cleanup_test_environment(test_env_vars):
    """Clean up test environment variables."""
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
    # Also clean up ENCRYPTION_KEY if it was set by this script
    if 'ENCRYPTION_KEY' in os.environ:
        del os.environ['ENCRYPTION_KEY']


def run_tests():
    """Run tests with proper environment setup."""
    print("Setting up test environment...")
    # Capture the environment variables set by setup_test_environment
    # so they can be cleaned up later.
    initial_env_keys = set(os.environ.keys())
    test_env_vars_set_by_script = setup_test_environment()
    new_env_keys = set(os.environ.keys()) - initial_env_keys


    try:
        print("Running tests...")
        # Run pytest with the arguments passed to this script
        cmd = [sys.executable, '-m', 'pytest'] + sys.argv[1:]

        # Add some default options if none provided
        if len(sys.argv) == 1:
            cmd.extend(['-v', '--tb=short'])

        # Pass a copy of the current environment variables to the subprocess
        result = subprocess.run(cmd, env=os.environ.copy())
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1
    finally:
        print("Cleaning up test environment...")
        # Clean up only the variables that were set by this script
        cleanup_test_environment(new_env_keys)

if __name__ == '__main__':
    sys.exit(run_tests())

