# progress-service/tests/test_models.py
# Tests for the database models in the Progress Service.

import pytest
from app import db
from app.models import ProgressTracking, AssessmentResult, CompletionCertificate
from datetime import datetime


class TestProgressTrackingModel:
    """Tests for the ProgressTracking model."""

    def test_create_progress_tracking(self, app):
        """Test creating a new progress tracking record."""
        with app.app_context():
            progress = ProgressTracking(
                user_id=1,
                course_id=101,
                completion_percentage=75.5,
                total_time_spent=180
            )

            db.session.add(progress)
            db.session.commit()

            assert progress.id is not None
            assert progress.user_id == 1
            assert progress.course_id == 101
            assert progress.completion_percentage == 75.5
            assert progress.total_time_spent == 180
            assert isinstance(progress.created_at, datetime)
            assert isinstance(progress.updated_at, datetime)
            assert isinstance(progress.last_accessed, datetime)

    def test_progress_to_dict(self, app):
        """Test converting progress to dictionary."""
        with app.app_context():
            progress = ProgressTracking(
                user_id=2,
                course_id=102,
                completion_percentage=25.0,
                total_time_spent=60
            )

            db.session.add(progress)
            db.session.commit()

            progress_dict = progress.to_dict()

            assert 'id' in progress_dict
            assert 'user_id' in progress_dict
            assert 'course_id' in progress_dict
            assert 'completion_percentage' in progress_dict
            assert 'last_accessed' in progress_dict
            assert 'total_time_spent' in progress_dict
            assert 'created_at' in progress_dict
            assert 'updated_at' in progress_dict

            assert progress_dict['user_id'] == 2
            assert progress_dict['course_id'] == 102
            assert progress_dict['completion_percentage'] == 25.0
            assert progress_dict['total_time_spent'] == 60

    def test_progress_relationships(self, app):
        """Test progress relationships with assessment results."""
        with app.app_context():
            progress = ProgressTracking(user_id=1, course_id=101)
            db.session.add(progress)
            db.session.commit()

            # Create assessment results linked to this progress
            result1 = AssessmentResult(
                user_id=1,
                assessment_id=201,
                score=80.0,
                max_score=100.0,
                percentage_score=80.0,
                progress_id=progress.id
            )
            result2 = AssessmentResult(
                user_id=1,
                assessment_id=202,
                score=90.0,
                max_score=100.0,
                percentage_score=90.0,
                progress_id=progress.id
            )

            db.session.add_all([result1, result2])
            db.session.commit()

            # Test relationship
            assert len(progress.assessment_results) == 2
            assert progress.assessment_results[0].score in [80.0, 90.0]
            assert progress.assessment_results[1].score in [80.0, 90.0]


class TestAssessmentResultModel:
    """Tests for the AssessmentResult model."""

    def test_create_assessment_result(self, app):
        """Test creating an assessment result."""
        with app.app_context():
            result = AssessmentResult(
                user_id=1,
                assessment_id=201,
                score=85.0,
                max_score=100.0,
                percentage_score=85.0,
                attempt_number=2,
                time_taken=45
            )

            db.session.add(result)
            db.session.commit()

            assert result.id is not None
            assert result.user_id == 1
            assert result.assessment_id == 201
            assert result.score == 85.0
            assert result.max_score == 100.0
            assert result.percentage_score == 85.0
            assert result.attempt_number == 2
            assert result.time_taken == 45
            assert isinstance(result.completed_at, datetime)

    def test_assessment_result_to_dict(self, app):
        """Test converting assessment result to dictionary."""
        with app.app_context():
            result = AssessmentResult(
                user_id=1,
                assessment_id=301,
                score=92.5,
                max_score=100.0,
                percentage_score=92.5
            )

            db.session.add(result)
            db.session.commit()

            result_dict = result.to_dict()

            assert 'id' in result_dict
            assert 'user_id' in result_dict
            assert 'assessment_id' in result_dict
            assert 'score' in result_dict
            assert 'max_score' in result_dict
            assert 'percentage_score' in result_dict
            assert 'attempt_number' in result_dict
            assert 'completed_at' in result_dict
            assert 'time_taken' in result_dict
            assert 'progress_id' in result_dict

            assert result_dict['score'] == 92.5
            assert result_dict['percentage_score'] == 92.5


class TestCompletionCertificateModel:
    """Tests for the CompletionCertificate model."""

    def test_create_completion_certificate(self, app):
        """Test creating a completion certificate."""
        with app.app_context():
            certificate = CompletionCertificate(
                user_id=1,
                course_id=101,
                certificate_url='https://example.com/cert/123',
                final_score=88.5
            )

            db.session.add(certificate)
            db.session.commit()

            assert certificate.id is not None
            assert certificate.user_id == 1
            assert certificate.course_id == 101
            assert certificate.certificate_url == 'https://example.com/cert/123'
            assert certificate.final_score == 88.5
            assert certificate.is_valid is True
            assert isinstance(certificate.issued_at, datetime)

    def test_certificate_to_dict(self, app):
        """Test converting certificate to dictionary."""
        with app.app_context():
            certificate = CompletionCertificate(
                user_id=2,
                course_id=102,
                certificate_url='https://example.com/cert/456',
                final_score=95.0,
                is_valid=False
            )

            db.session.add(certificate)
            db.session.commit()

            cert_dict = certificate.to_dict()

            assert 'id' in cert_dict
            assert 'user_id' in cert_dict
            assert 'course_id' in cert_dict
            assert 'certificate_url' in cert_dict
            assert 'issued_at' in cert_dict
            assert 'final_score' in cert_dict
            assert 'is_valid' in cert_dict

            assert cert_dict['user_id'] == 2
            assert cert_dict['course_id'] == 102
            assert cert_dict['final_score'] == 95.0
            assert cert_dict['is_valid'] is False