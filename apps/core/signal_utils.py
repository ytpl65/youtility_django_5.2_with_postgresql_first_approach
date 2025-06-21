"""
Utility functions for signals that need to queue background tasks
Provides PostgreSQL task queue integration for Django signals
"""

import logging
from apps.core.mqtt_adapter import PostgreSQLTaskAdapter

logger = logging.getLogger(__name__)


def queue_mqtt_task(topic, payload, priority=3):
    """
    Queue an MQTT publish task using PostgreSQL task queue
    
    Args:
        topic (str): MQTT topic
        payload (str): Message payload
        priority (int): Task priority (1-10, lower is higher priority)
    """
    try:
        adapter = PostgreSQLTaskAdapter()
        result = adapter.delay_task(
            'publish_mqtt', 
            topic, 
            payload,
            queue_name='mqtt',
            priority=priority
        )
        logger.debug(f"Queued MQTT task {result.task_id} for topic {topic}")
        return result
    except Exception as e:
        logger.error(f"Failed to queue MQTT task for topic {topic}: {e}")
        # Fallback: try to publish directly (synchronously)
        try:
            from background_tasks.tasks import publish_mqtt
            publish_mqtt(topic, payload)
            logger.info(f"Published MQTT message directly for topic {topic}")
        except Exception as sync_error:
            logger.error(f"Failed to publish MQTT directly for topic {topic}: {sync_error}")
        return None


def queue_background_task(task_name, *args, queue_name='default', priority=5, **kwargs):
    """
    Queue any background task using PostgreSQL task queue
    
    Args:
        task_name (str): Name of the task function
        *args: Positional arguments for the task
        queue_name (str): Queue name (default: 'default')
        priority (int): Task priority (1-10, lower is higher priority)  
        **kwargs: Keyword arguments for the task
    """
    try:
        adapter = PostgreSQLTaskAdapter()
        result = adapter.delay_task(
            task_name,
            *args,
            queue_name=queue_name,
            priority=priority,
            **kwargs
        )
        logger.debug(f"Queued task {task_name} with ID {result.task_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to queue task {task_name}: {e}")
        return None