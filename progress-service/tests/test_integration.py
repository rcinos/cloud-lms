# progress-service/tests/test_integration.py
# Integration tests for the Progress Service that test end-to-end functionality.

import pytest
import json
from unittest.mock import patch


class TestProgressWorkflow:
    """Integration tests for complete progress workflows."""

    def test_complete_progress_tracking_workflow(self, client, auth_headers):
        """Test complete workflow of progress tracking from start to certificate."""
        # 1. Create initial progress
        progress_data = {
            'user_id': 1,
            'course_id': 101,
            'completion_percentage': 25.0,
            'time_spent': 60
        }

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201

        # 2. Record first assessment
        assessment_data = {
            'user_id': 1,
            'course_id': 101,
            'assessment_id': 201,
            'score': 80.0,
            'max_score': 100.0,
            'time_taken': 30
        }

        response = client.post('/assessments/results',
                               data=json.dumps(assessment_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201

        # 3. Update progress to intermediate level
        progress_data['completion_percentage'] = 75.0
        progress_data['time_spent'] = 120

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201

        # 4. Record second assessment (retry)
        assessment_data['score'] = 90.0
        assessment_data['time_taken'] = 25

        response = client.post('/assessments/results',
                               data=json.dumps(assessment_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201

        result = json.loads(response.data)
        assert result['attempt_number'] == 2  # Should be second attempt

        # 5. Complete the course
        progress_data['completion_percentage'] = 100.0
        progress_data['time_spent'] = 60

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201

        # 6. Issue certificate
        certificate_data = {
            'user_id': 1,
            'course_id': 101,
            'certificate_url': 'https://example.com/cert/workflow'
        }

        response = client.post('/certificates',
                               data=json.dumps(certificate_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201

        # 7. Verify final analytics
        response = client.get('/analytics/user/1', headers=auth_headers)
        assert response.status_code == 200

        analytics = json.loads(response.data)
        assert analytics['total_courses_enrolled'] == 1
        assert analytics['completed_courses'] == 1
        assert analytics['certificates_earned'] == 1
        assert analytics['total_assessments_taken'] == 2

    def test_multiple_course_progress_workflow(self, client, auth_headers):
        """Test user progressing through multiple courses."""
        courses = [101, 102, 103]

        for i, course_id in enumerate(courses):
            # Create progress for each course
            progress_data = {
                'user_id': 1,
                'course_id': course_id,
                'completion_percentage': (i + 1) * 30.0,  # 30%, 60%, 90%
                'time_spent': (i + 1) * 45
            }

            response = client.post('/progress',
                                   data=json.dumps(progress_data),
                                   content_type='application/json',
                                   headers=auth_headers)
            assert response.status_code == 201

            # Add assessment for each course
            assessment_data = {
                'user_id': 1,
                'course_id': course_id,
                'assessment_id': 200 + course_id,
                'score': 85.0 + i * 5,  # Increasing scores
                'max_score': 100.0
            }

            response = client.post('/assessments/results',
                                   data=json.dumps(assessment_data),
                                   content_type='application/json',
                                   headers=auth_headers)
            assert response.status_code == 201

        # Verify user analytics
        response = client.get('/analytics/user/1', headers=auth_headers)
        assert response.status_code == 200

        analytics = json.loads(response.data)
        assert analytics['total_courses_enrolled'] == 3
        assert analytics['total_assessments_taken'] == 3
        assert analytics['average_completion_rate'] == 60.0  # (30+60+90)/3

    def test_course_analytics_workflow(self, client, auth_headers):
        """Test course analytics with multiple students."""
        # Create progress for multiple users on the same course
        user_ids = [1, 2, 3]
        completion_rates = [100.0, 75.0, 50.0]

        for user_id, completion in zip(user_ids, completion_rates):
            # Mock different user tokens for each request
            with patch('app.utils.jwt.decode') as mock_decode:
                mock_decode.return_value = {
                    'user_id': user_id,
                    'email': f'user{user_id}@example.com',
                    'user_type': 'student'
                }

                progress_data = {
                    'user_id': user_id,
                    'course_id': 101,
                    'completion_percentage': completion,
                    'time_spent': int(completion * 2)  # Time proportional to completion
                }

                response = client.post('/progress',
                                       data=json.dumps(progress_data),
                                       content_type='application/json',
                                       headers=auth_headers)
                assert response.status_code == 201

        # Check course analytics
        response = client.get('/analytics/course/101', headers=auth_headers)
        assert response.status_code == 200

        analytics = json.loads(response.data)
        assert analytics['total_enrollments'] == 3
        assert analytics['completed_students'] == 1  # Only user 1 completed (100%)
        assert analytics['completion_rate_percentage'] == 33.33  # 1/3 * 100
        assert analytics['average_progress_percentage'] == 75.0  # (100+75+50)/3


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_unauthorized_access_scenarios(self, client):
        """Test various unauthorized access scenarios."""
        # Test without token
        response = client.get('/progress')
        assert response.status_code == 401

        response = client.post('/progress', json={'user_id': 1, 'course_id': 101})
        assert response.status_code == 401

        response = client.get('/analytics/user/1')
        assert response.status_code == 401

    def test_cross_user_access_prevention(self, client, auth_headers):
        """Test that users cannot access other users' data."""
        # Try to access user 2's data with user 1's token
        response = client.get('/progress/2/101', headers=auth_headers)
        assert response.status_code == 403

        response = client.get('/analytics/user/2', headers=auth_headers)
        assert response.status_code == 403

        # Try to create progress for user 2 with user 1's token
        progress_data = {
            'user_id': 2,
            'course_id': 101,
            'completion_percentage': 50.0
        }
        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 403

    def test_malformed_json_handling(self, client, auth_headers):
        """Test handling of malformed JSON requests."""
        response = client.post('/progress',
                               data='invalid json',
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'INVALID_JSON_FORMAT'

        response = client.post('/assessments/results',
                               data='{invalid json}',
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'INVALID_JSON_FORMAT'

        response = client.post('/certificates',
                               data='not json at all',
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'INVALID_JSON_FORMAT'

    def test_missing_required_fields(self, client, auth_headers):
        """Test validation of required fields."""
        # Missing course_id in progress
        response = client.post('/progress',
                               json={'user_id': 1},
                               headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_FIELDS'

        # Missing max_score in assessment
        response = client.post('/assessments/results',
                               json={'user_id': 1, 'assessment_id': 201, 'score': 85.0},
                               headers=auth_headers)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_FIELDS'


class TestDataConsistency:
    """Tests for data consistency and integrity."""

    def test_progress_and_assessment_consistency(self, client, auth_headers):
        """Test consistency between progress and assessment records."""
        # Create progress
        progress_data = {
            'user_id': 1,
            'course_id': 101,
            'completion_percentage': 50.0,
            'time_spent': 120
        }

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201
        progress = json.loads(response.data)

        # Record assessment
        assessment_data = {
            'user_id': 1,
            'course_id': 101,
            'assessment_id': 201,
            'score': 85.0,
            'max_score': 100.0
        }

        response = client.post('/assessments/results',
                               data=json.dumps(assessment_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201
        assessment = json.loads(response.data)

        # Verify they're linked
        assert assessment['progress_id'] == progress['id']

        # Get detailed progress and verify assessment is included
        response = client.get(f'/progress/1/101', headers=auth_headers)
        assert response.status_code == 200

        detailed_progress = json.loads(response.data)
        assert len(detailed_progress['assessment_results']) == 1
        assert detailed_progress['assessment_results'][0]['id'] == assessment['id']

    def test_time_accumulation_consistency(self, client, auth_headers):
        """Test that time spent accumulates correctly."""
        # Initial progress
        progress_data = {
            'user_id': 1,
            'course_id': 101,
            'completion_percentage': 25.0,
            'time_spent': 60
        }

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201
        initial = json.loads(response.data)
        assert initial['total_time_spent'] == 60

        # Update with additional time
        progress_data['completion_percentage'] = 50.0
        progress_data['time_spent'] = 45

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201
        updated = json.loads(response.data)
        assert updated['total_time_spent'] == 105  # 60 + 45

        # Third update
        progress_data['completion_percentage'] = 75.0
        progress_data['time_spent'] = 30

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)
        assert response.status_code == 201
        final = json.loads(response.data)
        assert final['total_time_spent'] == 135  # 105 + 30