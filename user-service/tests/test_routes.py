# user-service/tests/test_routes.py
# Tests for the API routes in the User Service.

import pytest
import json
from unittest.mock import patch


class TestHealthRoutes:
    """Tests for health check and monitoring routes."""

    def test_ping(self, client):
        """Test ping endpoint."""
        response = client.get('/ping')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'pong'

    def test_metrics(self, client, sample_user, sample_instructor, sample_enrollment):
        """Test metrics endpoint."""
        response = client.get('/metrics')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_users' in data
        assert 'total_students' in data
        assert 'total_instructors' in data
        assert 'total_enrollments' in data
        assert data['service'] == 'user-service'
        assert data['total_users'] >= 2  # At least our sample users
        assert data['total_students'] >= 1
        assert data['total_instructors'] >= 1
        assert data['total_enrollments'] >= 1


class TestUserRoutes:
    """Tests for user-related API routes."""

    def test_get_users_empty(self, client):
        """Test getting users when none exist."""
        response = client.get('/users')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data
        assert 'pagination' in data
        assert len(data['users']) == 0

    def test_get_users_with_data(self, client, sample_user, sample_instructor):
        """Test getting users with existing data."""
        response = client.get('/users')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 2
        assert data['pagination']['total'] == 2

        # Check that user data doesn't include email by default
        for user in data['users']:
            assert 'email' not in user
            assert 'user_type' in user

    def test_get_users_pagination(self, client, app):
        """Test user pagination."""
        # Create multiple users
        with app.app_context():
            from app.services import UserService
            service = UserService()

            for i in range(15):
                user_data = {
                    'email': f'user{i}@example.com',
                    'password': 'Password123',
                    'user_type': 'student' if i % 2 == 0 else 'instructor'
                }
                service.create_user(user_data)

        # Test first page
        response = client.get('/users?page=1&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total'] == 15

        # Test second page
        response = client.get('/users?page=2&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 5  # Remaining users

    def test_get_users_filter_by_type(self, client, sample_user, sample_instructor):
        """Test filtering users by type."""
        # Test student filter
        response = client.get('/users?type=student')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 1
        assert data['users'][0]['user_type'] == 'student'

        # Test instructor filter
        response = client.get('/users?type=instructor')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 1
        assert data['users'][0]['user_type'] == 'instructor'

    def test_get_users_invalid_filter(self, client):
        """Test invalid user type filter."""
        response = client.get('/users?type=invalid')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_USER_TYPE'

    def test_get_user_by_id(self, client, sample_user):
        """Test getting a specific user by ID."""
        response = client.get(f'/users/{sample_user.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == sample_user.id
        assert data['email'] == sample_user.email  # Should include email for individual user
        assert data['user_type'] == sample_user.user_type

    def test_get_user_not_found(self, client):
        """Test getting a non-existent user."""
        response = client.get('/users/999')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['code'] == 'USER_NOT_FOUND'

    def test_get_user_with_profile(self, client, app):
        """Test getting a user with profile data."""
        with app.app_context():
            from app.services import UserService
            service = UserService()

            user_data = {
                'email': 'profile@example.com',
                'password': 'ProfilePass123',
                'user_type': 'student',
                'first_name': 'Profile',
                'last_name': 'User',
                'bio': 'Has profile data'
            }
            user = service.create_user(user_data)
            user_id = user.id

        response = client.get(f'/users/{user_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'profile' in data
        assert data['profile']['first_name'] == 'Profile'
        assert data['profile']['last_name'] == 'User'
        assert data['profile']['bio'] == 'Has profile data'


class TestAuthRoutes:
    """Tests for authentication routes."""

    def test_register_success(self, client):
        """Test successful user registration."""
        user_data = {
            'email': 'newregister@example.com',
            'password': 'RegisterPass123',
            'user_type': 'student',
            'first_name': 'New',
            'last_name': 'Register'
        }

        with patch('app.routes.publish_message') as mock_publish:
            response = client.post('/auth/register',
                                   data=json.dumps(user_data),
                                   content_type='application/json')

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['user_type'] == 'student'
            assert 'email' not in data  # Email should not be in response by default

            # Verify event was published
            mock_publish.assert_called_once()

    def test_register_missing_fields(self, client):
        """Test registration with missing required fields."""
        incomplete_data = {
            'email': 'incomplete@example.com'
            # Missing password and user_type
        }

        response = client.post('/auth/register',
                               data=json.dumps(incomplete_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_FIELDS'

    def test_register_invalid_user_type(self, client):
        """Test registration with invalid user type."""
        user_data = {
            'email': 'invalid@example.com',
            'password': 'InvalidPass123',
            'user_type': 'admin'  # Invalid type
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_USER_TYPE'

    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email."""
        user_data = {
            'email': 'duplicate@example.com',
            'password': 'DuplicatePass123',
            'user_type': 'instructor'
        }

        with patch('app.routes.publish_message'):
            # Create first user
            response = client.post('/auth/register',
                                   data=json.dumps(user_data),
                                   content_type='application/json')
            assert response.status_code == 201

            # Try to create duplicate
            response = client.post('/auth/register',
                                   data=json.dumps(user_data),
                                   content_type='application/json')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['code'] == 'REGISTRATION_VALIDATION_ERROR'

    def test_register_invalid_json(self, client):
        """Test registration with invalid JSON."""
        response = client.post('/auth/register',
                               data='invalid json',
                               content_type='application/json')

        assert response.status_code == 400

    def test_login_success(self, client, sample_user):
        """Test successful login."""
        login_data = {
            'email': sample_user.email,
            'password': sample_user.password  # Use the stored plain password
        }

        response = client.post('/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'token' in data
        assert data['token'] is not None

    def test_login_wrong_password(self, client, sample_user):
        """Test login with wrong password."""
        login_data = {
            'email': sample_user.email,
            'password': 'WrongPassword'
        }

        response = client.post('/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_CREDENTIALS'

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword'
        }

        response = client.post('/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['code'] == 'INVALID_CREDENTIALS'

    def test_login_missing_credentials(self, client):
        """Test login with missing credentials."""
        login_data = {
            'email': 'test@example.com'
            # Missing password
        }

        response = client.post('/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_CREDENTIALS'

    def test_login_invalid_json(self, client):
        """Test login with invalid JSON."""
        response = client.post('/auth/login',
                               data='invalid json',
                               content_type='application/json')

        assert response.status_code == 400


class TestEnrollmentRoutes:
    """Tests for enrollment routes."""

    def test_create_enrollment_success(self, client):
        """Test creating an enrollment successfully."""
        # First create a user
        user_data = {
            'email': 'enrolluser@example.com',
            'password': 'EnrollPass123',
            'user_type': 'student'
        }

        with patch('app.routes.publish_message') as mock_publish:
            response = client.post('/auth/register',
                                   data=json.dumps(user_data),
                                   content_type='application/json')
            assert response.status_code == 201
            user = json.loads(response.data)
            user_id = user['id']

            # Now create enrollment
            enrollment_data = {
                'user_id': user_id,
                'course_id': 201
            }

            response = client.post('/enrollments',
                                   data=json.dumps(enrollment_data),
                                   content_type='application/json')

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['user_id'] == user_id
            assert data['course_id'] == 201
            assert data['status'] == 'active'

            # Verify events were published (registration + enrollment)
            assert mock_publish.call_count == 2

    def test_create_enrollment_missing_fields(self, client):
        """Test creating enrollment with missing fields."""
        incomplete_data = {
            'user_id': 1
            # Missing course_id
        }

        response = client.post('/enrollments',
                               data=json.dumps(incomplete_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_FIELDS'

    def test_create_enrollment_duplicate(self, client, sample_enrollment):
        """Test creating duplicate enrollment."""
        enrollment_data = {
            'user_id': sample_enrollment.user_id,
            'course_id': sample_enrollment.course_id
        }

        response = client.post('/enrollments',
                               data=json.dumps(enrollment_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'ENROLLMENT_VALIDATION_ERROR'

    def test_create_enrollment_user_not_found(self, client):
        """Test creating enrollment for non-existent user."""
        enrollment_data = {
            'user_id': 999,  # Non-existent user
            'course_id': 202
        }

        response = client.post('/enrollments',
                               data=json.dumps(enrollment_data),
                               content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'ENROLLMENT_VALIDATION_ERROR'

    def test_get_user_enrollments(self, client, sample_enrollment):
        """Test getting user's enrollments."""
        response = client.get(f'/users/{sample_enrollment.user_id}/enrollments')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['user_id'] == sample_enrollment.user_id
        assert data[0]['course_id'] == sample_enrollment.course_id

    def test_get_user_enrollments_empty(self, client, sample_user):
        """Test getting enrollments for user with no enrollments."""
        response = client.get(f'/users/{sample_user.id}/enrollments')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 0

    def test_get_user_enrollments_user_not_found(self, client):
        """Test getting enrollments for non-existent user."""
        response = client.get('/users/999/enrollments')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['code'] == 'USER_NOT_FOUND'


class TestHealthCheckRoute:
    """Tests for the comprehensive health check route."""

    def test_health_check_basic(self, client):
        """Test basic health check functionality."""
        response = client.get('/api/health-check')

        # Should return either 200 (all OK) or 500 (some issues)
        assert response.status_code in [200, 500]

        data = json.loads(response.data)
        assert 'overall_status' in data
        assert 'database' in data
        assert 'redis_cache' in data
        assert 'service_bus_send' in data
        assert 'azure_storage_logging' in data

        # Each component should have status and message
        for component in ['database', 'redis_cache', 'service_bus_send', 'azure_storage_logging']:
            assert 'status' in data[component]
            assert 'message' in data[component]
            assert data[component]['status'] in ['OK', 'ERROR']