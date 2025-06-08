# progress-service/tests/conftest.py
# Test configuration and fixtures for the Progress Service test suite.

import pytest
import os
import tempfile
import time
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models import ProgressTracking, AssessmentResult, CompletionCertificate
import jwt


# Patch shared modules at import time to avoid 500 errors
@pytest.fixture(scope='session', autouse=True)
def setup_mocks():
    """Set up mocks for shared modules before any tests run."""
    with patch('shared.message_queue.publish_message') as mock_publish, \
            patch('shared.message_queue.consume_messages') as mock_consume, \
            patch('shared.logging_config.configure_logging'), \
            patch('app.routes.publish_message') as mock_routes_publish, \
            patch('requests.get') as mock_requests:
        mock_publish.return_value = None
        mock_consume.return_value = None
        mock_routes_publish.return_value = None

        # Mock successful user service response
        mock_response = MagicMock()
        mock_response.json.return_value = {'email': 'test@example.com', 'id': 1}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        yield


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    # Set environment variables before creating app
    os.environ.update({
        'TESTING': 'True',
        'DATABASE_URL_PROGRESS': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET': 'test-jwt-secret',
        'JWT_EXPIRATION_HOURS': '24',
        'CACHE_TYPE': 'NullCache',
        'LOG_LEVEL': 'ERROR',
        'USER_SERVICE_URL': 'http://test-user-service',
        'COURSE_SERVICE_URL': 'http://test-course-service'
    })

    # Clear Azure service environment variables
    for var in ['AZURE_SERVICE_BUS_CONNECTION_STRING', 'AZURE_STORAGE_CONNECTION_STRING',
                'APPLICATIONINSIGHTS_CONNECTION_STRING']:
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
        test_vars = ['TESTING', 'DATABASE_URL_PROGRESS', 'SECRET_KEY', 'JWT_SECRET',
                     'JWT_EXPIRATION_HOURS', 'CACHE_TYPE', 'LOG_LEVEL', 'USER_SERVICE_URL', 'COURSE_SERVICE_URL']
        for var in test_vars:
            os.environ.pop(var, None)


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean database before each test."""
    with app.app_context():
        # Clean up any existing data in reverse order due to foreign keys
        CompletionCertificate.query.delete()
        AssessmentResult.query.delete()
        ProgressTracking.query.delete()
        db.session.commit()


@pytest.fixture
def sample_progress_data():
    """Sample progress data for testing."""
    return {
        'user_id': 1,
        'course_id': 101,
        'completion_percentage': 50.0,
        'time_spent': 120  # minutes
    }


@pytest.fixture
def sample_assessment_data():
    """Sample assessment data for testing."""
    return {
        'user_id': 1,
        'course_id': 101,
        'assessment_id': 201,
        'score': 85.0,
        'max_score': 100.0,
        'time_taken': 30
    }


@pytest.fixture
def sample_certificate_data():
    """Sample certificate data for testing."""
    return {
        'user_id': 1,
        'course_id': 101,
        'certificate_url': 'https://example.com/certificate/1'
    }


@pytest.fixture
def valid_token(app):
    """Generate a valid JWT token for testing."""
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
def auth_headers(valid_token):
    """Headers with valid authorization token."""
    return {'Authorization': valid_token}


@pytest.fixture
def sample_progress(app, sample_progress_data):
    """Create a sample progress record in the database."""
    with app.app_context():
        progress = ProgressTracking(
            user_id=sample_progress_data['user_id'],
            course_id=sample_progress_data['course_id'],
            completion_percentage=sample_progress_data['completion_percentage'],
            total_time_spent=sample_progress_data['time_spent']
        )
        db.session.add(progress)
        db.session.commit()
        yield progress


@pytest.fixture
def completed_progress(app):
    """Create a completed progress record for certificate testing."""
    with app.app_context():
        progress = ProgressTracking(
            user_id=1,
            course_id=101,
            completion_percentage=100.0,
            total_time_spent=300
        )
        db.session.add(progress)
        db.session.commit()
        yield progress


@pytest.fixture
def sample_assessment_result(app, sample_progress):
    """Create a sample assessment result linked to progress."""
    with app.app_context():
        result = AssessmentResult(
            user_id=1,
            assessment_id=201,
            score=85.0,
            max_score=100.0,
            percentage_score=85.0,
            progress_id=sample_progress.id
        )
        db.session.add(result)
        db.session.commit()
        yield result