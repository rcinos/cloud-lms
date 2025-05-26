# user-service/app/commands.py
# This file defines Flask CLI commands for background tasks, such as message consumption.
# These commands can be run independently of the main Flask web server.

import click  # Flask CLI integration
from flask.cli import with_appcontext  # Ensures Flask app context is available
from shared.message_queue import consume_messages  # Import the message consumption utility
from shared.encryption import decrypt_data  # For decrypting incoming PII data in messages
import json  # For JSON parsing
import structlog  # For structured logging
import binascii  # For converting hex to bytes

logger = structlog.get_logger(__name__)


def process_incoming_event(message_data: dict):
    """
    Callback function to process incoming messages from the Service Bus queue.
    This function defines the logic for what the User Service does when it consumes an event.
    For demonstration, it simply logs the event and decrypts email if present.
    In a real scenario, this would trigger business logic (e.g., update a user status
    based on an event from the Progress Service).
    """
    event_type = message_data.get('event_type')
    user_id = message_data.get('user_id')

    logger.info("Received incoming event", event_type=event_type, user_id=user_id, raw_data=message_data)

    # Example: Decrypt email if it's an event that contains encrypted PII
    if 'email_encrypted' in message_data:
        try:
            # Convert hex string back to bytes before decrypting
            encrypted_email_bytes = binascii.unhexlify(message_data['email_encrypted'])
            decrypted_email = decrypt_data(encrypted_email_bytes)
            logger.info("Decrypted email from incoming event", decrypted_email=decrypted_email)
            # You would then use this decrypted email for further processing if needed
        except Exception as e:
            logger.error("Failed to decrypt email from incoming event", error=str(e))

    # Add specific logic for different event types that this service might consume
    if event_type == 'course_completed_by_user':  # Hypothetical event from Progress Service
        logger.info("User completed a course", user_id=user_id, course_id=message_data.get('course_id'))
        # Example: Update user's profile or send a notification
    elif event_type == 'instructor_assigned_to_course':  # Hypothetical event from Course Service
        logger.info("Instructor assigned to course", instructor_id=user_id, course_id=message_data.get('course_id'))
        # Example: Update instructor's internal course list or permissions
    else:
        logger.warning("Unhandled incoming event type", event_type=event_type, message_data=message_data)


@click.command('consume-incoming-events')
@with_appcontext  # Ensures the Flask application context is available for database, config, etc.
def consume_incoming_events_command():
    """
    Starts consuming messages from a designated Azure Service Bus queue for the User Service.
    This command should be run in a separate process/container.
    """
    # This queue name should be the one where other services send messages that the User Service needs to consume.
    # For demonstration, let's assume it consumes from 'user-service-incoming-events'.
    # You would define this queue in your Terraform configuration.
    queue_to_consume = 'user-service-incoming-events'
    logger.info(f"Starting consumer for '{queue_to_consume}' queue...")
    try:
        consume_messages(queue_to_consume, process_incoming_event)
    except Exception as e:
        logger.error(f"Consumer for '{queue_to_consume}' failed", error=str(e))
    logger.info(f"Stopped consumer for '{queue_to_consume}' queue.")

# To run this command:
# 1. Ensure your .env file is set up correctly.
# 2. Run 'flask consume-incoming-events' from your user-service directory.
