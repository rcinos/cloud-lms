# course-service/app/models.py
# This file defines the database models for the Course Service using Flask-SQLAlchemy.
# It includes models for Courses, Course Modules, and Assessments.

from app import db # Import the SQLAlchemy instance
from datetime import datetime

class Course(db.Model):
    __tablename__ = 'courses' # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    instructor_id = db.Column(db.Integer, nullable=False) # Reference to User Service's instructor ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships:
    # One-to-many relationship with CourseModule
    modules = db.relationship('CourseModule', backref='course', lazy=True, cascade='all, delete-orphan')
    # One-to-many relationship with Assessment
    assessments = db.relationship('Assessment', backref='course', lazy=True, cascade='all, delete-orphan')

    def to_dict(self) -> dict:
        """Converts the Course object to a dictionary for API responses."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'instructor_id': self.instructor_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CourseModule(db.Model):
    __tablename__ = 'course_modules' # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False) # Foreign key to courses table
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text) # Markdown or HTML content for the module
    order_index = db.Column(db.Integer, nullable=False) # Order within the course
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Converts the CourseModule object to a dictionary for API responses."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'content': self.content,
            'order_index': self.order_index,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Assessment(db.Model):
    __tablename__ = 'assessments' # Name of the database table

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False) # Foreign key to courses table
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    max_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Converts the Assessment object to a dictionary for API responses."""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'description': self.description,
            'max_score': self.max_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
