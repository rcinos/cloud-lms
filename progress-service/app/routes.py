# progress-service/app/routes.py
# This file defines the API endpoints for the Progress Service.
# It handles incoming HTTP requests, interacts with services, and returns JSON responses.

from flask import Blueprint, request, jsonify, current_app
from app import db, cache, logger  # Import initialized extensions and logger
from app.models import ProgressTracking, AssessmentResult, CompletionCertificate  # Import database models
from app.services import ProgressService  # Import service logic
from app.utils import token_required  # Authentication/Authorization decorator
from shared.message_queue import publish_message  # Utility for publishing messages
from sqlalchemy import text  # For database health check
from datetime import datetime  # For timestamps in health check and responses
import json  # For JSON serialization of messages
import requests  # For inter-service communication (e.g., fetching user/course details)

bp = Blueprint('main', __name__)  # Create a Blueprint for routes
progress_service = ProgressService()  # Instantiate progress service logic


@bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    Returns: A JSON response indicating the service status.
    """
    logger.info("Health check requested")
    return jsonify({'status': 'healthy', 'service': 'progress-service'}), 200


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
    Returns: A JSON response with various progress-related metrics.
    """
    try:
        total_progress_records = ProgressTracking.query.count()
        total_assessments_completed = AssessmentResult.query.count()
        total_certificates_issued = CompletionCertificate.query.count()

        # Calculate average completion rate (simple average for demonstration)
        avg_completion_rate = db.session.query(db.func.avg(ProgressTracking.completion_percentage)).scalar() or 0.0

        metrics_data = {
            'total_progress_records': total_progress_records,
            'total_assessments_completed': total_assessments_completed,
            'total_certificates_issued': total_certificates_issued,
            'average_completion_rate': round(float(avg_completion_rate), 2),
            'service': 'progress-service'
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
        test_key = "health_check_redis_key_progress"
        test_value = "health_check_redis_value_progress"
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
    test_queue_name = "health-check-queue-progress"  # Ensure this queue exists in your Service Bus Namespace.
    test_message_content = {
        "source": "progress-service-health-check",
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
                    component="health_check_progress")
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


@bp.route('/progress', methods=['GET'])
@token_required
@cache.cached(timeout=300, key_prefix='all_progress')
def get_progress_records(current_user_id: int):
    """Get all progress records with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)

        # Only allow users to see their own progress records
        progress_pagination = ProgressTracking.query.filter_by(user_id=current_user_id).paginate(page=page,
                                                                                                 per_page=per_page,
                                                                                                 error_out=False)

        result = {
            'progress': [p.to_dict() for p in progress_pagination.items],
            'pagination': {
                'page': page,
                'pages': progress_pagination.pages,
                'per_page': per_page,
                'total': progress_pagination.total
            }
        }
        logger.info("Retrieved progress records", user_id=current_user_id, page=page, per_page=per_page,
                    count=len(progress_pagination.items))
        return jsonify(result), 200
    except Exception as e:
        logger.error("Error retrieving progress records", user_id=current_user_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'PROGRESS_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/progress/<int:user_id>/<int:course_id>', methods=['GET'])
@token_required
@cache.cached(timeout=300)
def get_user_course_progress(current_user_id: int, user_id: int, course_id: int):
    """Get progress for specific user and course."""
    # Ensure user can only view their own progress
    if current_user_id != user_id:
        logger.warning("Unauthorized attempt to view other user's progress", current_user_id=current_user_id,
                       requested_user_id=user_id)
        return jsonify({'error': 'Unauthorized access', 'code': 'UNAUTHORIZED_ACCESS',
                        'timestamp': datetime.utcnow().isoformat()}), 403

    try:
        progress = ProgressTracking.query.filter_by(user_id=user_id, course_id=course_id).first()
        if not progress:
            logger.warning("Progress record not found", user_id=user_id, course_id=course_id)
            return jsonify({'error': 'Progress record not found', 'code': 'PROGRESS_NOT_FOUND',
                            'timestamp': datetime.utcnow().isoformat()}), 404

        progress_data = progress.to_dict()
        progress_data['assessment_results'] = [ar.to_dict() for ar in progress.assessment_results]

        logger.info("Retrieved user course progress", user_id=user_id, course_id=course_id)
        return jsonify(progress_data), 200
    except Exception as e:
        logger.error("Error retrieving user course progress", user_id=user_id, course_id=course_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'PROGRESS_DETAIL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/progress', methods=['POST'])
@token_required
def update_or_create_progress(current_user_id: int):
    """Update or create progress record."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        required_fields = ['user_id', 'course_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields', 'code': 'MISSING_FIELDS',
                            'timestamp': datetime.utcnow().isoformat()}), 400

        # Ensure user can only update their own progress
        if current_user_id != data['user_id']:
            logger.warning("Unauthorized attempt to update other user's progress", current_user_id=current_user_id,
                           requested_user_id=data['user_id'])
            return jsonify({'error': 'Unauthorized access', 'code': 'UNAUTHORIZED_ACCESS',
                            'timestamp': datetime.utcnow().isoformat()}), 403

        progress = progress_service.update_or_create_progress(data)

        # Publish progress update event
        event_data = {
            'event_type': 'progress_updated',
            'progress_id': progress.id,
            'user_id': progress.user_id,
            'course_id': progress.course_id,
            'completion_percentage': progress.completion_percentage,
            'total_time_spent': progress.total_time_spent
        }
        publish_message('progress-events', json.dumps(event_data))  # Publish to 'progress-events' queue

        logger.info("Progress record updated/created and event published", progress_id=progress.id,
                    user_id=progress.user_id, course_id=progress.course_id)
        return jsonify(progress.to_dict()), 201

    except ValueError as e:
        logger.warning("Progress update/create failed due to invalid input", error=str(e))
        return jsonify(
            {'error': str(e), 'code': 'PROGRESS_VALIDATION_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        logger.error("Error updating/creating progress", error=str(e), request_data=data)
        return jsonify({'error': 'Internal server error', 'code': 'PROGRESS_UPDATE_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/assessments/results', methods=['POST'])
@token_required
def record_assessment_result(current_user_id: int):
    """Record assessment result."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        required_fields = ['user_id', 'assessment_id', 'score', 'max_score', 'course_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields', 'code': 'MISSING_FIELDS',
                            'timestamp': datetime.utcnow().isoformat()}), 400

        # Ensure user can only record their own assessment results
        if current_user_id != data['user_id']:
            logger.warning("Unauthorized attempt to record other user's assessment", current_user_id=current_user_id,
                           requested_user_id=data['user_id'])
            return jsonify({'error': 'Unauthorized access', 'code': 'UNAUTHORIZED_ACCESS',
                            'timestamp': datetime.utcnow().isoformat()}), 403

        result = progress_service.record_assessment_result(data)

        # Publish assessment completed event
        event_data = {
            'event_type': 'assessment_completed',
            'result_id': result.id,
            'user_id': result.user_id,
            'assessment_id': result.assessment_id,
            'score': result.score,
            'percentage_score': result.percentage_score,
            'completed_at': result.completed_at.isoformat() + "Z"
        }
        publish_message('assessment-events', json.dumps(event_data))  # Publish to 'assessment-events' queue

        logger.info("Assessment result recorded and event published", result_id=result.id, user_id=result.user_id,
                    assessment_id=result.assessment_id)
        return jsonify(result.to_dict()), 201

    except ValueError as e:
        logger.warning("Assessment result recording failed due to invalid input", error=str(e))
        return jsonify(
            {'error': str(e), 'code': 'ASSESSMENT_VALIDATION_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        logger.error("Error recording assessment result", error=str(e), request_data=data)
        return jsonify({'error': 'Internal server error', 'code': 'ASSESSMENT_RECORD_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/analytics/user/<int:user_id>', methods=['GET'])
@token_required
@cache.cached(timeout=300)
def get_user_analytics(current_user_id: int, user_id: int):
    """Get comprehensive analytics for a user."""
    if current_user_id != user_id:
        logger.warning("Unauthorized attempt to view other user's analytics", current_user_id=current_user_id,
                       requested_user_id=user_id)
        return jsonify({'error': 'Unauthorized access', 'code': 'UNAUTHORIZED_ACCESS',
                        'timestamp': datetime.utcnow().isoformat()}), 403

    try:
        analytics = progress_service.get_user_analytics(user_id)
        logger.info("Retrieved user analytics", user_id=user_id)
        return jsonify(analytics), 200
    except ValueError as e:
        logger.warning("User analytics not found or calculation failed", user_id=user_id, error=str(e))
        return jsonify(
            {'error': str(e), 'code': 'ANALYTICS_NOT_FOUND', 'timestamp': datetime.utcnow().isoformat()}), 404
    except Exception as e:
        logger.error("Error retrieving user analytics", user_id=user_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'ANALYTICS_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/analytics/course/<int:course_id>', methods=['GET'])
@token_required  # Could be instructor_required or admin_required depending on policy
@cache.cached(timeout=300)
def get_course_analytics(current_user_id: int, course_id: int):
    """Get comprehensive analytics for a course."""
    # For simplicity, allowing any authenticated user to view course analytics.
    # In a real app, this might be restricted to instructors or admins.

    try:
        analytics = progress_service.get_course_analytics(course_id)
        logger.info("Retrieved course analytics", course_id=course_id)
        return jsonify(analytics), 200
    except ValueError as e:
        logger.warning("Course analytics not found or calculation failed", course_id=course_id, error=str(e))
        return jsonify(
            {'error': str(e), 'code': 'ANALYTICS_NOT_FOUND', 'timestamp': datetime.utcnow().isoformat()}), 404
    except Exception as e:
        logger.error("Error retrieving course analytics", course_id=course_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'ANALYTICS_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/certificates', methods=['POST'])
@token_required
def issue_completion_certificate(current_user_id: int):
    """Issue completion certificate."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {'error': 'Invalid JSON data', 'code': 'INVALID_JSON', 'timestamp': datetime.utcnow().isoformat()}), 400

        required_fields = ['user_id', 'course_id', 'certificate_url']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields', 'code': 'MISSING_FIELDS',
                            'timestamp': datetime.utcnow().isoformat()}), 400

        if current_user_id != data['user_id']:
            logger.warning("Unauthorized attempt to issue certificate for other user", current_user_id=current_user_id,
                           requested_user_id=data['user_id'])
            return jsonify({'error': 'Unauthorized access', 'code': 'UNAUTHORIZED_ACCESS',
                            'timestamp': datetime.utcnow().isoformat()}), 403

        certificate = progress_service.issue_certificate(data)
        logger.info("Certificate issued", certificate_id=certificate.id, user_id=certificate.user_id,
                    course_id=certificate.course_id)
        return jsonify(certificate.to_dict()), 201

    except ValueError as e:
        logger.warning("Certificate issuance failed due to invalid input", error=str(e))
        return jsonify(
            {'error': str(e), 'code': 'CERTIFICATE_VALIDATION_ERROR', 'timestamp': datetime.utcnow().isoformat()}), 400
    except Exception as e:
        logger.error("Error issuing certificate", error=str(e), request_data=data)
        return jsonify({'error': 'Internal server error', 'code': 'CERTIFICATE_ISSUE_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500


@bp.route('/certificates/user/<int:user_id>', methods=['GET'])
@token_required
@cache.cached(timeout=300)
def get_user_certificates(current_user_id: int, user_id: int):
    """Get all certificates for a user."""
    if current_user_id != user_id:
        logger.warning("Unauthorized attempt to view other user's certificates", current_user_id=current_user_id,
                       requested_user_id=user_id)
        return jsonify({'error': 'Unauthorized access', 'code': 'UNAUTHORIZED_ACCESS',
                        'timestamp': datetime.utcnow().isoformat()}), 403

    try:
        certificates = CompletionCertificate.query.filter_by(user_id=user_id).all()
        logger.info("Retrieved user certificates", user_id=user_id, count=len(certificates))
        return jsonify([cert.to_dict() for cert in certificates]), 200
    except Exception as e:
        logger.error("Error retrieving user certificates", user_id=user_id, error=str(e))
        return jsonify({'error': 'Internal server error', 'code': 'CERTIFICATES_RETRIEVAL_ERROR',
                        'timestamp': datetime.utcnow().isoformat()}), 500
