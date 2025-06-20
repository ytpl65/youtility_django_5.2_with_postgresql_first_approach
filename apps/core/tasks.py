"""
Celery task for PostgreSQL session cleanup
"""

from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task
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
