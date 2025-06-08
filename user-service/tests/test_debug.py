#!/usr/bin/env python3
# user-service/quick_test.py
# Quick test to verify the core functionality works

import os
import sys
from cryptography.fernet import Fernet


def setup_test_env():
    """Set up test environment."""
    test_encryption_key = Fernet.generate_key().decode()

    os.environ.update({
        'TESTING': 'True',
        'DATABASE_URL_USER': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET': 'test-jwt-secret',
        'JWT_EXPIRATION_HOURS': '24',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        'ENCRYPTION_KEY': test_encryption_key
    })

    # Clear Azure variables
    for var in ['AZURE_SERVICE_BUS_CONNECTION_STRING', 'AZURE_STORAGE_CONNECTION_STRING']:
        os.environ.pop(var, None)


def test_core_functionality():
    """Test the core functionality that was failing."""
    setup_test_env()

    # Add current directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from app import create_app, db
    from unittest.mock import patch

    app = create_app()

    with app.app_context():
        db.create_all()

        print("=" * 50)
        print("TESTING CORE FUNCTIONALITY")
        print("=" * 50)

        # Test 1: User Creation and Lookup
        print("\n1. Testing User Creation and Lookup")
        from app.services import UserService

        service = UserService()
        user_data = {
            'email': 'test@example.com',
            'password': 'TestPass123',
            'user_type': 'student'
        }

        # Create user
        user = service.create_user(user_data)
        print(f"✅ User created: ID={user.id}, Email={user.get_email()}")

        # Test lookup
        found_user = service.get_user_by_email('test@example.com')
        if found_user:
            print(f"✅ User found: ID={found_user.id}, Email={found_user.get_email()}")
        else:
            print("❌ User NOT found")
            return False

        # Test duplicate prevention
        try:
            duplicate = service.create_user(user_data)
            print("❌ Duplicate user created - this should NOT happen")
            return False
        except ValueError as e:
            print(f"✅ Duplicate prevention works: {e}")

        # Test 2: Authentication
        print("\n2. Testing Authentication")
        from app.services import AuthService

        auth_service = AuthService()
        token = auth_service.authenticate_user('test@example.com', 'TestPass123')

        if token:
            print(f"✅ Authentication successful")

            # Verify token
            import jwt
            decoded = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            print(f"✅ Token contains: user_id={decoded['user_id']}, email={decoded['email']}")
        else:
            print("❌ Authentication failed")
            return False

        # Test 3: API Endpoints
        print("\n3. Testing API Endpoints")

        with patch('app.routes.publish_message'):
            client = app.test_client()

            # Test registration
            response = client.post('/auth/register',
                                   json={
                                       'email': 'api@example.com',
                                       'password': 'ApiPass123',
                                       'user_type': 'instructor'
                                   })

            if response.status_code == 201:
                print("✅ Registration endpoint works")
                user_data = response.get_json()

                # Test login
                response = client.post('/auth/login',
                                       json={
                                           'email': 'api@example.com',
                                           'password': 'ApiPass123'
                                       })

                if response.status_code == 200:
                    print("✅ Login endpoint works")
                    login_data = response.get_json()

                    if 'token' in login_data:
                        print("✅ Token returned in login response")
                    else:
                        print("❌ No token in login response")
                        return False
                else:
                    print(f"❌ Login failed: {response.status_code}")
                    return False

                # Test duplicate registration
                response = client.post('/auth/register',
                                       json={
                                           'email': 'api@example.com',
                                           'password': 'ApiPass123',
                                           'user_type': 'instructor'
                                       })

                if response.status_code == 400:
                    print("✅ Duplicate registration prevented")
                else:
                    print(f"❌ Duplicate registration not prevented: {response.status_code}")
                    return False

            else:
                print(f"❌ Registration failed: {response.status_code}")
                return False

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED! 🎉")
        print("=" * 50)
        return True


if __name__ == '__main__':
    success = test_core_functionality()
    sys.exit(0 if success else 1)