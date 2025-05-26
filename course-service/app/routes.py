# course-service/app/routes.py
# This file defines the API endpoints for the Course Service.
# It handles incoming HTTP requests, interacts with services, and returns JSON responses.

from flask import Blueprint, request, jsonify, current_app
from app import db, cache, logger  # Import initialized extensions and logger
from app.models import Course, CourseModule, Assessment  # Import database models
from app.services import CourseService  # Import service logic
from app.utils import token_required, instructor_required  # Authentication/Authorization decorators
from shared.message_queue import publish_message  # Utility for publishing messages
from sqlalchemy import text  # For database health check
from datetime import datetime  # For timestamps in health check and responses
import json  # For JSON serialization of messages
import requests  # For inter-service communication (e.g., validating instructor ID)

bp = Blueprint('main', __name__)  # Create a Blueprint for routes
course_service = CourseService()  # Instantiate course service logic


@bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    Returns: A JSON response indicating the service status.
    """
    logger.info("Health check requested")
    return jsonify({'status': 'healthy', 'service': 'course-service'}), 200


@bp.route('/ping', methods=['GET'])
def ping():
    """
    Simple ping endpoint.
    Returns: A JSON response with a 'pong' message.
    """
    logger.info("Ping requested")
    return jsonify({'message': 'pong'}), 200


@bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Service metrics endpoint.
    Returns: A JSON response with various course-related metrics.
    """
    try:
        total_courses = Course.query.count()
        total_modules = CourseModule.query.count()
        total_assessments = Assessment.query.count()

        metrics_data = {
            'total_courses': total_courses,
            'total_modules': total_modules,
            'total_assessments': total_assessments,
            'service': 'course-service'
        }
        logger.info("Metrics requested", metrics=metrics_data)
        return jsonify(metrics_data), 200
    except Exception as e:
        logger.error("Error retrieving metrics", error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'METRICS_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/api/health-check', methods=['GET'])
def api_health_check():
    """
    Checks the connectivity to various backing services (Database, Redis, Service Bus, Azure Storage).
    Returns a JSON response indicating the status of each component.
    """
    results = {}

    # 1. Database Check (PostgreSQL)
    try:
        with db.session.begin():  # Start a transaction to ensure connection
            db.session.execute(text("SELECT 1"))
        results['database'] = {'status': 'OK', 'message': 'Successfully connected to PostgreSQL Database.'}
    except Exception as e:
        results['database'] = {'status': 'ERROR', 'message': f'Database connection failed: {str(e)}'}
        logger.error("Health check: Database connection failed", error=str(e))

    # 2. Redis Cache Check (Azure Cache for Redis)
    try:
        test_key = "health_check_redis_key_course"
        test_value = "health_check_redis_value_course"
        cache.set(test_key, test_value, timeout=10)  # Set a value with a short expiration
        retrieved_value = cache.get(test_key)  # Retrieve the value
        if retrieved_value and retrieved_value.decode('utf-8') == test_value:  # Decode if bytes
            results['redis_cache'] = {'status': 'OK', 'message': 'Successfully connected to Azure Cache for Redis.'}
        else:
            results['redis_cache'] = {'status': 'ERROR',
                                      'message': f'Redis set/get failed. Retrieved: {retrieved_value}'}
        cache.delete(test_key)  # Clean up the test key
    except Exception as e:
        results['redis_cache'] = {'status': 'ERROR', 'message': f'Redis connection failed: {str(e)}'}
        logger.error("Health check: Redis connection failed", error=str(e))

    # 3. Azure Service Bus Check (Sending a test message)
    test_queue_name = "health-check-queue-course"  # Ensure this queue exists in your Service Bus Namespace.
    test_message_content = {
        "source": "course-service-health-check",
        "message": "Test message from health check endpoint",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        publish_message(test_queue_name, json.dumps(test_message_content))
        results['service_bus_send'] = {'status': 'OK',
                                       'message': f'Successfully sent test message to Service Bus queue "{test_queue_name}".'}
    except Exception as e:
        results['service_bus_send'] = {'status': 'ERROR', 'message': f'Service Bus send failed: {str(e)}'}
        logger.error("Health check: Service Bus send failed", error=str(e))

    # 4. Azure Storage Logging Check (Implicitly tested when logger.info is called)
    try:
        logger.info("Health check endpoint accessed. Logging to Azure Storage Blob is configured.",
                    component="health_check_course")
        results['azure_storage_logging'] = {'status': 'OK',
                                            'message': 'Logging configured. Check Azure Storage Blob for recent logs.'}
    except Exception as e:
        results['azure_storage_logging'] = {'status': 'ERROR',
                                            'message': f'Logging setup might be problematic: {str(e)}'}
        logger.error("Health check: Logging setup problematic", error=str(e))

    overall_status = "OK"
    if any(res.get('status') == 'ERROR' for res in results.values()):
        overall_status = "DEGRADED"

    results['overall_status'] = overall_status
    status_code = 200 if overall_status == "OK" else 500
    return jsonify(results), status_code


@bp.route('/courses', methods=['GET'])
@cache.cached(timeout=300, key_prefix='all_courses')
def get_courses():
    """Get all courses with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)

        courses_pagination = Course.query.paginate(page=page, per_page=per_page, error_out=False)

        result = {
            'courses': [course.to_dict() for course in courses_pagination.items],
            'pagination': {
                'page': page,
                'pages': courses_pagination.pages,
                'per_page': per_page,
                'total': courses_pagination.total
            }
        }
        logger.info("Retrieved courses", page=page, per_page=per_page, count=len(courses_pagination.items))
        return jsonify(result), 200
    except Exception as e:
        logger.error("Error retrieving courses", error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'COURSES_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/courses/<int:course_id>', methods=['GET'])
@cache.cached(timeout=300)
def get_course(course_id: int):
    """Get specific course by ID."""
    try:
        course = Course.query.get(course_id)
        if not course:
            logger.warning("Course not found", course_id=course_id)
            return jsonify({'error': 'Course not found', 'code': 'COURSE_NOT_FOUND',
                            'timestamp': datetime.utcnow().isoformat()}), 404

        logger.info("Retrieved course", course_id=course_id)
        return jsonify(course.to_dict()), 200
    except Exception as e:
        logger.error("Error retrieving course", course_id=course_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'COURSE_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/courses', methods=['POST'])
@instructor_required  # Only instructors can create courses
def create_course(current_user_id: int):  # current_user_id is passed by instructor_required
    """Create new course (Instructor only)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        required_fields = ['title', 'description']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields', 'code': 'MISSING_FIELDS',
                            'timestamp': datetime.utcnow().isoformat()}), 400

        # The instructor_id from the JWT token is used
        data['instructor_id'] = current_user_id

        # Optional: Validate instructor ID against User Service (inter-service communication)
        user_service_url = current_app.config.get('USER_SERVICE_URL')
        if user_service_url:
            try:
                # Assuming /users/{id} endpoint exists and returns user_type
                response = requests.get(f"{user_service_url}/users/{current_user_id}")
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                user_data = response.json()
                if user_data.get('user_type') != 'instructor':
                    return jsonify({'error': 'User is not an instructor', 'code': 'NOT_INSTRUCTOR',
                                    'timestamp': datetime.utcnow().isoformat()}), 403
            except requests.exceptions.RequestException as req_e:
                logger.error("Failed to validate instructor with User Service", instructor_id=current_user_id,
                             error=str(req_e))
                return jsonify(
                    {'error': 'Failed to validate instructor with User Service', 'code': 'USER_SERVICE_ERROR',
                     'timestamp': datetime.utcnow().isoformat()}), 500
        else:
            logger.warning("USER_SERVICE_URL not configured, skipping instructor validation via API.")

        course = course_service.create_course(data)

        # Publish course creation event
        event_data = {
            'event_type': 'course_created',
            'course_id': course.id,
            'title': course.title,
            'instructor_id': course.instructor_id,
            'created_at': course.created_at.isoformat() + "Z"
        }
        publish_message('course-events', json.dumps(event_data))  # Publish to 'course-events' queue

        logger.info("Course created and event published", course_id=course.id, instructor_id=course.instructor_id)
        return jsonify(course.to_dict()), 201

    except ValueError as e:
        logger.warning("Course creation failed due to invalid input", error=str(e))
        return jsonify(
            {'error': str(e), 'code': 'COURSE_VALIDATION_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        logger.error("Error creating course", error=str(e), request_data=data)
        return jsonify({'error': 'Internal server error', 'code': 'COURSE_CREATION_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/courses/<int:course_id>/modules', methods=['GET'])
@cache.cached(timeout=300)
def get_course_modules(course_id: int):
    """Get all modules for a course."""
    try:
        course = Course.query.get(course_id)
        if not course:
            logger.warning("Course not found for modules query", course_id=course_id)
            return jsonify({'error': 'Course not found', 'code': 'COURSE_NOT_FOUND',
                            'timestamp': datetime.utcnow().isoformat()}), 404

        modules = CourseModule.query.filter_by(course_id=course_id).order_by(CourseModule.order_index).all()

        logger.info("Retrieved course modules", course_id=course_id, count=len(modules))
        return jsonify([module.to_dict() for module in modules]), 200
    except Exception as e:
        logger.error("Error retrieving course modules", course_id=course_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'MODULES_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/courses/<int:course_id>/assessments', methods=['GET'])
@cache.cached(timeout=300)
def get_course_assessments(course_id: int):
    """Get all assessments for a course."""
    try:
        course = Course.query.get(course_id)
        if not course:
            logger.warning("Course not found for assessments query", course_id=course_id)
            return jsonify({'error': 'Course not found', 'code': 'COURSE_NOT_FOUND',
                            'timestamp': datetime.utcnow().isoformat()}), 404

        assessments = Assessment.query.filter_by(course_id=course_id).all()

        logger.info("Retrieved course assessments", course_id=course_id, count=len(assessments))
        return jsonify([assessment.to_dict() for assessment in assessments]), 200
    except Exception as e:
        logger.error("Error retrieving course assessments", course_id=course_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'ASSESSMENTS_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500
