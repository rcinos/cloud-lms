# progress-service/app/commands.py
# This file defines Flask CLI commands for background tasks, such as message consumption.
# These commands can be run independently of the main Flask web server.

import click  # Flask CLI integration
from flask.cli import with_appcontext  # Ensures Flask app context is available
from shared.message_queue import consume_messages  # Import the message consumption utility
import json  # For JSON parsing
import structlog  # For structured logging

logger = structlog.get_logger(__name__)


def process_incoming_progress_event(message_data: dict):
    """
    Callback function to process incoming messages from the Service Bus queue.
    This function defines the logic for what the Progress Service does when it consumes an event.
    For demonstration, it simply logs the event.
    In a real scenario, this would trigger business logic (e.g., create initial progress records
    based on user enrollment, or update assessment results).
    """
    event_type = message_data.get('event_type')

    logger.info("Received incoming progress event", event_type=event_type, raw_data=message_data)

    # Example: Progress Service consumes events from User Service (enrollment)
    if event_type == 'user_enrolled':  # Event from User Service
        user_id = message_data.get('user_id')
        course_id = message_data.get('course_id')
        enrollment_id = message_data.get('enrollment_id')
        logger.info("User enrolled event received, creating initial progress record",
                    user_id=user_id, course_id=course_id, enrollment_id=enrollment_id)
        # In a real app, you'd call a service method here to create the initial ProgressTracking entry
        # Example: progress_service.update_or_create_progress({'user_id': user_id, 'course_id': course_id, 'completion_percentage': 0.0})
    elif event_type == 'assessment_completed':  # Event from Course Service (if it publishes this)
        user_id = message_data.get('user_id')
        assessment_id = message_data.get('assessment_id')
        score = message_data.get('score')
        logger.info("Assessment completed event received", user_id=user_id, assessment_id=assessment_id, score=score)
        # You might update a progress record or related assessment result
    else:
        logger.warning("Unhandled incoming progress event type", event_type=event_type, message_data=message_data)


@click.command('consume-progress-events')
@with_appcontext  # Ensures the Flask application context is available for database, config, etc.
def consume_progress_events_command():
    """
    Starts consuming messages from a designated Azure Service Bus queue for the Progress Service.
    This command should be run in a separate process/container.
    """
    # This queue name should be the one where other services send messages that the Progress Service needs to consume.
    # For demonstration, let's assume it consumes from 'progress-service-incoming-events'.
    # You would define this queue in your Terraform configuration.
    queue_to_consume = 'progress-service-incoming-events'
    logger.info(f"Starting consumer for '{queue_to_consume}' queue...")
    try:
        consume_messages(queue_to_consume, process_incoming_progress_event)
    except Exception as e:
        logger.error(f"Consumer for '{queue_to_consume}' failed", error=str(e))
    logger.info(f"Stopped consumer for '{queue_to_consume}' queue.")

# To run this command:
# 1. Ensure your .env file is set up correctly.
# 2. Run 'flask consume-progress-events' from your progress-service directory.
