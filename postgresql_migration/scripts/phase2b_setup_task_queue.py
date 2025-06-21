#!/usr/bin/env python3
"""
Phase 2B: PostgreSQL Task Queue Setup Script
Applies the PostgreSQL task queue schema and sets up Django models
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

import logging
from django.db import connection, transaction
from django.core.management import call_command
from django.conf import settings
from apps.core.models.task_queue import (
    TaskQueue, ScheduledTask, TaskWorker, 
    TaskExecutionHistory, WorkerHeartbeat
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_sql_schema():
    """Apply the PostgreSQL task queue schema"""
    logger.info("Applying PostgreSQL task queue schema...")
    
    schema_file = project_root / 'postgresql_migration' / 'scripts' / 'phase2b_postgresql_task_queue_schema.sql'
    
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_file, 'r') as f:
        sql_content = f.read()
    
    # Execute the SQL schema
    with connection.cursor() as cursor:
        try:
            # Split and execute SQL statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement.upper().startswith(('CREATE', 'INSERT', 'COMMENT')):
                    cursor.execute(statement)
                    logger.debug(f"Executed: {statement[:50]}...")
            
            logger.info("✅ PostgreSQL task queue schema applied successfully")
            
        except Exception as e:
            logger.error(f"❌ Error applying schema: {e}")
            raise


def create_django_migrations():
    """Create Django migrations for the task queue models"""
    logger.info("Creating Django migrations for task queue models...")
    
    try:
        # Create migrations
        call_command('makemigrations', 'core', verbosity=2)
        logger.info("✅ Django migrations created successfully")
        
        # Apply migrations
        call_command('migrate', 'core', verbosity=2)
        logger.info("✅ Django migrations applied successfully")
        
    except Exception as e:
        logger.error(f"❌ Error with Django migrations: {e}")
        raise


def setup_initial_scheduled_tasks():
    """Setup initial scheduled tasks from existing Celery configuration"""
    logger.info("Setting up initial scheduled tasks...")
    
    try:
        # Define initial scheduled tasks based on Celery analysis
        scheduled_tasks = [
            {
                'name': 'create_ppm_job',
                'task_name': 'create_ppm_job',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'cron',
                'cron_minute': '3',
                'cron_hour': '3,16',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'description': 'Create Preventive Maintenance jobs',
                'priority': 1,  # High priority
                'queue_name': 'high_priority'
            },
            {
                'name': 'auto_close_jobs',
                'task_name': 'auto_close_jobs',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 1800,  # 30 minutes
                'description': 'Auto-close expired jobs and create tickets',
                'priority': 1,  # High priority
                'queue_name': 'high_priority'
            },
            {
                'name': 'send_reminder_email',
                'task_name': 'send_reminder_email',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 28800,  # 8 hours
                'description': 'Send reminder emails for due tasks',
                'priority': 3,  # Medium priority
                'queue_name': 'email'
            },
            {
                'name': 'ticket_escalation',
                'task_name': 'ticket_escalation',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 1800,  # 30 minutes
                'description': 'Escalate overdue tickets',
                'priority': 3,  # Medium priority
                'queue_name': 'default'
            },
            {
                'name': 'create_job',
                'task_name': 'create_job',
                'task_module': 'apps.schedhuler.utils_new',
                'schedule_type': 'interval',
                'interval_seconds': 28800,  # 8 hours
                'description': 'Create scheduled jobs',
                'priority': 1,  # High priority
                'queue_name': 'high_priority'
            },
            {
                'name': 'send_generated_report_on_mail',
                'task_name': 'send_generated_report_on_mail',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 1620,  # 27 minutes
                'description': 'Send generated reports via email',
                'priority': 5,  # Medium priority
                'queue_name': 'reports'
            },
            {
                'name': 'create_scheduled_reports',
                'task_name': 'create_scheduled_reports',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 28800,  # 8 hours
                'description': 'Generate scheduled reports',
                'priority': 5,  # Medium priority
                'queue_name': 'reports'
            },
            {
                'name': 'move_media_to_cloud_storage',
                'task_name': 'move_media_to_cloud_storage',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'cron',
                'cron_minute': '0',
                'cron_hour': '0',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '1',  # Monday
                'description': 'Move files to Google Cloud Storage',
                'priority': 8,  # Low priority
                'queue_name': 'maintenance'
            },
            {
                'name': 'cleanup_expired_sessions_task',
                'task_name': 'cleanup_expired_sessions_task',
                'task_module': 'apps.core.tasks',
                'schedule_type': 'cron',
                'cron_minute': '0',
                'cron_hour': '2',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'description': 'Clean up expired PostgreSQL sessions',
                'priority': 7,  # Low priority
                'queue_name': 'maintenance'
            },
            {
                'name': 'cleanup_old_tasks',
                'task_name': 'cleanup_old_tasks',
                'task_module': 'apps.core.tasks',
                'schedule_type': 'cron',
                'cron_minute': '30',
                'cron_hour': '1',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'description': 'Clean up old completed tasks',
                'priority': 8,  # Low priority
                'queue_name': 'maintenance'
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for task_config in scheduled_tasks:
            task, created = ScheduledTask.objects.get_or_create(
                name=task_config['name'],
                defaults=task_config
            )
            
            if created:
                created_count += 1
                logger.info(f"Created scheduled task: {task.name}")
            else:
                # Update existing task configuration
                for key, value in task_config.items():
                    if key != 'name':
                        setattr(task, key, value)
                task.save()
                updated_count += 1
                logger.info(f"Updated scheduled task: {task.name}")
        
        logger.info(f"✅ Scheduled tasks setup complete: {created_count} created, {updated_count} updated")
        
    except Exception as e:
        logger.error(f"❌ Error setting up scheduled tasks: {e}")
        raise


def verify_installation():
    """Verify the task queue installation"""
    logger.info("Verifying PostgreSQL task queue installation...")
    
    try:
        # Check if tables exist
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%task%'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'task_queue',
                'scheduled_tasks',
                'task_workers',
                'task_execution_history',
                'worker_heartbeats',
                'task_dependencies',
                'task_workflows',
                'task_performance_metrics',
                'scheduled_task_executions'
            ]
            
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                logger.warning(f"⚠️  Missing tables: {missing_tables}")
            else:
                logger.info("✅ All expected tables exist")
        
        # Test Django model operations
        logger.info("Testing Django model operations...")
        
        # Test TaskQueue model
        test_task = TaskQueue(
            task_name='test_task',
            task_module='test_module',
            task_args=[],
            task_kwargs={},
            queue_name='test'
        )
        test_task.full_clean()  # Validate model
        logger.info("✅ TaskQueue model validation passed")
        
        # Check scheduled tasks count
        scheduled_count = ScheduledTask.objects.count()
        logger.info(f"✅ Scheduled tasks count: {scheduled_count}")
        
        # Test functions exist
        with connection.cursor() as cursor:
            cursor.execute("SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name LIKE '%task%'")
            functions = [row[0] for row in cursor.fetchall()]
            
            if functions:
                logger.info(f"✅ PostgreSQL functions available: {', '.join(functions)}")
            else:
                logger.warning("⚠️  No PostgreSQL functions found")
        
        logger.info("✅ Installation verification completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        raise


def print_usage_instructions():
    """Print usage instructions"""
    logger.info("\n" + "="*60)
    logger.info("📋 PostgreSQL Task Queue Setup Complete!")
    logger.info("="*60)
    
    logger.info("\n🚀 Next Steps:")
    logger.info("1. Start a worker:")
    logger.info("   python manage.py run_postgresql_worker --queues default high_priority email")
    
    logger.info("\n2. Monitor the queue:")
    logger.info("   python manage.py manage_task_queue monitor")
    
    logger.info("\n3. View statistics:")
    logger.info("   python manage.py manage_task_queue stats")
    
    logger.info("\n4. Submit a test task:")
    logger.info("   python manage.py manage_task_queue submit test_task")
    
    logger.info("\n5. View scheduled tasks:")
    logger.info("   python manage.py manage_task_queue schedule list")
    
    logger.info("\n📁 Key Components:")
    logger.info("   • Task Queue Models: apps/core/models/task_queue.py")
    logger.info("   • Worker Implementation: apps/core/tasks/postgresql_worker.py")
    logger.info("   • Management Commands: apps/core/management/commands/")
    logger.info("   • Database Schema: postgresql_migration/scripts/phase2b_postgresql_task_queue_schema.sql")
    
    logger.info("\n🔧 Worker Configuration:")
    logger.info("   • Default queues: default, high_priority, email, reports, maintenance")
    logger.info("   • Max concurrent tasks: 4 (configurable)")
    logger.info("   • Heartbeat interval: 30 seconds")
    logger.info("   • Automatic retry for failed tasks")
    
    logger.info("\n⚠️  Migration Notes:")
    logger.info("   • Celery workers can run alongside PostgreSQL workers during transition")
    logger.info("   • Gradually migrate tasks by priority: high -> medium -> low")
    logger.info("   • Monitor performance and adjust worker configuration as needed")


def main():
    """Main setup function"""
    logger.info("🚀 Starting PostgreSQL Task Queue Setup (Phase 2B)")
    logger.info("="*60)
    
    try:
        # Step 1: Apply SQL schema
        apply_sql_schema()
        
        # Step 2: Create and apply Django migrations
        create_django_migrations()
        
        # Step 3: Setup initial scheduled tasks
        setup_initial_scheduled_tasks()
        
        # Step 4: Verify installation
        verify_installation()
        
        # Step 5: Print usage instructions
        print_usage_instructions()
        
        logger.info("\n✅ PostgreSQL Task Queue setup completed successfully!")
        logger.info("🎯 Phase 2B implementation ready for testing and deployment")
        
    except Exception as e:
        logger.error(f"\n❌ Setup failed: {e}")
        logger.error("Please check the logs above for details")
        sys.exit(1)


if __name__ == '__main__':
    main()