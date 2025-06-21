"""
Django management command to run PostgreSQL task worker
Usage: python manage.py run_postgresql_worker
"""

import logging
from django.core.management.base import BaseCommand
from apps.core.tasks.postgresql_worker import PostgreSQLTaskWorker

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run PostgreSQL task worker to process tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-id',
            type=str,
            help='Unique worker identifier'
        )
        parser.add_argument(
            '--queues',
            nargs='+',
            default=['default'],
            help='Queue names to process (default: default)'
        )
        parser.add_argument(
            '--max-concurrent',
            type=int,
            default=4,
            help='Maximum concurrent tasks (default: 4)'
        )
        parser.add_argument(
            '--heartbeat-interval',
            type=int,
            default=30,
            help='Heartbeat interval in seconds (default: 30)'
        )
        parser.add_argument(
            '--max-task-time',
            type=int,
            default=3600,
            help='Maximum task execution time in seconds (default: 3600)'
        )
        parser.add_argument(
            '--log-level',
            type=str,
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Log level (default: INFO)'
        )
        parser.add_argument(
            '--enable-scheduler',
            action='store_true',
            default=False,
            help='Enable scheduler thread for scheduled tasks (replaces Celery Beat)'
        )
    
    def handle(self, *args, **options):
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, options['log_level']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        scheduler_status = "WITH SCHEDULER" if options['enable_scheduler'] else "WITHOUT SCHEDULER"
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting PostgreSQL task worker with queues: {options['queues']} ({scheduler_status})"
            )
        )
        
        # Create worker
        worker = PostgreSQLTaskWorker(
            worker_id=options['worker_id'],
            queues=options['queues'],
            max_concurrent_tasks=options['max_concurrent'],
            heartbeat_interval=options['heartbeat_interval'],
            max_task_execution_time=options['max_task_time'],
            enable_scheduler=options['enable_scheduler']
        )
        
        try:
            worker.start()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("Received interrupt signal, shutting down...")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Worker error: {e}")
            )
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            worker.stop()
            self.stdout.write(
                self.style.SUCCESS("Worker stopped")
            )