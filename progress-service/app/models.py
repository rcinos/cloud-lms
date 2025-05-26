# progress-service/app/models.py
# This file defines the database models for the Progress Service using Flask-SQLAlchemy.
# It includes models for Progress Tracking, Assessment Results, and Completion Certificates.

from app import db # Import the SQLAlchemy instance
from datetime import datetime

class ProgressTracking(db.Model):
    __tablename__ = 'progress_tracking' # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False) # Reference to User Service's user ID
    course_id = db.Column(db.Integer, nullable=False) # Reference to Course Service's course ID
    completion_percentage = db.Column(db.Float, default=0.0) # Percentage of course completed
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow) # Last time user accessed course
    total_time_spent = db.Column(db.Integer, default=0) # Total time spent in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships:
    # One-to-many relationship with AssessmentResult
    assessment_results = db.relationship('AssessmentResult', backref='progress_record', lazy=True, cascade='all, delete-orphan')

    def to_dict(self) -> dict:
        """Converts the ProgressTracking object to a dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'completion_percentage': self.completion_percentage,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'total_time_spent': self.total_time_spent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AssessmentResult(db.Model):
    __tablename__ = 'assessment_results' # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False) # Reference to User Service's user ID
    assessment_id = db.Column(db.Integer, nullable=False) # Reference to Course Service's assessment ID
    score = db.Column(db.Float, nullable=False) # Score achieved by the user
    max_score = db.Column(db.Float, nullable=False) # Maximum possible score for the assessment
    percentage_score = db.Column(db.Float, nullable=False) # score / max_score * 100
    attempt_number = db.Column(db.Integer, default=1) # Which attempt this was
    completed_at = db.Column(db.DateTime, default=datetime.utcnow) # Timestamp of completion
    time_taken = db.Column(db.Integer) # Time taken to complete in minutes/seconds
    progress_id = db.Column(db.Integer, db.ForeignKey('progress_tracking.id'), nullable=True) # Optional link to progress record

    def to_dict(self) -> dict:
        """Converts the AssessmentResult object to a dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assessment_id': self.assessment_id,
            'score': self.score,
            'max_score': self.max_score,
            'percentage_score': self.percentage_score,
            'attempt_number': self.attempt_number,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_taken': self.time_taken,
            'progress_id': self.progress_id
        }

class CompletionCertificate(db.Model):
    __tablename__ = 'completion_certificates' # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False) # Reference to User Service's user ID
    course_id = db.Column(db.Integer, nullable=False) # Reference to Course Service's course ID
    certificate_url = db.Column(db.String(512), nullable=False) # URL to the generated certificate
    issued_at = db.Column(db.DateTime, default=datetime.utcnow) # Date of certificate issuance
    final_score = db.Column(db.Float) # Final score for the course (e.g., average of assessments)
    is_valid = db.Column(db.Boolean, default=True) # Whether the certificate is still valid

    def to_dict(self) -> dict:
        """Converts the CompletionCertificate object to a dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'certificate_url': self.certificate_url,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'final_score': self.final_score,
            'is_valid': self.is_valid
        }
