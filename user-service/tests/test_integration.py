# user-service/tests/test_integration.py
# Fixed integration tests for the User Service

import pytest
import json
from unittest.mock import patch


class TestUserWorkflow:
    """Integration tests for complete user workflows."""

    def test_complete_user_registration_workflow(self, client):
        """Test complete workflow of user registration, login, and profile access."""
        # 1. Register a new user
        user_data = {
            'email': 'workflow@example.com',
            'password': 'WorkflowPass123',
            'user_type': 'student',
            'first_name': 'Workflow',
            'last_name': 'User',
            'bio': 'Integration test user'
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')
        assert response.status_code == 201

        user = json.loads(response.data)
        user_id = user['id']

        # Note: publish_message is mocked globally, so we don't verify it here

        # 2. Login with the new user
        login_data = {
            'email': user_data['email'],
            'password': user_data['password']
        }

        response = client.post('/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')
        assert response.status_code == 200

        login_result = json.loads(response.data)
        assert 'token' in login_result

        # 3. Get the user details
        response = client.get(f'/users/{user_id}')
        assert response.status_code == 200

        user_details = json.loads(response.data)
        assert user_details['email'] == user_data['email']
        assert user_details['user_type'] == user_data['user_type']
        assert 'profile' in user_details
        assert user_details['profile']['first_name'] == user_data['first_name']
        assert user_details['profile']['last_name'] == user_data['last_name']
        assert user_details['profile']['bio'] == user_data['bio']

        # 4. Verify user appears in user list
        response = client.get('/users')
        assert response.status_code == 200

        users_data = json.loads(response.data)
        assert len(users_data['users']) == 1
        assert users_data['users'][0]['id'] == user_id

    def test_enrollment_workflow(self, client):
        """Test complete enrollment workflow."""
        # 1. Create a user first
        user_data = {
            'email': 'enroll@example.com',
            'password': 'EnrollPass123',
            'user_type': 'student'
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')
        assert response.status_code == 201

        user = json.loads(response.data)
        user_id = user['id']

        # 2. Create an enrollment
        enrollment_data = {
            'user_id': user_id,
            'course_id': 301
        }

        response = client.post('/enrollments',
                               data=json.dumps(enrollment_data),
                               content_type='application/json')
        assert response.status_code == 201

        enrollment = json.loads(response.data)
        assert enrollment['user_id'] == user_id
        assert enrollment['course_id'] == 301

        # Note: publish_message is mocked globally

        # 3. Get user's enrollments
        response = client.get(f'/users/{user_id}/enrollments')
        assert response.status_code == 200

        enrollments = json.loads(response.data)
        assert len(enrollments) == 1
        assert enrollments[0]['course_id'] == 301

    def test_user_types_workflow(self, client):
        """Test workflow with different user types."""
        # Create student
        student_data = {
            'email': 'student@example.com',
            'password': 'StudentPass123',
            'user_type': 'student'
        }

        response = client.post('/auth/register',
                               data=json.dumps(student_data),
                               content_type='application/json')
        assert response.status_code == 201

        # Create instructor
        instructor_data = {
            'email': 'instructor@example.com',
            'password': 'InstructorPass123',
            'user_type': 'instructor'
        }

        response = client.post('/auth/register',
                               data=json.dumps(instructor_data),
                               content_type='application/json')
        assert response.status_code == 201

        # Test filtering by user type
        response = client.get('/users?type=student')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 1
        assert data['users'][0]['user_type'] == 'student'

        response = client.get('/users?type=instructor')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 1
        assert data['users'][0]['user_type'] == 'instructor'

    def test_authentication_flow(self, client):
        """Test complete authentication flow."""
        # 1. Register user
        user_data = {
            'email': 'auth@example.com',
            'password': 'AuthPass123',
            'user_type': 'student'
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')
        assert response.status_code == 201

        # 2. Login successfully
        login_data = {
            'email': user_data['email'],
            'password': user_data['password']
        }

        response = client.post('/auth/login',
                               data=json.dumps(login_data),
                               content_type='application/json')
        assert response.status_code == 200

        # 3. Try login with wrong password
        wrong_login = {
            'email': user_data['email'],
            'password': 'WrongPassword'
        }

        response = client.post('/auth/login',
                               data=json.dumps(wrong_login),
                               content_type='application/json')
        assert response.status_code == 401

        # 4. Try login with non-existent user
        nonexistent_login = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword'
        }

        response = client.post('/auth/login',
                               data=json.dumps(nonexistent_login),
                               content_type='application/json')
        assert response.status_code == 401

    def test_pagination_workflow(self, client):
        """Test pagination across multiple users."""
        # Create multiple users
        for i in range(25):
            user_data = {
                'email': f'user{i}@example.com',
                'password': f'Password{i}',
                'user_type': 'student' if i % 2 == 0 else 'instructor'
            }
            response = client.post('/auth/register',
                                   data=json.dumps(user_data),
                                   content_type='application/json')
            assert response.status_code == 201

        # Test first page
        response = client.get('/users?page=1&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total'] == 25

        # Test second page
        response = client.get('/users?page=2&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 10
        assert data['pagination']['page'] == 2

        # Test last page
        response = client.get('/users?page=3&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['users']) == 5  # Remaining users


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_validation_error_handling(self, client):
        """Test various validation error scenarios."""
        # Test registration with invalid data
        invalid_data = {
            'email': 'invalid-email',  # Invalid email format
            'password': '123',  # Too short
            'user_type': 'admin'  # Invalid type
        }

        response = client.post('/auth/register',
                               data=json.dumps(invalid_data),
                               content_type='application/json')
        assert response.status_code == 400

        # Test login with missing data
        response = client.post('/auth/login',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400

        # Test enrollment with invalid data
        response = client.post('/enrollments',
                               data=json.dumps({'user_id': 'invalid'}),
                               content_type='application/json')
        assert response.status_code == 400

    def test_not_found_scenarios(self, client):
        """Test various not found scenarios."""
        # Test getting non-existent user
        response = client.get('/users/999')
        assert response.status_code == 404

        # Test getting enrollments for non-existent user
        response = client.get('/users/999/enrollments')
        assert response.status_code == 404

    def test_malformed_json_handling(self, client):
        """Test handling of malformed JSON requests."""
        # Test registration with malformed JSON - should return 400
        response = client.post('/auth/register',
                               data='invalid json',
                               content_type='application/json')
        assert response.status_code == 400

        # Test login with malformed JSON - should return 400
        response = client.post('/auth/login',
                               data='{invalid json}',
                               content_type='application/json')
        assert response.status_code == 400

        # Test enrollment with malformed JSON - should return 400
        response = client.post('/enrollments',
                               data='not json at all',
                               content_type='application/json')
        assert response.status_code == 400

    def test_service_recovery(self, client):
        """Test that service recovers from errors."""
        # Make a request that causes an error (Flask will handle it gracefully)
        response = client.post('/auth/register',
                               data='invalid json',
                               content_type='application/json')
        assert response.status_code == 400

        # Verify service is still functional
        response = client.get('/ping')
        assert response.status_code == 200

        response = client.get('/users')
        assert response.status_code == 200


class TestServiceIntegration:
    """Tests focusing on service layer integration."""

    def test_service_layer_integration(self, client):
        """Test that service layer properly integrates with routes."""
        user_data = {
            'email': 'service@example.com',
            'password': 'ServicePass123',
            'user_type': 'instructor',
            'first_name': 'Service',
            'last_name': 'Test'
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')
        assert response.status_code == 201

        user = json.loads(response.data)

        # Verify user was created through service layer
        response = client.get(f'/users/{user["id"]}')
        assert response.status_code == 200

        user_details = json.loads(response.data)
        assert user_details['email'] == user_data['email']
        assert user_details['profile']['first_name'] == user_data['first_name']

    def test_duplicate_prevention(self, client):
        """Test that duplicate prevention works across service calls."""
        user_data = {
            'email': 'duplicate@example.com',
            'password': 'DuplicatePass123',
            'user_type': 'student'
        }

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
        assert 'already exists' in data['error'].lower()


class TestDataConsistency:
    """Tests for data consistency and integrity."""

    def test_user_profile_consistency(self, client):
        """Test consistency between user and profile data."""
        user_data = {
            'email': 'consistent@example.com',
            'password': 'ConsistentPass123',
            'user_type': 'student',
            'first_name': 'Consistent',
            'last_name': 'User'
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')
        assert response.status_code == 201

        user = json.loads(response.data)
        user_id = user['id']

        # Get user details
        response = client.get(f'/users/{user_id}')
        assert response.status_code == 200

        user_details = json.loads(response.data)

        # Verify consistency
        assert user_details['email'] == user_data['email']
        assert user_details['user_type'] == user_data['user_type']
        assert user_details['profile']['first_name'] == user_data['first_name']
        assert user_details['profile']['last_name'] == user_data['last_name']

    def test_enrollment_consistency(self, client):
        """Test consistency in enrollment data."""
        # Create user
        user_data = {
            'email': 'enroll@example.com',
            'password': 'EnrollPass123',
            'user_type': 'student'
        }

        response = client.post('/auth/register',
                               data=json.dumps(user_data),
                               content_type='application/json')
        assert response.status_code == 201

        user = json.loads(response.data)
        user_id = user['id']

        # Create enrollment
        enrollment_data = {
            'user_id': user_id,
            'course_id': 401
        }

        response = client.post('/enrollments',
                               data=json.dumps(enrollment_data),
                               content_type='application/json')
        assert response.status_code == 201

        enrollment = json.loads(response.data)

        # Verify enrollment consistency
        response = client.get(f'/users/{user_id}/enrollments')
        assert response.status_code == 200

        enrollments = json.loads(response.data)
        assert len(enrollments) == 1
        assert enrollments[0]['id'] == enrollment['id']
        assert enrollments[0]['user_id'] == user_id
        assert enrollments[0]['course_id'] == 401