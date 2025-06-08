#!/usr/bin/env python3
# course-service/run_tests.py
# Simple test runner script that ensures proper test environment setup

import os
import sys
import subprocess
from tests.test_config import setup_test_environment, cleanup_test_environment


def run_tests():
    """Run tests with proper environment setup."""
    print("Setting up test environment...")
    test_env_vars = setup_test_environment()

    try:
        print("Running tests...")
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
        cleanup_test_environment(test_env_vars)


if __name__ == '__main__':
    exit_code = run_tests()
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code {exit_code}")
    sys.exit(exit_code)