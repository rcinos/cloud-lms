# course-service/tests/test_debug.py
# Debug tests to identify 500 errors

import pytest
import json
from unittest.mock import patch


class TestDebugRoutes:
    """Debug tests to identify what's causing 500 errors."""

    def test_create_course_debug(self, client, instructor_token):
        """Debug test for course creation."""
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}
        course_data = {
            'title': 'Debug Course',
            'description': 'Debug description'
        }

        print(f"Headers: {headers}")
        print(f"Course data: {course_data}")

        response = client.post('/courses',
                               data=json.dumps(course_data),
                               headers=headers)

        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        print(f"Response headers: {response.headers}")

        # Decode and print the actual error
        if response.status_code != 201:
            try:
                error_data = json.loads(response.data)
                print(f"Error details: {error_data}")
                # Let's see what the actual error is instead of asserting
                return  # Don't fail the test, just show us the error
            except Exception as e:
                print(f"Could not parse error response: {e}")
                print(f"Raw error response: {response.data}")
                return
        else:
            success_data = json.loads(response.data)
            print(f"Success! Course created: {success_data}")
            assert success_data['title'] == 'Debug Course'

    def test_all_routes_debug(self, client, instructor_token):
        """Test all routes to identify any remaining 500 errors."""
        print("\n=== Testing all routes ===")

        # Health routes
        response = client.get('/health')
        print(f"GET /health: {response.status_code}")

        response = client.get('/ping')
        print(f"GET /ping: {response.status_code}")

        response = client.get('/metrics')
        print(f"GET /metrics: {response.status_code}")

        # Course routes
        response = client.get('/courses')
        print(f"GET /courses: {response.status_code}")

        # Create a course
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}
        course_data = {'title': 'Test Course', 'description': 'Test description'}
        response = client.post('/courses', data=json.dumps(course_data), headers=headers)
        print(f"POST /courses: {response.status_code}")

        if response.status_code == 201:
            course = json.loads(response.data)
            course_id = course['id']

            # Test course-specific routes
            response = client.get(f'/courses/{course_id}')
            print(f"GET /courses/{course_id}: {response.status_code}")

            response = client.get(f'/courses/{course_id}/modules')
            print(f"GET /courses/{course_id}/modules: {response.status_code}")

            response = client.get(f'/courses/{course_id}/assessments')
            print(f"GET /courses/{course_id}/assessments: {response.status_code}")

    def test_mocking_debug(self, client):
        """Debug test to check if mocking is working properly."""
        print("\n=== Testing Mocking ===")

        # Test if requests.get is mocked
        import requests
        try:
            response = requests.get('http://test-user-service/users/1')
            print(f"requests.get mock status: {response.status_code}")
            print(f"requests.get mock response: {response.json()}")
        except Exception as e:
            print(f"requests.get mock error: {e}")

        # Test if publish_message is mocked
        try:
            from shared.message_queue import publish_message
            result = publish_message('test-queue', 'test-message')
            print(f"publish_message mock result: {result}")
        except Exception as e:
            print(f"publish_message mock error: {e}")

    @patch('shared.message_queue.publish_message')
    @patch('requests.get')
    def test_create_course_explicit_mock(self, mock_requests, mock_publish, client, instructor_token):
        """Test course creation with explicit mocking."""

        # Set up mocks explicitly with proper class
        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {'user_type': 'instructor'}

            def raise_for_status(self):
                pass

        mock_requests.return_value = MockResponse()
        mock_publish.return_value = None

        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}
        course_data = {
            'title': 'Explicit Mock Course',
            'description': 'Test with explicit mocking'
        }

        print(f"Making request with explicit mocks...")
        response = client.post('/courses',
                               data=json.dumps(course_data),
                               headers=headers)

        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")

        if response.status_code == 201:
            print("✅ Explicit mocking works!")
            success_data = json.loads(response.data)
            assert success_data['title'] == 'Explicit Mock Course'
        else:
            print("❌ Even explicit mocking failed")
            if response.status_code == 500:
                try:
                    error_data = json.loads(response.data)
                    print(f"Error details: {error_data}")
                except:
                    print(f"Raw error response: {response.data}")

    def test_instructor_token_debug(self, app, instructor_token):
        """Debug test for instructor token."""
        print(f"Instructor token: {instructor_token}")

        with app.app_context():
            import jwt
            try:
                # Try to decode the token
                token_without_bearer = instructor_token.replace('Bearer ', '')
                decoded = jwt.decode(token_without_bearer, app.config['JWT_SECRET'], algorithms=['HS256'])
                print(f"Decoded token: {decoded}")
            except Exception as e:
                print(f"Token decode error: {e}")

    def test_app_config_debug(self, app):
        """Debug test to check app configuration."""
        with app.app_context():
            print(f"App config keys: {list(app.config.keys())}")
            print(f"JWT_SECRET exists: {'JWT_SECRET' in app.config}")
            print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
            print(f"Testing mode: {app.config.get('TESTING')}")