"""
Django management command for task queue operations
Usage: python manage.py manage_task_queue <command>
"""

import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from apps.core.models.task_queue import (
    TaskQueue, TaskWorker, ScheduledTask, 
    TaskExecutionHistory, TaskPerformanceMetrics
)
from apps.core.tasks.postgresql_worker import TaskSubmitter


class Command(BaseCommand):
    help = 'Manage PostgreSQL task queue operations'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Stats command
        stats_parser = subparsers.add_parser('stats', help='Show task queue statistics')
        stats_parser.add_argument('--queue', help='Specific queue name')
        stats_parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
        
        # Workers command
        workers_parser = subparsers.add_parser('workers', help='Show worker information')
        workers_parser.add_argument('--worker-id', help='Specific worker ID')
        
        # Submit command
        submit_parser = subparsers.add_parser('submit', help='Submit a task')
        submit_parser.add_argument('task_name', help='Task name')
        submit_parser.add_argument('--module', default='background_tasks.tasks', help='Task module')
        submit_parser.add_argument('--args', help='Task arguments (JSON)')
        submit_parser.add_argument('--kwargs', help='Task keyword arguments (JSON)')
        submit_parser.add_argument('--queue', default='default', help='Queue name')
        submit_parser.add_argument('--priority', type=int, default=5, help='Priority (1-10)')
        submit_parser.add_argument('--delay', type=int, default=0, help='Delay in seconds')
        
        # Cleanup command
        cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old tasks')
        cleanup_parser.add_argument('--days', type=int, default=30, help='Days to keep (default: 30)')
        cleanup_parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')
        
        # Retry command
        retry_parser = subparsers.add_parser('retry', help='Retry failed tasks')
        retry_parser.add_argument('--task-id', help='Specific task ID to retry')
        retry_parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
        
        # Schedule command
        schedule_parser = subparsers.add_parser('schedule', help='Manage scheduled tasks')
        schedule_parser.add_argument('action', choices=['list', 'create', 'enable', 'disable'])
        schedule_parser.add_argument('--name', help='Scheduled task name')
        schedule_parser.add_argument('--task-name', help='Task function name')
        schedule_parser.add_argument('--module', help='Task module')
        schedule_parser.add_argument('--cron', help='Cron expression')
        schedule_parser.add_argument('--interval', type=int, help='Interval in seconds')
        
        # Monitor command
        monitor_parser = subparsers.add_parser('monitor', help='Monitor task queue in real-time')
        monitor_parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds')
    
    def handle(self, *args, **options):
        command = options.get('command')
        
        if not command:
            self.print_help('manage_task_queue', '')
            return
        
        try:
            if command == 'stats':
                self.show_stats(options)
            elif command == 'workers':
                self.show_workers(options)
            elif command == 'submit':
                self.submit_task(options)
            elif command == 'cleanup':
                self.cleanup_tasks(options)
            elif command == 'retry':
                self.retry_tasks(options)
            elif command == 'schedule':
                self.manage_scheduled_tasks(options)
            elif command == 'monitor':
                self.monitor_queue(options)
            else:
                raise CommandError(f"Unknown command: {command}")
                
        except Exception as e:
            raise CommandError(f"Error executing command: {e}")
    
    def show_stats(self, options):
        """Show task queue statistics"""
        queue_name = options.get('queue')
        hours = options.get('hours', 24)
        
        since = timezone.now() - timedelta(hours=hours)
        
        # Base queryset
        qs = TaskQueue.objects.filter(created_at__gte=since)
        if queue_name:
            qs = qs.filter(queue_name=queue_name)
        
        # Overall stats
        total_tasks = qs.count()
        pending_tasks = qs.filter(status='pending').count()
        processing_tasks = qs.filter(status='processing').count()
        completed_tasks = qs.filter(status='completed').count()
        failed_tasks = qs.filter(status='failed').count()
        
        self.stdout.write(self.style.SUCCESS(f"\n=== Task Queue Statistics (Last {hours} hours) ==="))
        if queue_name:
            self.stdout.write(f"Queue: {queue_name}")
        
        self.stdout.write(f"Total Tasks: {total_tasks}")
        self.stdout.write(f"Pending: {pending_tasks}")
        self.stdout.write(f"Processing: {processing_tasks}")
        self.stdout.write(f"Completed: {completed_tasks}")
        self.stdout.write(f"Failed: {failed_tasks}")
        
        if completed_tasks > 0:
            success_rate = (completed_tasks / (completed_tasks + failed_tasks)) * 100
            self.stdout.write(f"Success Rate: {success_rate:.1f}%")
        
        # Queue breakdown
        if not queue_name:
            self.stdout.write(self.style.SUCCESS(f"\n=== Queue Breakdown ==="))
            queue_stats = qs.values('queue_name').annotate(
                total=models.Count('id'),
                pending=models.Count('id', filter=models.Q(status='pending')),
                processing=models.Count('id', filter=models.Q(status='processing')),
                completed=models.Count('id', filter=models.Q(status='completed')),
                failed=models.Count('id', filter=models.Q(status='failed'))
            ).order_by('-total')
            
            for stat in queue_stats:
                self.stdout.write(
                    f"{stat['queue_name']}: {stat['total']} total "
                    f"({stat['pending']} pending, {stat['processing']} processing, "
                    f"{stat['completed']} completed, {stat['failed']} failed)"
                )
        
        # Task type breakdown
        self.stdout.write(self.style.SUCCESS(f"\n=== Task Type Breakdown ==="))
        task_stats = qs.values('task_name').annotate(
            total=models.Count('id'),
            avg_duration=models.Avg(
                models.ExpressionWrapper(
                    models.F('completed_at') - models.F('started_at'),
                    output_field=models.DurationField()
                )
            )
        ).order_by('-total')[:10]
        
        for stat in task_stats:
            avg_duration = ""
            if stat['avg_duration']:
                seconds = stat['avg_duration'].total_seconds()
                avg_duration = f" (avg: {seconds:.1f}s)"
            
            self.stdout.write(f"{stat['task_name']}: {stat['total']}{avg_duration}")
    
    def show_workers(self, options):
        """Show worker information"""
        worker_id = options.get('worker_id')
        
        qs = TaskWorker.objects.all()
        if worker_id:
            qs = qs.filter(worker_id=worker_id)
        
        workers = qs.order_by('-last_heartbeat')
        
        self.stdout.write(self.style.SUCCESS(f"\n=== Active Workers ==="))
        
        if not workers:
            self.stdout.write("No workers found")
            return
        
        for worker in workers:
            seconds_since_heartbeat = (timezone.now() - worker.last_heartbeat).total_seconds()
            status_color = self.style.SUCCESS if worker.is_healthy else self.style.ERROR
            
            self.stdout.write(
                status_color(
                    f"Worker: {worker.worker_id} ({worker.status})\n"
                    f"  Host: {worker.hostname} (PID: {worker.pid})\n"
                    f"  Queues: {', '.join(worker.queues)}\n"
                    f"  Tasks: {worker.current_task_count}/{worker.max_concurrent_tasks}\n"
                    f"  Processed: {worker.total_tasks_processed} "
                    f"(avg: {worker.avg_task_duration_ms}ms)\n"
                    f"  Last heartbeat: {seconds_since_heartbeat:.0f}s ago\n"
                )
            )
    
    def submit_task(self, options):
        """Submit a task to the queue"""
        task_name = options['task_name']
        module = options['module']
        args = json.loads(options.get('args', '[]'))
        kwargs = json.loads(options.get('kwargs', '{}'))
        queue = options['queue']
        priority = options['priority']
        delay = options['delay']
        
        task = TaskSubmitter.submit_task(
            task_name=task_name,
            task_module=module,
            args=args,
            kwargs=kwargs,
            queue_name=queue,
            priority=priority,
            delay_seconds=delay
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Submitted task {task_name} with ID {task.id} to queue {queue}"
            )
        )
    
    def cleanup_tasks(self, options):
        """Clean up old completed/failed tasks"""
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find tasks to delete
        tasks_to_delete = TaskQueue.objects.filter(
            status__in=['completed', 'failed'],
            completed_at__lt=cutoff_date
        )
        
        count = tasks_to_delete.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} tasks older than {days} days"
                )
            )
            return
        
        if count == 0:
            self.stdout.write("No tasks to clean up")
            return
        
        # Delete tasks
        with transaction.atomic():
            deleted_count, _ = tasks_to_delete.delete()
        
        # Also clean up old execution history
        TaskExecutionHistory.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} tasks older than {days} days"
            )
        )
    
    def retry_tasks(self, options):
        """Retry failed tasks"""
        task_id = options.get('task_id')
        hours = options.get('hours', 24)
        
        if task_id:
            # Retry specific task
            try:
                task = TaskQueue.objects.get(id=task_id)
                if task.status != 'failed':
                    raise CommandError(f"Task {task_id} is not in failed status")
                
                task.retry()
                self.stdout.write(
                    self.style.SUCCESS(f"Retried task {task_id}")
                )
            except TaskQueue.DoesNotExist:
                raise CommandError(f"Task {task_id} not found")
        else:
            # Retry failed tasks from last N hours
            count = TaskQueue.objects.retry_failed_tasks(max_age_hours=hours)
            self.stdout.write(
                self.style.SUCCESS(f"Retried {count} failed tasks from last {hours} hours")
            )
    
    def manage_scheduled_tasks(self, options):
        """Manage scheduled tasks"""
        action = options['action']
        
        if action == 'list':
            tasks = ScheduledTask.objects.all().order_by('name')
            
            self.stdout.write(self.style.SUCCESS(f"\n=== Scheduled Tasks ==="))
            
            for task in tasks:
                status = "ENABLED" if task.enabled else "DISABLED"
                status_color = self.style.SUCCESS if task.enabled else self.style.WARNING
                
                schedule_info = ""
                if task.schedule_type == 'cron':
                    schedule_info = f"Cron: {task.cron_minute} {task.cron_hour} {task.cron_day_of_month} {task.cron_month} {task.cron_day_of_week}"
                elif task.schedule_type == 'interval':
                    schedule_info = f"Interval: {task.interval_seconds}s"
                
                self.stdout.write(
                    status_color(
                        f"{task.name} ({status})\n"
                        f"  Task: {task.task_module}.{task.task_name}\n"
                        f"  Schedule: {schedule_info}\n"
                        f"  Queue: {task.queue_name} (Priority: {task.priority})\n"
                        f"  Last Run: {task.last_run_at or 'Never'}\n"
                        f"  Next Run: {task.next_run_at or 'Not scheduled'}\n"
                    )
                )
        
        elif action in ['enable', 'disable']:
            name = options.get('name')
            if not name:
                raise CommandError("--name is required for enable/disable")
            
            try:
                task = ScheduledTask.objects.get(name=name)
                task.enabled = (action == 'enable')
                task.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"{'Enabled' if task.enabled else 'Disabled'} scheduled task {name}")
                )
            except ScheduledTask.DoesNotExist:
                raise CommandError(f"Scheduled task {name} not found")
        
        elif action == 'create':
            name = options.get('name')
            task_name = options.get('task_name')
            module = options.get('module')
            cron = options.get('cron')
            interval = options.get('interval')
            
            if not all([name, task_name, module]):
                raise CommandError("--name, --task-name, and --module are required for create")
            
            if not (cron or interval):
                raise CommandError("Either --cron or --interval is required")
            
            if cron:
                scheduled_task = TaskSubmitter.submit_scheduled_task(
                    name=name,
                    task_name=task_name,
                    task_module=module,
                    cron_expr=cron
                )
            else:
                scheduled_task = TaskSubmitter.submit_scheduled_task(
                    name=name,
                    task_name=task_name,
                    task_module=module,
                    interval_seconds=interval
                )
            
            self.stdout.write(
                self.style.SUCCESS(f"Created scheduled task {name}")
            )
    
    def monitor_queue(self, options):
        """Monitor task queue in real-time"""
        import time
        import os
        
        refresh_interval = options['refresh']
        
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Show current time
                self.stdout.write(
                    self.style.SUCCESS(
                        f"=== Task Queue Monitor - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} ==="
                    )
                )
                
                # Show queue stats
                total_pending = TaskQueue.objects.filter(status='pending').count()
                total_processing = TaskQueue.objects.filter(status='processing').count()
                
                self.stdout.write(f"Pending Tasks: {total_pending}")
                self.stdout.write(f"Processing Tasks: {total_processing}")
                
                # Show active workers
                active_workers = TaskWorker.objects.filter(
                    status__in=['active', 'idle', 'busy'],
                    last_heartbeat__gte=timezone.now() - timedelta(minutes=5)
                ).count()
                
                self.stdout.write(f"Active Workers: {active_workers}")
                
                # Show recent tasks
                recent_tasks = TaskQueue.objects.filter(
                    created_at__gte=timezone.now() - timedelta(minutes=5)
                ).order_by('-created_at')[:10]
                
                if recent_tasks:
                    self.stdout.write(self.style.SUCCESS(f"\n=== Recent Tasks (Last 5 minutes) ==="))
                    for task in recent_tasks:
                        status_color = {
                            'pending': self.style.WARNING,
                            'processing': self.style.NOTICE,
                            'completed': self.style.SUCCESS,
                            'failed': self.style.ERROR
                        }.get(task.status, self.style.SUCCESS)
                        
                        self.stdout.write(
                            status_color(
                                f"{task.task_name} ({task.status}) - {task.created_at.strftime('%H:%M:%S')}"
                            )
                        )
                
                self.stdout.write(f"\nRefresh every {refresh_interval}s (Ctrl+C to stop)")
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nMonitoring stopped"))


# Import Django's Count and Q for aggregation
from django.db import models