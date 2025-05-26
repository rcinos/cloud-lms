# course-service/app/services.py
# This file contains the business logic for the Course Service,
# abstracting database operations.

from app import db  # Import the SQLAlchemy instance
from app.models import Course, CourseModule, Assessment  # Import database models
from datetime import datetime  # For timestamps


class CourseService:
    def create_course(self, data: dict) -> Course:
        """
        Creates a new course.
        Raises ValueError if a course with the same title already exists for this instructor.
        """
        # Optional: Check for duplicate course titles by the same instructor
        existing_course = Course.query.filter_by(
            title=data['title'],
            instructor_id=data['instructor_id']
        ).first()
        if existing_course:
            raise ValueError('Course with this title already exists for this instructor.')

        course = Course(
            title=data['title'],
            description=data.get('description'),
            instructor_id=data['instructor_id']
        )

        db.session.add(course)
        db.session.commit()

        return course

    def create_module(self, course_id: int, data: dict) -> CourseModule:
        """
        Creates a new module for a given course.
        Ensures the course exists and handles order_index.
        """
        course = Course.query.get(course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found.")

        # Determine the next order_index
        max_order_index = db.session.query(db.func.max(CourseModule.order_index)).filter_by(
            course_id=course_id).scalar()
        next_order_index = (max_order_index or 0) + 1

        module = CourseModule(
            course_id=course_id,
            title=data['title'],
            content=data.get('content'),
            order_index=data.get('order_index', next_order_index)
        )

        db.session.add(module)
        db.session.commit()

        return module

    def create_assessment(self, course_id: int, data: dict) -> Assessment:
        """
        Creates a new assessment for a given course.
        Ensures the course exists.
        """
        course = Course.query.get(course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found.")

        assessment = Assessment(
            course_id=course_id,
            title=data['title'],
            description=data.get('description'),
            max_score=data['max_score']
        )

        db.session.add(assessment)
        db.session.commit()

        return assessment
