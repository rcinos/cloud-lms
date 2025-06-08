# progress-service/tests/test_services.py
# Fixed version with proper test setup for certificate issuance

import pytest
from app import db
from app.services import ProgressService
from app.models import ProgressTracking, AssessmentResult, CompletionCertificate


class TestProgressService:
    """Tests for the ProgressService class."""

    def test_create_new_progress(self, app):
        """Test creating a new progress record."""
        with app.app_context():
            service = ProgressService()
            data = {
                'user_id': 1,
                'course_id': 101,
                'completion_percentage': 25.0,
                'time_spent': 60
            }

            progress = service.update_or_create_progress(data)

            assert progress.id is not None
            assert progress.user_id == 1
            assert progress.course_id == 101
            assert progress.completion_percentage == 25.0
            assert progress.total_time_spent == 60

            # Verify it was saved to database
            saved_progress = ProgressTracking.query.get(progress.id)
            assert saved_progress is not None
            assert saved_progress.completion_percentage == 25.0

    def test_update_existing_progress(self, app, sample_progress):
        """Test updating an existing progress record."""
        with app.app_context():
            service = ProgressService()

            # Get initial time spent
            initial_time = sample_progress.total_time_spent

            update_data = {
                'user_id': sample_progress.user_id,
                'course_id': sample_progress.course_id,
                'completion_percentage': 75.0,
                'time_spent': 30  # Additional time
            }

            updated_progress = service.update_or_create_progress(update_data)

            assert updated_progress.id == sample_progress.id
            assert updated_progress.completion_percentage == 75.0
            assert updated_progress.total_time_spent == initial_time + 30

    def test_record_assessment_result(self, app, sample_progress):
        """Test recording an assessment result."""
        with app.app_context():
            service = ProgressService()
            data = {
                'user_id': 1,
                'course_id': 101,
                'assessment_id': 201,
                'score': 85.0,
                'max_score': 100.0,
                'time_taken': 30
            }

            result = service.record_assessment_result(data)

            assert result.id is not None
            assert result.user_id == 1
            assert result.assessment_id == 201
            assert result.score == 85.0
            assert result.max_score == 100.0
            assert result.percentage_score == 85.0
            assert result.attempt_number == 1
            assert result.time_taken == 30
            assert result.progress_id == sample_progress.id

    def test_record_multiple_assessment_attempts(self, app, sample_progress):
        """Test recording multiple attempts for the same assessment."""
        with app.app_context():
            service = ProgressService()

            # First attempt
            data1 = {
                'user_id': 1,
                'course_id': 101,
                'assessment_id': 201,
                'score': 75.0,
                'max_score': 100.0
            }
            result1 = service.record_assessment_result(data1)
            assert result1.attempt_number == 1

            # Second attempt
            data2 = {
                'user_id': 1,
                'course_id': 101,
                'assessment_id': 201,
                'score': 85.0,
                'max_score': 100.0
            }
            result2 = service.record_assessment_result(data2)
            assert result2.attempt_number == 2

    def test_record_assessment_with_zero_max_score(self, app):
        """Test that zero max score raises ValueError."""
        with app.app_context():
            service = ProgressService()
            data = {
                'user_id': 1,
                'course_id': 101,
                'assessment_id': 201,
                'score': 50.0,
                'max_score': 0.0
            }

            with pytest.raises(ValueError, match="Max score must be greater than zero"):
                service.record_assessment_result(data)

    def test_issue_certificate_success(self, app):
        """Test issuing a certificate for completed course."""
        with app.app_context():
            service = ProgressService()

            # Create a completed progress record
            progress = ProgressTracking(
                user_id=1,
                course_id=101,
                completion_percentage=100.0,
                total_time_spent=300
            )
            db.session.add(progress)
            db.session.commit()

            # Create at least one assessment result to get a non-zero final score
            assessment_result = AssessmentResult(
                user_id=1,
                assessment_id=201,
                score=85.0,
                max_score=100.0,
                percentage_score=85.0,
                progress_id=progress.id
            )
            db.session.add(assessment_result)
            db.session.commit()

            # Now issue certificate
            data = {
                'user_id': 1,
                'course_id': 101,
                'certificate_url': 'https://example.com/cert/123'
            }

            certificate = service.issue_certificate(data)

            assert certificate.id is not None
            assert certificate.user_id == 1
            assert certificate.course_id == 101
            assert certificate.certificate_url == 'https://example.com/cert/123'
            assert certificate.is_valid is True
            assert certificate.final_score == 85.0  # Should match the assessment result

    def test_issue_certificate_insufficient_completion(self, app, sample_progress):
        """Test that certificate issuance fails for incomplete course."""
        with app.app_context():
            service = ProgressService()
            data = {
                'user_id': sample_progress.user_id,
                'course_id': sample_progress.course_id,
                'certificate_url': 'https://example.com/cert/123'
            }

            # sample_progress has 50% completion, should fail
            with pytest.raises(ValueError, match="has not completed course.*sufficiently"):
                service.issue_certificate(data)

    def test_get_user_analytics(self, app, sample_progress, sample_assessment_result):
        """Test getting user analytics."""
        with app.app_context():
            service = ProgressService()

            analytics = service.get_user_analytics(1)

            assert analytics['user_id'] == 1
            assert analytics['total_courses_enrolled'] >= 1
            assert analytics['total_assessments_taken'] >= 1
            assert analytics['average_completion_rate'] > 0
            assert analytics['total_time_spent_minutes'] > 0
            assert 'user_email' in analytics
            assert 'completion_rate_percentage' in analytics

    def test_get_user_analytics_no_data(self, app):
        """Test getting analytics for user with no data."""
        with app.app_context():
            service = ProgressService()

            analytics = service.get_user_analytics(999)  # Non-existent user

            assert analytics['user_id'] == 999
            assert analytics['total_courses_enrolled'] == 0
            assert analytics['total_assessments_taken'] == 0
            assert analytics['average_completion_rate'] == 0.0
            assert analytics['completion_rate_percentage'] == 0.0

    def test_get_course_analytics(self, app, sample_progress, sample_assessment_result):
        """Test getting course analytics."""
        with app.app_context():
            service = ProgressService()

            analytics = service.get_course_analytics(101)

            assert analytics['course_id'] == 101
            assert analytics['total_enrollments'] >= 1
            assert analytics['average_progress_percentage'] > 0
            assert analytics['total_time_spent_minutes'] > 0
            assert 'course_title' in analytics
            assert 'progress_distribution' in analytics
            assert 'completion_rate_percentage' in analytics

    def test_get_course_analytics_no_data(self, app):
        """Test getting analytics for course with no data."""
        with app.app_context():
            service = ProgressService()

            analytics = service.get_course_analytics(999)  # Non-existent course

            assert analytics['course_id'] == 999
            assert analytics['total_enrollments'] == 0
            assert analytics['average_progress_percentage'] == 0.0
            assert analytics['completion_rate_percentage'] == 0.0