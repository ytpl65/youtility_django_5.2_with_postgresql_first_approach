"""
Task functions for PostgreSQL Task Queue
"""

# from celery import shared_task  # Removed - using PostgreSQL Task Queue
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

# @shared_task  # Removed - using PostgreSQL Task Queue
def cleanup_expired_sessions_task():
    """
    Celery task to clean up expired sessions from PostgreSQL
    Runs periodically to maintain database performance
    """
    try:
        # Use the Django management command we created
        call_command('cleanup_sessions')
        logger.info("Session cleanup task completed successfully")
        return "Session cleanup completed"
    except Exception as e:
        logger.error(f"Session cleanup task failed: {str(e)}")
        raise

# PostgreSQL Task Queue versions (without Celery decorator)
def cleanup_expired_sessions_task_pg(retention_days=30):
    """
    PostgreSQL Task Queue version of session cleanup
    """
    try:
        call_command('cleanup_sessions', '--days', str(retention_days))
        logger.info(f"PostgreSQL session cleanup completed (retention: {retention_days} days)")
        return f"Session cleanup completed - removed sessions older than {retention_days} days"
    except Exception as e:
        logger.error(f"PostgreSQL session cleanup failed: {str(e)}")
        raise

def hello_world_task(message="Hello from PostgreSQL Task Queue!"):
    """
    Simple test task for PostgreSQL Task Queue
    """
    logger.info(f"Hello World Task executed: {message}")
    print(f"✅ Task executed successfully: {message}")
    return f"Success: {message}"

def test_task(name="Test", count=1):
    """
    Simple test task with parameters
    """
    result = f"Test task executed {count} times for {name}"
    logger.info(result)
    print(f"✅ {result}")
    return result
