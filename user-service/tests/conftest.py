# user-service/tests/conftest.py
# Test configuration and fixtures for the User Service test suite.

import pytest
import os
import uuid
import tempfile
from unittest.mock import patch
from app import create_app, db
from app.models import User, UserProfile, Enrollment
import jwt
import time
from cryptography.fernet import Fernet


# Patch shared modules at import time to avoid 500 errors
@pytest.fixture(scope='session', autouse=True)
def setup_mocks():
    """Set up mocks for shared modules before any tests run."""
    with patch('shared.message_queue.publish_message') as mock_publish, \
            patch('shared.message_queue.consume_messages') as mock_consume, \
            patch('shared.logging_config.AzureBlobLogProcessor'), \
            patch('app.routes.publish_message') as mock_routes_publish:
        mock_publish.return_value = None
        mock_consume.return_value = None
        mock_routes_publish.return_value = None

        yield


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    # Generate a test encryption key (32-byte URL-safe base64-encoded)
    test_encryption_key = Fernet.generate_key().decode()

    # Set environment variables before creating app
    os.environ.update({
        'TESTING': 'True',
        'DATABASE_URL_USER': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET': 'test-jwt-secret',
        'JWT_EXPIRATION_HOURS': '24',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        'ENCRYPTION_KEY': test_encryption_key
    })

    # Clear Azure service environment variables
    for var in ['AZURE_SERVICE_BUS_CONNECTION_STRING', 'AZURE_STORAGE_CONNECTION_STRING']:
        os.environ.pop(var, None)

    try:
        app = create_app()
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    finally:
        # Clean up
        os.close(db_fd)
        os.unlink(db_path)

        # Clean up environment variables
        test_vars = ['TESTING', 'DATABASE_URL_USER', 'SECRET_KEY', 'JWT_SECRET',
                     'JWT_EXPIRATION_HOURS', 'CACHE_TYPE', 'LOG_LEVEL', 'ENCRYPTION_KEY']
        for var in test_vars:
            os.environ.pop(var, None)


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean database before each test."""
    with app.app_context():
        # Clean up any existing data in reverse order due to foreign keys
        Enrollment.query.delete()
        UserProfile.query.delete()
        User.query.delete()
        db.session.commit()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        'email': f'test{unique_id}@example.com',
        'password': 'TestPassword123',
        'user_type': 'student',
        'first_name': 'Test',
        'last_name': 'User',
        'phone': '123-456-7890',
        'bio': 'Test user biography'
    }


@pytest.fixture
def sample_instructor_data():
    """Sample instructor data for testing."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        'email': f'instructor{unique_id}@example.com',
        'password': 'InstructorPass123',
        'user_type': 'instructor',
        'first_name': 'Test',
        'last_name': 'Instructor',
        'bio': 'Test instructor biography'
    }


@pytest.fixture
def sample_enrollment_data():
    """Sample enrollment data for testing."""
    return {
        'user_id': 1,
        'course_id': 101
    }


@pytest.fixture
def valid_user_token(app):
    """Generate a valid student JWT token for testing."""
    with app.app_context():
        payload = {
            'user_id': 1,
            'email': 'test@example.com',
            'user_type': 'student',
            'exp': int(time.time()) + 3600  # 1 hour from now
        }
        token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
        return f'Bearer {token}'


@pytest.fixture
def valid_instructor_token(app):
    """Generate a valid instructor JWT token for testing."""
    with app.app_context():
        payload = {
            'user_id': 2,
            'email': 'instructor@example.com',
            'user_type': 'instructor',
            'exp': int(time.time()) + 3600  # 1 hour from now
        }
        token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
        return f'Bearer {token}'


@pytest.fixture
def expired_token(app):
    """Generate an expired JWT token for testing."""
    with app.app_context():
        payload = {
            'user_id': 1,
            'email': 'test@example.com',
            'user_type': 'student',
            'exp': int(time.time()) - 3600  # 1 hour ago (expired)
        }
        token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
        return f'Bearer {token}'


@pytest.fixture
def sample_user(app, sample_user_data):
    """Create a sample user in the database."""
    with app.app_context():
        from app.services import UserService
        user_service = UserService()
        user = user_service.create_user(sample_user_data)

        # Create a simple mock object with the essential data
        class MockUser:
            def __init__(self, user_id, email, user_type, password):
                self.id = user_id
                self.email = email
                self.user_type = user_type
                self.password = password  # Store the plain password for testing

            def to_dict(self, include_email=False):
                result = {
                    'id': self.id,
                    'user_type': self.user_type,
                    'is_active': True
                }
                if include_email:
                    result['email'] = self.email
                return result

        yield MockUser(user.id, sample_user_data['email'], sample_user_data['user_type'], sample_user_data['password'])


@pytest.fixture
def sample_instructor(app, sample_instructor_data):
    """Create a sample instructor in the database."""
    with app.app_context():
        from app.services import UserService
        user_service = UserService()
        instructor = user_service.create_user(sample_instructor_data)

        class MockInstructor:
            def __init__(self, user_id, email, user_type, password):
                self.id = user_id
                self.email = email
                self.user_type = user_type
                self.password = password

            def to_dict(self, include_email=False):
                result = {
                    'id': self.id,
                    'user_type': self.user_type,
                    'is_active': True
                }
                if include_email:
                    result['email'] = self.email
                return result

        yield MockInstructor(instructor.id, sample_instructor_data['email'], sample_instructor_data['user_type'],
                             sample_instructor_data['password'])


@pytest.fixture
def sample_enrollment(app, sample_user, sample_enrollment_data):
    """Create a sample enrollment in the database."""
    with app.app_context():
        enrollment_data = sample_enrollment_data.copy()
        enrollment_data['user_id'] = sample_user.id

        enrollment = Enrollment(**enrollment_data)
        db.session.add(enrollment)
        db.session.commit()

        enrollment_id = enrollment.id

        class MockEnrollment:
            def __init__(self, enrollment_id, user_id, course_id):
                self.id = enrollment_id
                self.user_id = user_id
                self.course_id = course_id
                self.status = 'active'

            def to_dict(self):
                return {
                    'id': self.id,
                    'user_id': self.user_id,
                    'course_id': self.course_id,
                    'status': self.status
                }

        yield MockEnrollment(enrollment_id, sample_user.id, enrollment_data['course_id'])