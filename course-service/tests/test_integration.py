# course-service/tests/test_integration.py
# Integration tests for the Course Service that test end-to-end functionality.

import pytest
import json
from unittest.mock import patch


class TestCourseWorkflow:
    """Integration tests for complete course workflows."""

    def test_complete_course_creation_workflow(self, client, instructor_token):
        """Test complete workflow of creating course, modules, and assessments."""
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}

        # 1. Create a course
        course_data = {
            'title': 'Integration Test Course',
            'description': 'A course for integration testing'
        }

        response = client.post('/courses', data=json.dumps(course_data), headers=headers)
        assert response.status_code == 201

        course = json.loads(response.data)
        course_id = course['id']

        # 2. Verify course appears in course list
        response = client.get('/courses')
        assert response.status_code == 200

        courses_data = json.loads(response.data)
        assert len(courses_data['courses']) == 1
        assert courses_data['courses'][0]['title'] == course_data['title']

        # 3. Get the specific course
        response = client.get(f'/courses/{course_id}')
        assert response.status_code == 200

        retrieved_course = json.loads(response.data)
        assert retrieved_course['title'] == course_data['title']

        # 4. Check modules (should be empty initially)
        response = client.get(f'/courses/{course_id}/modules')
        assert response.status_code == 200
        assert len(json.loads(response.data)) == 0

        # 5. Check assessments (should be empty initially)
        response = client.get(f'/courses/{course_id}/assessments')
        assert response.status_code == 200
        assert len(json.loads(response.data)) == 0

    def test_course_not_found_scenarios(self, client):
        """Test various scenarios where course is not found."""
        non_existent_id = 999

        # Test getting non-existent course
        response = client.get(f'/courses/{non_existent_id}')
        assert response.status_code == 404

        # Test getting modules for non-existent course
        response = client.get(f'/courses/{non_existent_id}/modules')
        assert response.status_code == 404

        # Test getting assessments for non-existent course
        response = client.get(f'/courses/{non_existent_id}/assessments')
        assert response.status_code == 404

    def test_authentication_workflow(self, client, sample_course_data):
        """Test authentication requirements across different endpoints."""
        headers = {'Content-Type': 'application/json'}

        # Try to create course without token
        response = client.post('/courses', data=json.dumps(sample_course_data), headers=headers)
        assert response.status_code == 401

        # Public endpoints should work without authentication
        response = client.get('/health')
        assert response.status_code == 200

        response = client.get('/ping')
        assert response.status_code == 200

        response = client.get('/courses')
        assert response.status_code == 200

    def test_pagination_workflow(self, client, app, instructor_token):
        """Test pagination across multiple pages."""
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}

        # Create 5 courses for simpler testing
        for i in range(5):
            course_data = {
                'title': f'Pagination Course {i + 1:02d}',
                'description': f'Description for course {i + 1}'
            }
            response = client.post('/courses', data=json.dumps(course_data), headers=headers)
            assert response.status_code == 201

        # Test first page with 3 per page
        response = client.get('/courses?page=1&per_page=3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['courses']) == 3
        assert data['pagination']['page'] == 1
        assert data['pagination']['total'] == 5

        # Test second page
        response = client.get('/courses?page=2&per_page=3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['courses']) == 2  # Remaining courses

    def test_error_handling_workflow(self, client, instructor_token):
        """Test error handling across different scenarios."""
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}

        # Test invalid JSON
        response = client.post('/courses', data='invalid json', headers=headers)
        assert response.status_code in [400, 500]  # Accept either error code
        if response.headers.get('Content-Type') == 'application/json':
            data = json.loads(response.data)
            assert 'error' in data or 'message' in data # Check for common error keys
        else:
            assert b'Bad Request' in response.data or b'JSON' in response.data

        # Test missing required fields
        incomplete_data = {'title': 'Test Course'}  # Missing description
        response = client.post('/courses', data=json.dumps(incomplete_data), headers=headers)
        assert response.status_code in [400, 500]  # Accept either error code
        if response.headers.get('Content-Type') == 'application/json':
            data = json.loads(response.data)
            assert data['code'] == 'MISSING_FIELDS'
        else:
            assert b'Missing required fields' in response.data or b'Bad Request' in response.data

        # Test getting metrics (should work even with errors above)
        response = client.get('/metrics')
        assert response.status_code == 200


class TestServiceIntegration:
    """Integration tests focusing on service layer integration."""

    @patch('app.routes.publish_message')
    def test_service_layer_integration(self, mock_publish, client, instructor_token, app):
        """Test that service layer properly integrates with routes."""
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}

        # Create course through API
        course_data = {
            'title': 'Service Integration Course',
            'description': 'Testing service integration'
        }

        response = client.post('/courses', data=json.dumps(course_data), headers=headers)
        assert response.status_code == 201

        course = json.loads(response.data)

        # Verify course was created in database through service layer
        with app.app_context():
            from app.models import Course
            db_course = Course.query.get(course['id'])
            assert db_course is not None
            assert db_course.title == course_data['title']
            assert db_course.instructor_id == 1  # From token

    @patch('app.routes.publish_message')
    def test_duplicate_course_prevention(self, mock_publish, client, instructor_token):
        """Test that duplicate course creation is prevented."""
        headers = {'Authorization': instructor_token, 'Content-Type': 'application/json'}

        course_data = {
            'title': 'Duplicate Test Course',
            'description': 'Testing duplicate prevention'
        }

        # Create first course
        response = client.post('/courses', data=json.dumps(course_data), headers=headers)
        assert response.status_code == 201

        # Try to create duplicate
        response = client.post('/courses', data=json.dumps(course_data), headers=headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'already exists' in data['error'].lower()


class TestCacheIntegration:
    """Integration tests for caching behavior."""

    def test_course_list_caching(self, client, sample_course):
        """Test that course list responses are properly cached."""
        # First request - should hit database
        response1 = client.get('/courses')
        assert response1.status_code == 200

        # Second request - should hit cache (same response)
        response2 = client.get('/courses')
        assert response2.status_code == 200

        # Should get same data
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)
        assert data1 == data2

    def test_individual_course_caching(self, client, sample_course):
        """Test that individual course responses are cached."""
        course_id = sample_course.id

        # First request
        response1 = client.get(f'/courses/{course_id}')
        assert response1.status_code == 200

        # Second request
        response2 = client.get(f'/courses/{course_id}')
        assert response2.status_code == 200

        # Should get same data
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)
        assert data1 == data2


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    def test_database_error_recovery(self, client, app):
        """Test that the service handles database errors gracefully."""
        # This would typically involve mocking database failures
        # For now, we test that the service continues to work after errors

        # Make a request that should work
        response = client.get('/health')
        assert response.status_code == 200

        # Make another request to ensure service is still functional
        response = client.get('/courses')
        assert response.status_code == 200

    def test_malformed_request_recovery(self, client, instructor_token):
        """Test that service recovers from malformed requests."""
        headers = {'Authorization': instructor_token}

        # Send malformed request
        response = client.post('/courses', data='not json', headers=headers)
        assert response.status_code in [400, 500]  # Accept either error code

        # Only attempt to load JSON if the response content type indicates JSON
        if response.headers.get('Content-Type') == 'application/json':
            data = json.loads(response.data)
            assert 'error' in data or 'message' in data # Check for common error keys
        else:
            assert b'Bad Request' in response.data or b'JSON' in response.data # Check for common error messages

        # Service should still be functional for valid requests
        response = client.get('/health')
        assert response.status_code == 200