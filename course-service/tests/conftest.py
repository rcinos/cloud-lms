# course-service/tests/conftest.py
# Test configuration and fixtures for the Course Service test suite.

import pytest
import os
import uuid
import tempfile
from unittest.mock import patch
from app import create_app, db
from app.models import Course, CourseModule, Assessment
import jwt
import time


# Patch shared modules at import time to avoid 500 errors
@pytest.fixture(scope='session', autouse=True)
def setup_mocks():
    """Set up mocks for shared modules before any tests run."""
    with patch('shared.message_queue.publish_message') as mock_publish, \
            patch('shared.message_queue.consume_messages') as mock_consume, \
            patch('shared.logging_config.AzureBlobLogProcessor'), \
            patch('requests.get') as mock_requests_get:
        mock_publish.return_value = None
        mock_consume.return_value = None

        # Create a proper mock response class
        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {'user_type': 'instructor'}

            def raise_for_status(self):
                pass

        mock_requests_get.return_value = MockResponse()

        yield


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    # Create a temporary file for the database
    import tempfile
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    # Set environment variables before creating app
    os.environ.update({
        'TESTING': 'True',
        'DATABASE_URL_COURSE': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET': 'test-jwt-secret',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        'USER_SERVICE_URL': 'http://test-user-service',
        'ENCRYPTION_KEY': 'dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcy1sb25nLTEyMzQ1'  # base64 encoded test key
    })

    # Clear Azure service environment variables
    for var in ['AZURE_SERVICE_BUS_CONNECTION_STRING', 'APPLICATIONINSIGHTS_CONNECTION_STRING',
                'AZURE_STORAGE_CONNECTION_STRING']:
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
        test_vars = ['TESTING', 'DATABASE_URL_COURSE', 'SECRET_KEY', 'JWT_SECRET', 'CACHE_TYPE', 'LOG_LEVEL',
                     'USER_SERVICE_URL', 'ENCRYPTION_KEY']
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
        Assessment.query.delete()
        CourseModule.query.delete()
        Course.query.delete()
        db.session.commit()


@pytest.fixture
def sample_course_data():
    """Sample course data for testing."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        'title': f'Test Course {unique_id}',
        'description': 'This is a test course description',
        'instructor_id': 1
    }


@pytest.fixture
def sample_module_data():
    """Sample module data for testing."""
    return {
        'title': 'Test Module',
        'content': 'This is test module content',
        'order_index': 1
    }


@pytest.fixture
def sample_assessment_data():
    """Sample assessment data for testing."""
    return {
        'title': 'Test Assessment',
        'description': 'This is a test assessment',
        'max_score': 100
    }


@pytest.fixture
def instructor_token(app):
    """Generate a valid instructor JWT token for testing."""
    with app.app_context():
        payload = {
            'user_id': 1,
            'user_type': 'instructor',
            'exp': int(time.time()) + 3600  # 1 hour from now
        }
        token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
        return f'Bearer {token}'


@pytest.fixture
def student_token(app):
    """Generate a valid student JWT token for testing."""
    with app.app_context():
        payload = {
            'user_id': 2,
            'user_type': 'student',
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
            'user_type': 'instructor',
            'exp': int(time.time()) - 3600  # 1 hour ago (expired)
        }
        token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')
        return f'Bearer {token}'


@pytest.fixture
def sample_course(app, sample_course_data):
    """Create a sample course in the database."""
    with app.app_context():
        course = Course(**sample_course_data)
        db.session.add(course)
        db.session.commit()

        # Return course data as a simple object with necessary methods
        course_id = course.id
        course_data = course.to_dict()

        class MockCourse:
            def __init__(self, data, course_id):
                self.id = course_id
                self.title = data['title']
                self.description = data['description']
                self.instructor_id = data['instructor_id']
                self._data = data

            def to_dict(self):
                return self._data

        yield MockCourse(course_data, course_id)


@pytest.fixture
def sample_module(app, sample_course, sample_module_data):
    """Create a sample module in the database."""
    with app.app_context():
        module_data = sample_module_data.copy()
        module_data['course_id'] = sample_course.id
        module = CourseModule(**module_data)
        db.session.add(module)
        db.session.commit()

        module_id = module.id
        module_dict = module.to_dict()

        class MockModule:
            def __init__(self, data, module_id):
                self.id = module_id
                self.course_id = data['course_id']
                self.title = data['title']
                self.content = data['content']
                self.order_index = data['order_index']
                self._data = data

            def to_dict(self):
                return self._data

        yield MockModule(module_dict, module_id)


@pytest.fixture
def sample_assessment(app, sample_course, sample_assessment_data):
    """Create a sample assessment in the database."""
    with app.app_context():
        assessment_data = sample_assessment_data.copy()
        assessment_data['course_id'] = sample_course.id
        assessment = Assessment(**assessment_data)
        db.session.add(assessment)
        db.session.commit()

        assessment_id = assessment.id
        assessment_dict = assessment.to_dict()

        class MockAssessment:
            def __init__(self, data, assessment_id):
                self.id = assessment_id
                self.course_id = data['course_id']
                self.title = data['title']
                self.description = data['description']
                self.max_score = data['max_score']
                self._data = data

            def to_dict(self):
                return self._data

        yield MockAssessment(assessment_dict, assessment_id)