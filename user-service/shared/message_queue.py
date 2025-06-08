# shared/message_queue.py
# This module provides a centralized interface for interacting with Azure Service Bus,
# handling both message publishing (sending) and message consumption (receiving).

from azure.servicebus import ServiceBusClient, ServiceBusMessage, ServiceBusSender, ServiceBusReceiver
from flask import current_app  # To access AZURE_SERVICE_BUS_CONNECTION_STRING from Flask config
import structlog  # For structured logging
import json  # For JSON serialization/deserialization of messages

logger = structlog.get_logger(__name__)

# Dictionary to store ServiceBusSender instances for different queues
_senders = {}


def get_sender(queue_name: str) -> ServiceBusSender:
    """
    Gets or creates a Service Bus sender client for a given queue.
    This helps in reusing sender instances for efficiency.
    Args:
        queue_name (str): The name of the Service Bus queue.
    Returns:
        ServiceBusSender: An initialized Service Bus sender client.
    Raises:
        RuntimeError: If AZURE_SERVICE_BUS_CONNECTION_STRING is not configured.
        Exception: If there's an error creating the ServiceBusSender.
    """
    if queue_name not in _senders:
        connection_string = current_app.config.get('AZURE_SERVICE_BUS_CONNECTION_STRING')
        if not connection_string:
            raise RuntimeError("AZURE_SERVICE_BUS_CONNECTION_STRING not set in Flask configuration.")

        try:
            # Create a ServiceBusClient from the connection string
            servicebus_client = ServiceBusClient.from_connection_string(conn_str=connection_string)
            # Get a sender for the specified queue
            _senders[queue_name] = servicebus_client.get_queue_sender(queue_name=queue_name)
            logger.info("ServiceBusSender created", queue=queue_name)
        except Exception as e:
            logger.error("Failed to create ServiceBusSender", queue=queue_name, error=str(e))
            raise  # Re-raise the exception to indicate failure
    return _senders[queue_name]


def publish_message(queue_name: str, message_body: str):
    """
    Publishes a message (string) to the specified Azure Service Bus queue.
    The message body is encoded to UTF-8 bytes before sending.
    Args:
        queue_name (str): The name of the Service Bus queue to send to.
        message_body (str): The string content of the message.
    """
    sender = get_sender(queue_name)
    try:
        # Use 'with sender:' to ensure the sender is properly closed after sending.
        with sender:
            # Create a ServiceBusMessage from the string body (encoded to bytes).
            message = ServiceBusMessage(message_body.encode('utf-8'))
            sender.send_messages(message)  # Send the message
            logger.info("Message published to Service Bus", queue=queue_name, message_size=len(message_body))
    except Exception as e:
        logger.error("Failed to publish message to Service Bus", queue=queue_name, error=str(e))
        # In a production system, consider implementing retry logic or a dead-letter queue for failed messages.


# Dictionary to store ServiceBusReceiver instances for different queues
_receivers = {}


def get_receiver(queue_name: str) -> ServiceBusReceiver:
    """
    Gets or creates a Service Bus receiver client for a given queue.
    This helps in reusing receiver instances for efficiency.
    Args:
        queue_name (str): The name of the Service Bus queue.
    Returns:
        ServiceBusReceiver: An initialized Service Bus receiver client.
    Raises:
        RuntimeError: If AZURE_SERVICE_BUS_CONNECTION_STRING is not configured.
        Exception: If there's an error creating the ServiceBusReceiver.
    """
    if queue_name not in _receivers:
        connection_string = current_app.config.get('AZURE_SERVICE_BUS_CONNECTION_STRING')
        if not connection_string:
            raise RuntimeError("AZURE_SERVICE_BUS_CONNECTION_STRING not set in Flask configuration.")

        try:
            servicebus_client = ServiceBusClient.from_connection_string(conn_str=connection_string)
            # Get a receiver for the specified queue.
            # max_wait_time specifies how long to wait for a message before returning None.
            _receivers[queue_name] = servicebus_client.get_queue_receiver(
                queue_name=queue_name,
                max_wait_time=5  # Wait up to 5 seconds for a message
            )
            logger.info("ServiceBusReceiver created", queue=queue_name)
        except Exception as e:
            logger.error("Failed to create ServiceBusReceiver", queue=queue_name, error=str(e))
            raise
    return _receivers[queue_name]


def consume_messages(queue_name: str, callback_function):
    """
    Continuously consumes messages from the specified Azure Service Bus queue.
    Each received message is passed to the provided callback_function for processing.
    Messages are completed (removed from queue) upon successful processing,
    or abandoned (re-queued) on failure.
    Args:
        queue_name (str): The name of the Service Bus queue to consume from.
        callback_function (callable): A function that takes one argument (the parsed message body).
    """
    receiver = get_receiver(queue_name)
    logger.info("Starting message consumption", queue=queue_name)
    try:
        # Use 'with receiver:' to ensure the receiver is properly closed.
        for msg in receiver:  # This loop continuously receives messages
            try:
                message_body = msg.body.decode('utf-8')  # Decode message body from bytes to string
                message_data = json.loads(message_body)  # Parse the JSON string
                logger.info("Received message", queue=queue_name, message_id=msg.message_id,
                            event_type=message_data.get('event_type'))

                callback_function(message_data)  # Call the provided function to process the message

                receiver.complete_message(msg)  # Mark message as successfully processed and remove from queue
                logger.info("Message processed and completed", queue=queue_name, message_id=msg.message_id)
            except json.JSONDecodeError:
                logger.error("Failed to decode message body as JSON",
                             message_body=msg.body.decode('utf-8', errors='ignore'))
                receiver.dead_letter_message(msg, reason="InvalidJsonFormat",
                                             description="Message body is not valid JSON")
            except Exception as e:
                # If processing fails, log the error and abandon the message so it can be re-queued.
                logger.error("Error processing message", error=str(e),
                             message_body=msg.body.decode('utf-8', errors='ignore'))
                receiver.abandon_message(msg)  # Abandon message, it will be re-queued for another attempt
    except KeyboardInterrupt:
        logger.info("Message consumption stopped by user (KeyboardInterrupt)", queue=queue_name)
    except Exception as e:
        logger.error("Error during message consumption loop", queue=queue_name, error=str(e))

