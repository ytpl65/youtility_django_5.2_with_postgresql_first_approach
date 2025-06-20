#!/usr/bin/env python3
"""
Add periodic session cleanup task to Celery beat
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json

def create_session_cleanup_task():
    """Create periodic task for session cleanup"""
    print("⏰ Setting up periodic session cleanup task...")
    
    # Create interval schedule (every 6 hours)
    schedule, created = IntervalSchedule.objects.get_or_create(
        every=6,
        period=IntervalSchedule.HOURS,
    )
    
    if created:
        print("✅ Created 6-hour interval schedule")
    else:
        print("📋 Using existing 6-hour interval schedule")
    
    # Create or update the periodic task
    task, created = PeriodicTask.objects.update_or_create(
        name='cleanup_expired_sessions',
        defaults={
            'task': 'cleanup_expired_sessions_task',
            'interval': schedule,
            'args': json.dumps([]),
            'kwargs': json.dumps({}),
            'enabled': True,
            'description': 'Automatically clean up expired PostgreSQL sessions'
        }
    )
    
    if created:
        print("✅ Created periodic session cleanup task")
    else:
        print("🔄 Updated existing session cleanup task")
    
    print(f"📅 Task will run every {schedule.every} {schedule.period}")
    
    return task

def create_celery_task_file():
    """Create the Celery task for session cleanup"""
    print("📝 Creating Celery task file...")
    
    task_content = '''"""
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
'''
    
    # Write to apps/core/tasks.py
    tasks_file = "apps/core/tasks.py"
    
    # Check if file exists and append, or create new
    if os.path.exists(tasks_file):
        with open(tasks_file, 'r') as f:
            content = f.read()
        
        if 'cleanup_expired_sessions_task' not in content:
            with open(tasks_file, 'a') as f:
                f.write("\n" + task_content)
            print("✅ Added session cleanup task to existing tasks.py")
        else:
            print("📋 Session cleanup task already exists in tasks.py")
    else:
        with open(tasks_file, 'w') as f:
            f.write(task_content)
        print("✅ Created new tasks.py with session cleanup task")

if __name__ == "__main__":
    print("🚀 Setting up automated session cleanup...")
    print("")
    
    # Create the Celery task
    create_celery_task_file()
    
    # Create the periodic task
    create_session_cleanup_task()
    
    print("")
    print("✅ Automated Session Cleanup Setup Complete!")
    print("")
    print("🎯 Automation Benefits:")
    print("   • Sessions cleaned every 6 hours automatically")
    print("   • No manual intervention required")
    print("   • Maintains database performance")
    print("   • Prevents session table bloat")
    print("")
    print("🔧 Management:")
    print("   • Manual cleanup: python manage.py cleanup_sessions")
    print("   • Monitor via Celery Flower dashboard")
    print("   • Logs available in Django admin and log files")