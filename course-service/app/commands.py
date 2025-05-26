# course-service/app/commands.py
# This file defines Flask CLI commands for background tasks, such as message consumption.
# These commands can be run independently of the main Flask web server.

import click  # Flask CLI integration
from flask.cli import with_appcontext  # Ensures Flask app context is available
from shared.message_queue import consume_messages  # Import the message consumption utility
import json  # For JSON parsing
import structlog  # For structured logging

logger = structlog.get_logger(__name__)


def process_incoming_course_event(message_data: dict):
    """
    Callback function to process incoming messages from the Service Bus queue.
    This function defines the logic for what the Course Service does when it consumes an event.
    For demonstration, it simply logs the event.
    In a real scenario, this would trigger business logic (e.g., update course data
    based on an event from the User Service, like a user type change affecting instructor status).
    """
    event_type = message_data.get('event_type')

    logger.info("Received incoming course event", event_type=event_type, raw_data=message_data)

    # Example: If Course Service needs to react to events from other services
    if event_type == 'user_registered':  # Hypothetical event from User Service
        user_id = message_data.get('user_id')
        user_type = message_data.get('user_type')
        logger.info("User registered event received", user_id=user_id, user_type=user_type)
        # If user_type is 'instructor', you might update a local cache or a view for instructors
    elif event_type == 'some_other_service_event_for_course':
        # Process other relevant events
        pass
    else:
        logger.warning("Unhandled incoming course event type", event_type=event_type, message_data=message_data)


@click.command('consume-course-events')
@with_appcontext  # Ensures the Flask application context is available for database, config, etc.
def consume_course_events_command():
    """
    Starts consuming messages from a designated Azure Service Bus queue for the Course Service.
    This command should be run in a separate process/container.
    """
    # This queue name should be the one where other services send messages that the Course Service needs to consume.
    # For demonstration, let's assume it consumes from 'course-service-incoming-events'.
    # You would define this queue in your Terraform configuration.
    queue_to_consume = 'course-service-incoming-events'
    logger.info(f"Starting consumer for '{queue_to_consume}' queue...")
    try:
        consume_messages(queue_to_consume, process_incoming_course_event)
    except Exception as e:
        logger.error(f"Consumer for '{queue_to_consume}' failed", error=str(e))
    logger.info(f"Stopped consumer for '{queue_to_consume}' queue.")

# To run this command:
# 1. Ensure your .env file is set up correctly.
# 2. Run 'flask consume-course-events' from your course-service directory.
