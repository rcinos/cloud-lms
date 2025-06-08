# progress-service/tests/test_routes.py
# Tests for the API routes in the Progress Service.

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

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get('/health')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'progress-service'

    def test_metrics(self, client, sample_progress, sample_assessment_result):
        """Test metrics endpoint."""
        response = client.get('/metrics')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_progress_records' in data
        assert 'total_assessments_completed' in data
        assert 'total_certificates_issued' in data
        assert 'average_completion_rate' in data
        assert data['service'] == 'progress-service'
        assert data['total_progress_records'] >= 1


class TestProgressRoutes:
    """Tests for progress-related API routes."""

    def test_get_progress_records_empty(self, client, auth_headers):
        """Test getting progress records when none exist."""
        response = client.get('/progress', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'progress' in data
        assert 'pagination' in data
        assert len(data['progress']) == 0

    def test_get_progress_records_with_data(self, client, auth_headers, sample_progress):
        """Test getting progress records with existing data."""
        response = client.get('/progress', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['progress']) == 1
        assert data['progress'][0]['user_id'] == 1
        assert data['progress'][0]['course_id'] == 101

    def test_get_progress_records_unauthorized(self, client):
        """Test getting progress records without authorization."""
        response = client.get('/progress')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['code'] == 'TOKEN_MISSING'

    def test_get_user_course_progress(self, client, auth_headers, sample_progress):
        """Test getting specific user course progress."""
        response = client.get(f'/progress/1/101', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert data['course_id'] == 101
        assert 'assessment_results' in data

    def test_get_user_course_progress_unauthorized_user(self, client, auth_headers):
        """Test accessing another user's progress is forbidden."""
        response = client.get(f'/progress/2/101', headers=auth_headers)  # Different user_id

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 'UNAUTHORIZED_ACCESS'

    def test_get_user_course_progress_not_found(self, client, auth_headers):
        """Test getting progress for non-existent user/course combination."""
        response = client.get(f'/progress/1/999', headers=auth_headers)

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['code'] == 'PROGRESS_NOT_FOUND'

    def test_update_or_create_progress_new(self, client, auth_headers):
        """Test creating new progress record."""
        progress_data = {
            'user_id': 1,
            'course_id': 102,
            'completion_percentage': 30.0,
            'time_spent': 90
        }

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert data['course_id'] == 102
        assert data['completion_percentage'] == 30.0
        assert data['total_time_spent'] == 90

    def test_update_or_create_progress_update(self, client, auth_headers, sample_progress):
        """Test updating existing progress record."""
        update_data = {
            'user_id': 1,
            'course_id': 101,
            'completion_percentage': 80.0,
            'time_spent': 60
        }

        response = client.post('/progress',
                               data=json.dumps(update_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['completion_percentage'] == 80.0
        # total_time_spent should be original + new time
        assert data['total_time_spent'] > 120  # original was 120

    def test_update_progress_unauthorized_user(self, client, auth_headers):
        """Test updating another user's progress is forbidden."""
        progress_data = {
            'user_id': 2,  # Different user
            'course_id': 102,
            'completion_percentage': 30.0
        }

        response = client.post('/progress',
                               data=json.dumps(progress_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 'UNAUTHORIZED_ACCESS'

    def test_update_progress_missing_fields(self, client, auth_headers):
        """Test updating progress with missing required fields."""
        incomplete_data = {
            'user_id': 1
            # Missing course_id
        }

        response = client.post('/progress',
                               data=json.dumps(incomplete_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_FIELDS'


class TestAssessmentRoutes:
    """Tests for assessment-related routes."""

    def test_record_assessment_result(self, client, auth_headers, sample_progress):
        """Test recording an assessment result."""
        assessment_data = {
            'user_id': 1,
            'course_id': 101,
            'assessment_id': 201,
            'score': 90.0,
            'max_score': 100.0,
            'time_taken': 25
        }

        response = client.post('/assessments/results',
                               data=json.dumps(assessment_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert data['assessment_id'] == 201
        assert data['score'] == 90.0
        assert data['percentage_score'] == 90.0
        assert data['attempt_number'] == 1

    def test_record_assessment_unauthorized_user(self, client, auth_headers):
        """Test recording assessment for another user is forbidden."""
        assessment_data = {
            'user_id': 2,  # Different user
            'course_id': 101,
            'assessment_id': 201,
            'score': 90.0,
            'max_score': 100.0
        }

        response = client.post('/assessments/results',
                               data=json.dumps(assessment_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 'UNAUTHORIZED_ACCESS'

    def test_record_assessment_missing_fields(self, client, auth_headers):
        """Test recording assessment with missing fields."""
        incomplete_data = {
            'user_id': 1,
            'assessment_id': 201
            # Missing score, max_score, course_id
        }

        response = client.post('/assessments/results',
                               data=json.dumps(incomplete_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'MISSING_FIELDS'


class TestAnalyticsRoutes:
    """Tests for analytics routes."""

    def test_get_user_analytics(self, client, auth_headers, sample_progress, sample_assessment_result):
        """Test getting user analytics."""
        response = client.get('/analytics/user/1', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert 'total_courses_enrolled' in data
        assert 'average_completion_rate' in data
        assert 'total_assessments_taken' in data
        assert data['total_courses_enrolled'] >= 1

    def test_get_user_analytics_unauthorized(self, client, auth_headers):
        """Test getting analytics for another user is forbidden."""
        response = client.get('/analytics/user/2', headers=auth_headers)  # Different user

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 'UNAUTHORIZED_ACCESS'

    def test_get_course_analytics(self, client, auth_headers, sample_progress):
        """Test getting course analytics."""
        response = client.get('/analytics/course/101', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['course_id'] == 101
        assert 'total_enrollments' in data
        assert 'average_progress_percentage' in data
        assert 'progress_distribution' in data
        assert data['total_enrollments'] >= 1

    def test_get_course_analytics_no_data(self, client, auth_headers):
        """Test getting analytics for course with no data."""
        response = client.get('/analytics/course/999', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['course_id'] == 999
        assert data['total_enrollments'] == 0


class TestCertificateRoutes:
    """Tests for certificate routes."""

    def test_issue_certificate_success(self, client, auth_headers, completed_progress):
        """Test issuing a certificate for completed course."""
        certificate_data = {
            'user_id': 1,
            'course_id': 101,
            'certificate_url': 'https://example.com/cert/123'
        }

        response = client.post('/certificates',
                               data=json.dumps(certificate_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert data['course_id'] == 101
        assert data['certificate_url'] == 'https://example.com/cert/123'
        assert data['is_valid'] is True

    def test_issue_certificate_insufficient_completion(self, client, auth_headers, sample_progress):
        """Test issuing certificate for incomplete course fails."""
        certificate_data = {
            'user_id': 1,
            'course_id': 101,
            'certificate_url': 'https://example.com/cert/123'
        }

        response = client.post('/certificates',
                               data=json.dumps(certificate_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 'CERTIFICATE_VALIDATION_ERROR'

    def test_issue_certificate_unauthorized_user(self, client, auth_headers):
        """Test issuing certificate for another user is forbidden."""
        certificate_data = {
            'user_id': 2,  # Different user
            'course_id': 101,
            'certificate_url': 'https://example.com/cert/123'
        }

        response = client.post('/certificates',
                               data=json.dumps(certificate_data),
                               content_type='application/json',
                               headers=auth_headers)

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 'UNAUTHORIZED_ACCESS'

    def test_get_user_certificates(self, client, auth_headers):
        """Test getting user certificates."""
        # First create a certificate
        from app.models import CompletionCertificate
        from app import db

        certificate = CompletionCertificate(
            user_id=1,
            course_id=101,
            certificate_url='https://example.com/cert/test'
        )
        db.session.add(certificate)
        db.session.commit()

        response = client.get('/certificates/user/1', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
        assert data[0]['user_id'] == 1
        assert data[0]['course_id'] == 101

    def test_get_user_certificates_unauthorized(self, client, auth_headers):
        """Test getting certificates for another user is forbidden."""
        response = client.get('/certificates/user/2', headers=auth_headers)  # Different user

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 'UNAUTHORIZED_ACCESS'

    def test_get_user_certificates_empty(self, client, auth_headers):
        """Test getting certificates when user has none."""
        response = client.get('/certificates/user/1', headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 0


class TestHealthCheckRoute:
    """Tests for the comprehensive health check route."""

    def test_api_health_check_basic(self, client):
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