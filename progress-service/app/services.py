# progress-service/app/services.py
# This file contains the business logic for the Progress Service,
# abstracting database operations and analytics calculations.

from app import db  # Import the SQLAlchemy instance
from app.models import ProgressTracking, AssessmentResult, CompletionCertificate  # Import database models
from datetime import datetime
import requests  # For inter-service communication
from flask import current_app  # To access Flask application configuration
import json  # For JSON parsing


class ProgressService:
    def update_or_create_progress(self, data: dict) -> ProgressTracking:
        """
        Updates an existing progress record or creates a new one if it doesn't exist.
        Calculates total_time_spent.
        """
        user_id = data['user_id']
        course_id = data['course_id']

        progress = ProgressTracking.query.filter_by(user_id=user_id, course_id=course_id).first()

        if progress:
            # Update existing record
            progress.completion_percentage = data.get('completion_percentage', progress.completion_percentage)
            progress.total_time_spent += data.get('time_spent', 0)  # Add new time spent
            progress.last_accessed = datetime.utcnow()
        else:
            # Create new record
            progress = ProgressTracking(
                user_id=user_id,
                course_id=course_id,
                completion_percentage=data.get('completion_percentage', 0.0),
                total_time_spent=data.get('time_spent', 0),
                last_accessed=datetime.utcnow()
            )
            db.session.add(progress)

        db.session.commit()
        return progress

    def record_assessment_result(self, data: dict) -> AssessmentResult:
        """
        Records an assessment result and updates the associated progress tracking.
        Calculates percentage_score.
        """
        score = data['score']
        max_score = data['max_score']

        if max_score <= 0:
            raise ValueError("Max score must be greater than zero.")

        percentage_score = (score / max_score) * 100

        # Find or create associated progress record
        progress = ProgressTracking.query.filter_by(user_id=data['user_id'], course_id=data['course_id']).first()
        if not progress:
            # If no progress record exists, create a basic one
            progress = ProgressTracking(user_id=data['user_id'], course_id=data['course_id'])
            db.session.add(progress)
            db.session.flush()  # Flush to get progress.id before commit

        # Determine attempt number
        last_attempt = AssessmentResult.query.filter_by(
            user_id=data['user_id'],
            assessment_id=data['assessment_id']
        ).order_by(AssessmentResult.attempt_number.desc()).first()

        attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1

        result = AssessmentResult(
            user_id=data['user_id'],
            assessment_id=data['assessment_id'],
            score=score,
            max_score=max_score,
            percentage_score=percentage_score,
            attempt_number=attempt_number,
            time_taken=data.get('time_taken'),
            progress_id=progress.id  # Link to the progress record
        )

        db.session.add(result)
        db.session.commit()

        return result

    def issue_certificate(self, data: dict) -> CompletionCertificate:
        """
        Issues a completion certificate for a user and course.
        Requires that progress is at 100% (or a high threshold) for the course.
        """
        user_id = data['user_id']
        course_id = data['course_id']

        # Optional: Verify completion status
        progress = ProgressTracking.query.filter_by(user_id=user_id, course_id=course_id).first()
        if not progress or progress.completion_percentage < 90.0:  # Example threshold
            raise ValueError(f"User {user_id} has not completed course {course_id} sufficiently to issue certificate.")

        # Optional: Calculate final score (e.g., average of all assessments for the course)
        # This would require fetching assessments from Course Service and results for user.
        # For simplicity, we'll use a placeholder or calculate based on available results.
        avg_score_query = db.session.query(db.func.avg(AssessmentResult.percentage_score)).filter_by(
            user_id=user_id,
            progress_record=progress  # Filter by progress record
        ).scalar()
        final_score = round(float(avg_score_query), 2) if avg_score_query else 0.0

        certificate = CompletionCertificate(
            user_id=user_id,
            course_id=course_id,
            certificate_url=data['certificate_url'],
            final_score=final_score
        )

        db.session.add(certificate)
        db.session.commit()

        return certificate

    def get_user_analytics(self, user_id: int) -> dict:
        """Calculates comprehensive analytics for a specific user."""
        total_courses_enrolled = ProgressTracking.query.filter_by(user_id=user_id).count()
        completed_courses = ProgressTracking.query.filter_by(user_id=user_id, completion_percentage=100.0).count()

        avg_completion_rate = db.session.query(db.func.avg(ProgressTracking.completion_percentage)).filter_by(
            user_id=user_id).scalar() or 0.0

        total_time_spent_minutes = db.session.query(db.func.sum(ProgressTracking.total_time_spent)).filter_by(
            user_id=user_id).scalar() or 0

        total_assessments_taken = AssessmentResult.query.filter_by(user_id=user_id).count()
        avg_assessment_score = db.session.query(db.func.avg(AssessmentResult.percentage_score)).filter_by(
            user_id=user_id).scalar() or 0.0

        certificates_earned = CompletionCertificate.query.filter_by(user_id=user_id).count()

        # Fetch user details from User Service (inter-service communication)
        user_service_url = current_app.config.get('USER_SERVICE_URL')
        user_email = "N/A"
        if user_service_url:
            try:
                # This call would typically be authenticated with a service-to-service token
                response = requests.get(f"{user_service_url}/users/{user_id}")
                response.raise_for_status()
                user_data = response.json()
                user_email = user_data.get('email', 'N/A')
            except requests.exceptions.RequestException as req_e:
                current_app.logger.error("Failed to fetch user details from User Service", user_id=user_id,
                                         error=str(req_e))
                user_email = "Error fetching email"

        return {
            "user_id": user_id,
            "user_email": user_email,  # Added for more comprehensive analytics
            "total_courses_enrolled": total_courses_enrolled,
            "completed_courses": completed_courses,
            "average_completion_rate": round(float(avg_completion_rate), 2),
            "total_time_spent_minutes": total_time_spent_minutes,
            "total_assessments_taken": total_assessments_taken,
            "average_assessment_score": round(float(avg_assessment_score), 2),
            "certificates_earned": certificates_earned,
            "completion_rate_percentage": round(
                (completed_courses / total_courses_enrolled * 100) if total_courses_enrolled > 0 else 0.0, 2)
        }

    def get_course_analytics(self, course_id: int) -> dict:
        """Calculates comprehensive analytics for a specific course."""
        total_enrollments = ProgressTracking.query.filter_by(course_id=course_id).count()
        completed_students = ProgressTracking.query.filter_by(course_id=course_id, completion_percentage=100.0).count()

        avg_progress_percentage = db.session.query(db.func.avg(ProgressTracking.completion_percentage)).filter_by(
            course_id=course_id).scalar() or 0.0

        total_time_spent_minutes = db.session.query(db.func.sum(ProgressTracking.total_time_spent)).filter_by(
            course_id=course_id).scalar() or 0

        # Calculate average time per student
        average_time_per_student = (total_time_spent_minutes / total_enrollments) if total_enrollments > 0 else 0.0

        certificates_issued = CompletionCertificate.query.filter_by(course_id=course_id).count()

        # Progress distribution (example calculation, can be more sophisticated)
        progress_distribution = {
            "0-25%": ProgressTracking.query.filter_by(course_id=course_id).filter(
                ProgressTracking.completion_percentage >= 0, ProgressTracking.completion_percentage < 25).count(),
            "25-50%": ProgressTracking.query.filter_by(course_id=course_id).filter(
                ProgressTracking.completion_percentage >= 25, ProgressTracking.completion_percentage < 50).count(),
            "50-75%": ProgressTracking.query.filter_by(course_id=course_id).filter(
                ProgressTracking.completion_percentage >= 50, ProgressTracking.completion_percentage < 75).count(),
            "75-100%": ProgressTracking.query.filter_by(course_id=course_id).filter(
                ProgressTracking.completion_percentage >= 75, ProgressTracking.completion_percentage <= 100).count(),
        }

        # Fetch course details from Course Service (inter-service communication)
        course_title = "N/A"
        course_service_url = current_app.config.get('COURSE_SERVICE_URL')
        if course_service_url:
            try:
                response = requests.get(f"{course_service_url}/courses/{course_id}")
                response.raise_for_status()
                course_data = response.json()
                course_title = course_data.get('title', 'N/A')
            except requests.exceptions.RequestException as req_e:
                current_app.logger.error("Failed to fetch course details from Course Service", course_id=course_id,
                                         error=str(req_e))
                course_title = "Error fetching title"

        return {
            "course_id": course_id,
            "course_title": course_title,  # Added for more comprehensive analytics
            "total_enrollments": total_enrollments,
            "completed_students": completed_students,
            "completion_rate_percentage": round(
                (completed_students / total_enrollments * 100) if total_enrollments > 0 else 0.0, 2),
            "average_progress_percentage": round(float(avg_progress_percentage), 2),
            "total_time_spent_minutes": total_time_spent_minutes,
            "average_time_per_student": round(float(average_time_per_student), 2),
            "certificates_issued": certificates_issued,
            "progress_distribution": progress_distribution
        }
