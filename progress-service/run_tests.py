#!/usr/bin/env python3
# progress-service/run_tests.py
# Test runner script for Progress Service

import os
import sys
import subprocess


def setup_test_environment():
    """Set up environment variables for testing."""
    test_env = {
        'TESTING': 'True',
        'DATABASE_URL_PROGRESS': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET': 'test-jwt-secret',
        'JWT_EXPIRATION_HOURS': '24',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        'USER_SERVICE_URL': 'http://test-user-service',
        'COURSE_SERVICE_URL': 'http://test-course-service'
    }

    # Clear problematic environment variables
    problematic_vars = [
        'AZURE_SERVICE_BUS_CONNECTION_STRING',
        'AZURE_STORAGE_CONNECTION_STRING',
        'APPLICATIONINSIGHTS_CONNECTION_STRING'
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


def run_tests():
    """Run tests with proper environment setup."""
    print("Setting up test environment...")
    initial_env_keys = set(os.environ.keys())
    test_env_vars_set = setup_test_environment()
    new_env_keys = set(os.environ.keys()) - initial_env_keys

    try:
        print("Running Progress Service tests...")
        # Run pytest with the arguments passed to this script
        cmd = [sys.executable, '-m', 'pytest'] + sys.argv[1:]

        # Add some default options if none provided
        if len(sys.argv) == 1:
            cmd.extend(['-v', '--tb=short'])

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
        cleanup_test_environment(new_env_keys)


if __name__ == '__main__':
    sys.exit(run_tests())
