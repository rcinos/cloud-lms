# user-service/app/routes.py
# This file defines the API endpoints for the User Service.
# It handles incoming HTTP requests, interacts with services, and returns JSON responses.

from flask import Blueprint, request, jsonify
from app import db, cache, logger  # Import initialized extensions and logger
from app.models import User, UserProfile, Enrollment  # Import database models
from app.services import UserService, AuthService  # Import service logic
from shared.message_queue import publish_message  # Utility for publishing messages
from sqlalchemy import text
from datetime import datetime
from shared.encryption import encrypt_data  # Utility for encrypting data (for messages)
import json  # For JSON serialization
from werkzeug.exceptions import BadRequest # Import BadRequest for JSON parsing errors

bp = Blueprint('main', __name__)  # Create a Blueprint for routes
user_service = UserService()  # Instantiate user service logic
auth_service = AuthService()  # Instantiate authentication service logic


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
    Returns: A JSON response with various user-related metrics.
    """
    try:
        total_users = User.query.count()
        total_students = User.query.filter_by(user_type='student').count()
        total_instructors = User.query.filter_by(user_type='instructor').count()
        total_enrollments = Enrollment.query.count()

        metrics_data = {
            'total_users': total_users,
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_enrollments': total_enrollments,
            'service': 'user-service'
        }
        logger.info("Metrics requested", metrics=metrics_data)
        return jsonify(metrics_data), 200
    except Exception as e:
        logger.error("Error retrieving metrics", error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'METRICS_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/users', methods=['GET'])
@cache.cached(timeout=300, key_prefix='all_users')  # Cache the response for 300 seconds
def get_users():
    """
    Get all users with pagination.
    Parameters:
        page (int, optional): Page number (default: 1).
        per_page (int, optional): Items per page (default: 10, max: 100).
        type (str, optional): Filter by user type ('student' or 'instructor').
    Returns: A JSON response with a list of users and pagination info.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Limit per_page to 100
        user_type = request.args.get('type')

        query = User.query
        if user_type:
            if user_type not in ['student', 'instructor']:
                return jsonify({'error': 'Invalid user type filter', 'code': 'INVALID_USER_TYPE',
                                'timestamp': datetime.utcnow().isoformat()}), 400
            query = query.filter_by(user_type=user_type)

        # Paginate the query results
        users_pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page,
                                                                           error_out=False)

        result = {
            'users': [user.to_dict() for user in users_pagination.items],
            'pagination': {
                'page': page,
                'pages': users_pagination.pages,
                'per_page': per_page,
                'total': users_pagination.total
            }
        }

        logger.info("Retrieved users", page=page, per_page=per_page, user_type=user_type,
                    count=len(users_pagination.items))
        return jsonify(result), 200

    except Exception as e:
        logger.error("Error retrieving users", error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'USERS_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/users/<int:user_id>', methods=['GET'])
@cache.cached(timeout=300)  # Cache individual user responses
def get_user(user_id: int):
    """
    Get specific user by ID.
    Parameters:
        user_id (int): The ID of the user.
    Returns: A JSON response with the user's details.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning("User not found", user_id=user_id)
            return jsonify(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND', 'timestamp': datetime.utcnow().isoformat()}), 404

        user_data = user.to_dict(include_email=True)

        # Include profile details if available
        if user.user_profile:
            user_data['profile'] = user.user_profile.to_dict()

        logger.info("Retrieved user", user_id=user_id)
        return jsonify(user_data), 200
    except Exception as e:
        logger.error("Error retrieving user", user_id=user_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'USER_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/auth/register', methods=['POST'])
def register():
    """
    Register a new user.
    Request Body:
        email (str): User's email.
        password (str): User's password.
        user_type (str): 'student' or 'instructor'.
        first_name (str, optional): User's first name.
        last_name (str, optional): User's last name.
        phone (str, optional): User's phone number.
        bio (str, optional): User's biography.
    Returns: A JSON response with the newly created user's details.
    """
    data = None # Initialize data to None to prevent UnboundLocalError
    try:
        data = request.get_json()
        if not data:
            logger.warning("Registration failed: No JSON data provided.")
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        required_fields = ['email', 'password', 'user_type']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            logger.warning("Registration failed: Missing required fields.", missing_fields=missing_fields)
            return jsonify({'error': 'Missing required fields', 'code': 'MISSING_FIELDS',
                            'details': missing_fields, 'timestamp': datetime.utcnow().isoformat()}), 400

        if data['user_type'] not in ['student', 'instructor']:
            logger.warning("Registration failed: Invalid user type.", user_type=data['user_type'])
            return jsonify({'error': 'Invalid user type', 'code': 'INVALID_USER_TYPE',
                            'timestamp': datetime.utcnow().isoformat()}), 400

        user = user_service.create_user(data)

        # Publish user registration event to message queue
        event_data = {
            'event_type': 'user_registered',
            'user_id': user.id,
            'user_type': user.user_type,
            'email': user.get_email()  # Decrypted email for event, will be re-encrypted for message
        }

        # Encrypt sensitive data (email) within the message payload before publishing
        # The .hex() is used because bytes cannot be directly JSON serialized.
        # The consumer will need to convert hex back to bytes before decryption.
        encrypted_event = {
            'event_type': event_data['event_type'],
            'user_id': event_data['user_id'],
            'user_type': event_data['user_type'],
            'email_encrypted': encrypt_data(event_data['email']).hex()
        }

        publish_message('course-service-incoming-events', json.dumps(encrypted_event))

        logger.info("User registered and event published", user_id=user.id, user_type=user.user_type)
        return jsonify(user.to_dict()), 201

    except BadRequest as e:
        # This catches errors from request.get_json() if the payload is not valid JSON
        logger.warning("Registration failed: Malformed JSON payload.", error=str(e))
        return jsonify({'error': f'Malformed JSON: {e.description}', 'code': 'INVALID_JSON_FORMAT',
                        'timestamp': datetime.utcnow().isoformat()}), 400
    except ValueError as e:
        # This catches the ValueError raised by UserService.create_user for duplicate emails
        logger.warning("User registration failed due to invalid input.", error=str(e), request_data=data if data else 'N/A')
        return jsonify(
            {'error': str(e), 'code': 'REGISTRATION_VALIDATION_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        # Catch any other unexpected errors
        logger.error("Error registering user.", error=str(e), request_data=data if data else 'N/A')
        return jsonify({'error': 'Internal server error', 'code': 'REGISTRATION_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/auth/login', methods=['POST'])
def login():
    """
    User login endpoint.
    Request Body:
        email (str): User's email.
        password (str): User's password.
    Returns: A JSON response with a JWT token upon successful authentication.
    """
    data = None # Initialize data to None to prevent UnboundLocalError
    try:
        data = request.get_json()
        if not data:
            logger.warning("Login failed: No JSON data provided.")
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            logger.warning("Login failed: Email or password missing.")
            return jsonify({'error': 'Email and password required', 'code': 'MISSING_CREDENTIALS',
                            'timestamp': datetime.utcnow().isoformat()}), 400

        token = auth_service.authenticate_user(email, password)

        if not token:
            logger.warning("Login failed: Invalid credentials for email.", email=email)
            return jsonify({'error': 'Invalid credentials', 'code': 'INVALID_CREDENTIALS',
                            'timestamp': datetime.utcnow().isoformat()}), 401

        logger.info("User logged in successfully.", email=email)
        return jsonify({'token': token}), 200

    except BadRequest as e:
        # This catches errors from request.get_json() if the payload is not valid JSON
        logger.warning("Login failed: Malformed JSON payload.", error=str(e))
        return jsonify({'error': f'Malformed JSON: {e.description}', 'code': 'INVALID_JSON_FORMAT',
                        'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        # Catch any other unexpected errors
        # Use a check for 'email' in locals() to prevent UnboundLocalError if data parsing failed before email was extracted
        logger.error("Error during login process.", error=str(e), email=email if 'email' in locals() else 'N/A')
        return jsonify(
            {'error': 'Internal server error', 'code': 'LOGIN_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/enrollments', methods=['POST'])
def create_enrollment():
    """
    Create a new course enrollment for a user.
    Request Body:
        user_id (int): ID of the user enrolling.
        course_id (int): ID of the course to enroll in.
    Returns: A JSON response with the newly created enrollment details.
    """
    data = None # Initialize data to None
    try:
        data = request.get_json()
        if not data:
            logger.warning("Enrollment failed: No JSON data provided.")
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        required_fields = ['user_id', 'course_id']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            logger.warning("Enrollment failed: Missing required fields.", missing_fields=missing_fields)
            return jsonify({'error': 'Missing required fields', 'code': 'MISSING_FIELDS',
                            'details': missing_fields, 'timestamp': datetime.utcnow().isoformat()}), 400

        enrollment = user_service.create_enrollment(data)

        # Publish enrollment event to message queue
        event_data = {
            'event_type': 'user_enrolled',
            'enrollment_id': enrollment.id,
            'user_id': enrollment.user_id,
            'course_id': enrollment.course_id
        }
        # Publish to 'user-enrolled-events' queue (as defined in Service Bus setup)
        publish_message('progress-service-incoming-events', json.dumps(event_data))

        logger.info("User enrolled and event published", enrollment_id=enrollment.id, user_id=enrollment.user_id,
                    course_id=enrollment.course_id)
        return jsonify(enrollment.to_dict()), 201

    except BadRequest as e:
        logger.warning("Enrollment failed: Malformed JSON payload.", error=str(e))
        return jsonify({'error': f'Malformed JSON: {e.description}', 'code': 'INVALID_JSON_FORMAT',
                        'timestamp': datetime.utcnow().isoformat()}), 400
    except ValueError as e:
        logger.warning("Enrollment failed due to invalid input.", error=str(e), request_data=data if data else 'N/A')
        return jsonify(
            {'error': str(e), 'code': 'ENROLLMENT_VALIDATION_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        logger.error("Error creating enrollment.", error=str(e), request_data=data if data else 'N/A')
        return jsonify({'error': 'Internal server error', 'code': 'ENROLLMENT_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/users/<int:user_id>/enrollments', methods=['GET'])
@cache.cached(timeout=300)  # Cache user's enrollments
def get_user_enrollments(user_id: int):
    """
    Get all enrollments for a specific user.
    Parameters:
        user_id (int): The ID of the user.
    Returns: A JSON response with a list of the user's enrollments.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            logger.warning("User not found for enrollments query.", user_id=user_id)
            return jsonify(
                {'error': 'User not found', 'code': 'USER_NOT_FOUND', 'timestamp': datetime.utcnow().isoformat()}), 404

        enrollments = Enrollment.query.filter_by(user_id=user_id).all()

        logger.info("Retrieved user enrollments.", user_id=user_id, count=len(enrollments))
        return jsonify([enrollment.to_dict() for enrollment in enrollments]), 200
    except Exception as e:
        logger.error("Error retrieving user enrollments.", user_id=user_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'ENROLLMENTS_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500

@bp.route('/api/health-check', methods=['GET'])
def health_check():
    """
    Checks the connectivity to various backing services (Database, Redis, Service Bus, Azure Storage).
    Returns a JSON response indicating the status of each component.
    """
    results = {}

    # 1. Database Check (SQL Server)
    try:
        with db.session.begin(): # Start a transaction to ensure connection
            # Perform a simple query to verify database connectivity
            db.session.execute(text("SELECT 1"))
        results['database'] = {'status': 'OK', 'message': 'Successfully connected to Azure SQL Database.'}
    except Exception as e:
        results['database'] = {'status': 'ERROR', 'message': f'Database connection failed: {str(e)}'}
        logger.error("Health check: Database connection failed", error=str(e)) # Log the error

    # 2. Redis Cache Check (Azure Cache for Redis)
    try:
        test_key = "health_check_redis_key"
        test_value = "health_check_redis_value"
        cache.set(test_key, test_value, timeout=10) # Set a value with a short expiration
        retrieved_value = cache.get(test_key) # Retrieve the value
        # Ensure retrieved_value is not None and matches after decoding if it's bytes
        if retrieved_value:
            # Handle both string and bytes
            if isinstance(retrieved_value, bytes):
                retrieved_str = retrieved_value.decode('utf-8')
            else:
                retrieved_str = str(retrieved_value)

            if retrieved_str == test_value:
                results['redis_cache'] = {'status': 'OK', 'message': 'Successfully connected to Azure Cache for Redis.'}
            else:
                results['redis_cache'] = {'status': 'ERROR',
                                          'message': f'Redis set/get failed. Retrieved: {retrieved_str}'}
        else:
            results['redis_cache'] = {'status': 'ERROR', 'message': 'Redis get returned None'}

        cache.delete(test_key)  # Clean up the test key
    except Exception as e:
        results['redis_cache'] = {'status': 'ERROR', 'message': f'Redis connection failed: {str(e)}'}
        logger.error("Health check: Redis connection failed", error=str(e)) # Log the error

    # 3. Azure Service Bus Check (Sending a test message)
    # IMPORTANT: Ensure a queue named 'health-check-queue' exists in your Azure Service Bus Namespace.
    test_queue_name = "health-check-queue"
    test_message_content = {
        "source": "user-service-health-check",
        "message": "Test message from health check endpoint",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        # This calls the send_message_to_queue function from shared.message_queue
        publish_message(test_queue_name, json.dumps(test_message_content))
        results['service_bus_send'] = {'status': 'OK', 'message': f'Successfully sent test message to Service Bus queue "{test_queue_name}".'}
    except Exception as e:
        results['service_bus_send'] = {'status': 'ERROR', 'message': f'Service Bus send failed: {str(e)}'}
        logger.error("Health check: Service Bus send failed", error=str(e)) # Log the error

    # 4. Azure Storage Logging Check (Implicitly tested when logger.info is called)
    # The 'configure_logging' function in app/__init__.py sets up logging to Azure Storage Blob.
    # If the database, redis, or service bus checks encountered errors, they were logged.
    # We'll just confirm that the logging mechanism itself seems functional.
    try:
        logger.info("Health check endpoint accessed. Logging to Azure Storage Blob is configured.", component="health_check")
        results['azure_storage_logging'] = {'status': 'OK', 'message': 'Logging configured. Check Azure Storage Blob for recent logs.'}
    except Exception as e:
        # This catch might not trigger if logging errors are handled asynchronously or swallowed by the logging library.
        results['azure_storage_logging'] = {'status': 'ERROR', 'message': f'Logging setup might be problematic: {str(e)}'}
        logger.error("Health check: Logging setup problematic", error=str(e)) # Log the error

    # Determine overall status
    overall_status = "OK"
    # If any component reports an error, the overall status is DEGRADED.
    if any(res.get('status') == 'ERROR' for res in results.values()):
        overall_status = "DEGRADED"

    results['overall_status'] = overall_status

    # Return JSON response with appropriate HTTP status code
    status_code = 200 if overall_status == "OK" else 500
    return jsonify(results), status_code

