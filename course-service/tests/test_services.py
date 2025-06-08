# course-service/tests/test_services.py
# Tests for the service layer business logic in the Course Service.

import pytest
from app import db
from app.services import CourseService
from app.models import Course, CourseModule, Assessment


class TestCourseService:
    """Tests for the CourseService class."""

    def test_create_course_success(self, app):
        """Test creating a course successfully."""
        with app.app_context():
            import uuid
            service = CourseService()
            sample_course_data = {
                'title': f'Test Course {uuid.uuid4().hex[:8]}',
                'description': 'Test description',
                'instructor_id': 1
            }
            course = service.create_course(sample_course_data)

            assert course.id is not None
            assert course.title == sample_course_data['title']
            assert course.description == sample_course_data['description']
            assert course.instructor_id == sample_course_data['instructor_id']

            # Verify it was saved to database
            saved_course = Course.query.get(course.id)
            assert saved_course is not None
            assert saved_course.title == sample_course_data['title']

    def test_create_duplicate_course(self, app):
        """Test creating a duplicate course raises ValueError."""
        with app.app_context():
            import uuid
            service = CourseService()
            sample_course_data = {
                'title': f'Duplicate Course {uuid.uuid4().hex[:8]}',
                'description': 'Test description',
                'instructor_id': 1
            }

            # Create first course
            service.create_course(sample_course_data)

            # Try to create duplicate
            with pytest.raises(ValueError, match="Course with this title already exists"):
                service.create_course(sample_course_data)

    def test_create_module_success(self, app, sample_course, sample_module_data):
        """Test creating a module successfully."""
        with app.app_context():
            service = CourseService()
            module = service.create_module(sample_course.id, sample_module_data)

            assert module.id is not None
            assert module.course_id == sample_course.id
            assert module.title == sample_module_data['title']
            assert module.content == sample_module_data['content']
            assert module.order_index == sample_module_data['order_index']

            # Verify it was saved to database
            saved_module = CourseModule.query.get(module.id)
            assert saved_module is not None

    def test_create_module_nonexistent_course(self, app, sample_module_data):
        """Test creating a module for non-existent course raises ValueError."""
        with app.app_context():
            service = CourseService()

            with pytest.raises(ValueError, match="Course with ID 999 not found"):
                service.create_module(999, sample_module_data)

    def test_create_module_auto_order_index(self, app, sample_course):
        """Test that modules get automatic order_index when not provided."""
        with app.app_context():
            service = CourseService()

            # Create first module without order_index
            module_data_1 = {'title': 'Module 1', 'content': 'Content 1'}
            module1 = service.create_module(sample_course.id, module_data_1)

            # Create second module without order_index
            module_data_2 = {'title': 'Module 2', 'content': 'Content 2'}
            module2 = service.create_module(sample_course.id, module_data_2)

            assert module1.order_index == 1
            assert module2.order_index == 2

    def test_create_assessment_success(self, app, sample_course, sample_assessment_data):
        """Test creating an assessment successfully."""
        with app.app_context():
            service = CourseService()
            assessment = service.create_assessment(sample_course.id, sample_assessment_data)

            assert assessment.id is not None
            assert assessment.course_id == sample_course.id
            assert assessment.title == sample_assessment_data['title']
            assert assessment.description == sample_assessment_data['description']
            assert assessment.max_score == sample_assessment_data['max_score']

            # Verify it was saved to database
            saved_assessment = Assessment.query.get(assessment.id)
            assert saved_assessment is not None

    def test_create_assessment_nonexistent_course(self, app, sample_assessment_data):
        """Test creating an assessment for non-existent course raises ValueError."""
        with app.app_context():
            service = CourseService()

            with pytest.raises(ValueError, match="Course with ID 999 not found"):
                service.create_assessment(999, sample_assessment_data)

    def test_create_course_minimal_data(self, app):
        """Test creating a course with minimal required data."""
        with app.app_context():
            service = CourseService()
            minimal_data = {
                'title': 'Minimal Course',
                'instructor_id': 1
                # description is optional
            }

            course = service.create_course(minimal_data)

            assert course.id is not None
            assert course.title == 'Minimal Course'
            assert course.description is None
            assert course.instructor_id == 1

    def test_create_module_minimal_data(self, app, sample_course):
        """Test creating a module with minimal required data."""
        with app.app_context():
            service = CourseService()
            minimal_data = {
                'title': 'Minimal Module'
                # content and order_index are optional
            }

            module = service.create_module(sample_course.id, minimal_data)

            assert module.id is not None
            assert module.title == 'Minimal Module'
            assert module.content is None
            assert module.order_index == 1  # Auto-assigned

    def test_create_assessment_with_zero_max_score(self, app, sample_course):
        """Test creating an assessment with zero max score."""
        with app.app_context():
            service = CourseService()
            assessment_data = {
                'title': 'Zero Score Assessment',
                'description': 'Assessment with zero max score',
                'max_score': 0
            }

            assessment = service.create_assessment(sample_course.id, assessment_data)

            assert assessment.max_score == 0