"""
Management command to migrate Celery Beat scheduled tasks to PostgreSQL ScheduledTask
This replaces the need for Celery Beat scheduler
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from apps.core.models.task_queue import ScheduledTask


class Command(BaseCommand):
    help = 'Migrate Celery Beat scheduled tasks to PostgreSQL ScheduledTask system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually creating tasks',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing scheduled tasks with the same name',
        )

    def handle(self, *args, **options):
        self.stdout.write("="*60)
        self.stdout.write(self.style.SUCCESS("🔄 CELERY BEAT TO POSTGRESQL MIGRATION"))
        self.stdout.write("="*60)
        
        # Define the Celery Beat tasks from celery.py.deprecated
        celery_beat_tasks = [
            {
                'name': 'ppm_schedule_at_minute_3_past_hour_3_and_16',
                'task_name': 'create_ppm_job',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'cron',
                'cron_minute': '3',
                'cron_hour': '3,16',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'queue_name': 'maintenance',
                'priority': 2,
                'description': 'Create preventive maintenance jobs at 3:03 AM and 4:03 PM daily'
            },
            {
                'name': 'reminder_emails_at_minute_10_past_every_8th_hour',
                'task_name': 'send_reminder_email',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'cron',
                'cron_minute': '10',
                'cron_hour': '*/8',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'queue_name': 'email',
                'priority': 3,
                'description': 'Send reminder emails every 8 hours at minute 10'
            },
            {
                'name': 'auto_close_at_every_30_minute',
                'task_name': 'auto_close_jobs',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 1800,  # 30 minutes
                'queue_name': 'default',
                'priority': 4,
                'description': 'Auto-close jobs every 30 minutes'
            },
            {
                'name': 'ticket_escalation_every_30min',
                'task_name': 'ticket_escalation',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 1800,  # 30 minutes
                'queue_name': 'default',
                'priority': 3,
                'description': 'Process ticket escalation every 30 minutes'
            },
            {
                'name': 'create_job_at_minute_27_past_every_8th_hour',
                'task_name': 'create_job',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'cron',
                'cron_minute': '27',
                'cron_hour': '*/8',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'queue_name': 'default',
                'priority': 3,
                'description': 'Create jobs every 8 hours at minute 27'
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
                'queue_name': 'maintenance',
                'priority': 5,
                'description': 'Move media files to cloud storage every Monday at midnight'
            },
            {
                'name': 'send_report_generated_on_mail',
                'task_name': 'send_generated_report_on_mail',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'interval',
                'interval_seconds': 1620,  # 27 minutes
                'queue_name': 'email',
                'priority': 4,
                'description': 'Send generated reports via email every 27 minutes'
            },
            {
                'name': 'create_reports_scheduled',
                'task_name': 'create_scheduled_reports',
                'task_module': 'background_tasks.tasks',
                'schedule_type': 'cron',
                'cron_minute': '22',
                'cron_hour': '*/8',
                'cron_day_of_month': '*',
                'cron_month': '*',
                'cron_day_of_week': '*',
                'queue_name': 'reports',
                'priority': 3,
                'description': 'Create scheduled reports every 8 hours at minute 22'
            }
        ]
        
        self.stdout.write(f"Found {len(celery_beat_tasks)} Celery Beat tasks to migrate")
        self.stdout.write("")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for task_config in celery_beat_tasks:
            try:
                task_name = task_config['name']
                
                # Check if task already exists
                existing_task = ScheduledTask.objects.filter(name=task_name).first()
                
                if existing_task and not options['replace']:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  Skipping {task_name} - Already exists")
                    )
                    skipped_count += 1
                    continue
                
                if options['dry_run']:
                    self.stdout.write(
                        self.style.SUCCESS(f"🔍 Would create: {task_name}")
                    )
                    self.stdout.write(f"   Task: {task_config['task_module']}.{task_config['task_name']}")
                    self.stdout.write(f"   Schedule: {task_config['schedule_type']}")
                    if task_config['schedule_type'] == 'cron':
                        cron_expr = f"{task_config['cron_minute']} {task_config['cron_hour']} {task_config['cron_day_of_month']} {task_config['cron_month']} {task_config['cron_day_of_week']}"
                        self.stdout.write(f"   Cron: {cron_expr}")
                    elif task_config['schedule_type'] == 'interval':
                        self.stdout.write(f"   Interval: {task_config['interval_seconds']} seconds")
                    self.stdout.write(f"   Queue: {task_config['queue_name']} (Priority: {task_config['priority']})")
                    self.stdout.write("")
                    migrated_count += 1
                    continue
                
                # Create or update the scheduled task
                if existing_task and options['replace']:
                    # Update existing task
                    for key, value in task_config.items():
                        if key != 'name':  # Don't update the name
                            setattr(existing_task, key, value)
                    
                    # Calculate next run time
                    existing_task.next_run_at = self._calculate_next_run(existing_task)
                    existing_task.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Updated: {task_name}")
                    )
                else:
                    # Create new task
                    scheduled_task = ScheduledTask.objects.create(**task_config)
                    
                    # Calculate initial next run time
                    scheduled_task.next_run_at = self._calculate_next_run(scheduled_task)
                    scheduled_task.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Created: {task_name}")
                    )
                
                self.stdout.write(f"   Task: {task_config['task_module']}.{task_config['task_name']}")
                self.stdout.write(f"   Schedule: {task_config['schedule_type']}")
                if task_config['schedule_type'] == 'cron':
                    cron_expr = f"{task_config['cron_minute']} {task_config['cron_hour']} {task_config['cron_day_of_month']} {task_config['cron_month']} {task_config['cron_day_of_week']}"
                    self.stdout.write(f"   Cron: {cron_expr}")
                elif task_config['schedule_type'] == 'interval':
                    self.stdout.write(f"   Interval: {task_config['interval_seconds']} seconds")
                self.stdout.write(f"   Queue: {task_config['queue_name']} (Priority: {task_config['priority']})")
                self.stdout.write("")
                
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error migrating {task_config['name']}: {e}")
                )
                error_count += 1
        
        # Summary
        self.stdout.write("="*60)
        self.stdout.write("📊 MIGRATION SUMMARY:")
        self.stdout.write(f"   ✅ Migrated: {migrated_count}")
        self.stdout.write(f"   ⚠️  Skipped: {skipped_count}")
        self.stdout.write(f"   ❌ Errors: {error_count}")
        self.stdout.write("="*60)
        
        if not options['dry_run']:
            self.stdout.write("")
            self.stdout.write("🚀 Next Steps:")
            self.stdout.write("1. Start PostgreSQL worker with scheduler:")
            self.stdout.write("   python3 manage.py run_postgresql_worker --enable-scheduler")
            self.stdout.write("")
            self.stdout.write("2. Monitor scheduled tasks:")
            self.stdout.write("   python3 manage.py manage_task_queue --scheduled")
            self.stdout.write("")
            self.stdout.write("3. Test scheduled tasks:")
            self.stdout.write("   python3 test_periodic_tasks.py")
            self.stdout.write("")
            self.stdout.write("✅ Celery Beat migration completed!")
    
    def _calculate_next_run(self, scheduled_task):
        """Calculate next run time for a scheduled task"""
        now = timezone.now()
        
        if scheduled_task.schedule_type == 'interval':
            # For interval tasks, start immediately or in 1 minute
            return now + timedelta(minutes=1)
        
        elif scheduled_task.schedule_type == 'cron':
            # For cron tasks, calculate next run based on current time
            # This is a simplified implementation - in production use croniter library
            if scheduled_task.cron_minute == '*/30':
                # Every 30 minutes
                next_run = now.replace(second=0, microsecond=0)
                while next_run.minute % 30 != 0:
                    next_run += timedelta(minutes=1)
                if next_run <= now:
                    next_run += timedelta(minutes=30)
                return next_run
            
            elif scheduled_task.cron_hour == '*/8':
                # Every 8 hours
                next_run = now.replace(minute=int(scheduled_task.cron_minute), second=0, microsecond=0)
                while next_run.hour % 8 != 0:
                    next_run += timedelta(hours=1)
                if next_run <= now:
                    next_run += timedelta(hours=8)
                return next_run
            
            elif scheduled_task.cron_hour == '3,16':
                # At 3 AM and 4 PM (16:00)
                next_run = now.replace(minute=int(scheduled_task.cron_minute), second=0, microsecond=0)
                if next_run.hour < 3:
                    next_run = next_run.replace(hour=3)
                elif next_run.hour < 16:
                    next_run = next_run.replace(hour=16)
                else:
                    next_run = (next_run + timedelta(days=1)).replace(hour=3)
                
                if next_run <= now:
                    if next_run.hour == 3:
                        next_run = next_run.replace(hour=16)
                    else:
                        next_run = (next_run + timedelta(days=1)).replace(hour=3)
                
                return next_run
            
            elif scheduled_task.cron_day_of_week == '1':
                # Weekly on Monday
                next_run = now.replace(hour=int(scheduled_task.cron_hour), minute=int(scheduled_task.cron_minute), second=0, microsecond=0)
                days_ahead = 0 - next_run.weekday()  # Monday is 0
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)
                return next_run
            
            else:
                # Default: run in next hour
                return now + timedelta(hours=1)
        
        return now + timedelta(minutes=5)