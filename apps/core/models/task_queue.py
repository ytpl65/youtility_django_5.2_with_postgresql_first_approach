"""
PostgreSQL Task Queue Models
Phase 2B: Celery/Redis to PostgreSQL Migration
"""

import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal

from django.db import models, transaction
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


def serialize_result(result: Any) -> Any:
    """
    Serialize task result to JSON-compatible format
    Handles datetime, Decimal, and other non-serializable objects
    """
    if result is None:
        return None
    
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return str(obj)
    
    try:
        # First try regular JSON serialization
        json.dumps(result)
        return result
    except (TypeError, ValueError):
        # If that fails, try to convert problematic objects
        try:
            if isinstance(result, dict):
                return {k: serialize_result(v) for k, v in result.items()}
            elif isinstance(result, (list, tuple)):
                return [serialize_result(item) for item in result]
            elif isinstance(result, datetime):
                return result.isoformat()
            elif isinstance(result, Decimal):
                return float(result)
            else:
                return str(result)
        except Exception as e:
            # Last resort: convert to string
            logger.warning(f"Could not serialize result, converting to string: {e}")
            return str(result)


class TaskQueueManager(models.Manager):
    """Custom manager for TaskQueue with common queries"""
    
    def pending_tasks(self, queue_name: str = None, priority_order: bool = True):
        """Get pending tasks, optionally filtered by queue and ordered by priority"""
        qs = self.filter(
            status='pending',
            scheduled_at__lte=timezone.now()
        )
        
        if queue_name:
            qs = qs.filter(queue_name=queue_name)
            
        if priority_order:
            qs = qs.order_by('priority', 'created_at')
            
        return qs
    
    def get_next_task(self, queue_names: List[str] = None, worker_id: str = None):
        """Get next available task and mark it as processing"""
        with transaction.atomic():
            qs = self.select_for_update(skip_locked=True).filter(
                status='pending',
                scheduled_at__lte=timezone.now()
            )
            
            if queue_names:
                qs = qs.filter(queue_name__in=queue_names)
                
            task = qs.order_by('priority', 'created_at').first()
            
            if task:
                task.status = 'processing'
                task.started_at = timezone.now()
                task.worker_id = worker_id
                task.save(update_fields=['status', 'started_at', 'worker_id'])
                
            return task
    
    def retry_failed_tasks(self, max_age_hours: int = 24):
        """Retry failed tasks that are within retry limits"""
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
        
        failed_tasks = self.filter(
            status='failed',
            completed_at__gte=cutoff_time,
            retry_count__lt=models.F('max_retries')
        )
        
        count = 0
        for task in failed_tasks:
            task.retry()
            count += 1
            
        return count


class TaskQueue(models.Model):
    """Main task queue table"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    PRIORITY_CHOICES = [(i, f'Priority {i}') for i in range(1, 11)]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_name = models.CharField(max_length=255, db_index=True)
    task_module = models.CharField(max_length=255)
    task_args = models.JSONField(default=list)
    task_kwargs = models.JSONField(default=dict)
    
    # Task scheduling and execution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=5, db_index=True)
    queue_name = models.CharField(max_length=100, default='default', db_index=True)
    
    # Timing information
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    scheduled_at = models.DateTimeField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Retry mechanism
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=60)  # seconds
    
    # Worker assignment
    worker_id = models.CharField(max_length=100, blank=True, db_index=True)
    worker_hostname = models.CharField(max_length=255, blank=True)
    worker_pid = models.IntegerField(null=True, blank=True)
    
    # Result storage
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    traceback = models.TextField(blank=True)
    
    # Metadata
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    tenant_id = models.IntegerField(null=True, blank=True, db_index=True)
    created_by = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list)
    
    objects = TaskQueueManager()
    
    class Meta:
        db_table = 'task_queue'
        indexes = [
            models.Index(fields=['status', 'priority', 'scheduled_at', 'queue_name'], name='idx_task_pickup'),
            models.Index(fields=['expires_at'], name='idx_task_expires', condition=models.Q(expires_at__isnull=False)),
        ]
    
    def __str__(self):
        return f"{self.task_name} ({self.status})"
    
    def clean(self):
        """Validate task configuration"""
        if self.priority < 1 or self.priority > 10:
            raise ValidationError("Priority must be between 1 and 10")
        
        if self.max_retries < 0:
            raise ValidationError("Max retries cannot be negative")
        
        if self.retry_delay < 0:
            raise ValidationError("Retry delay cannot be negative")
    
    def retry(self):
        """Retry a failed task"""
        if self.retry_count >= self.max_retries:
            raise ValidationError("Task has exceeded maximum retry attempts")
        
        self.status = 'pending'
        self.retry_count += 1
        self.scheduled_at = timezone.now() + timedelta(seconds=self.retry_delay * (2 ** self.retry_count))
        self.started_at = None
        self.completed_at = None
        self.worker_id = ''
        self.worker_hostname = ''
        self.worker_pid = None
        self.error_message = ''
        self.traceback = ''
        self.save()
    
    def mark_completed(self, result: Any = None):
        """Mark task as completed with optional result"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result is not None:
            self.result = serialize_result(result)
        self.save(update_fields=['status', 'completed_at', 'result'])
    
    def mark_failed(self, error_message: str, traceback: str = ''):
        """Mark task as failed with error information"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.traceback = traceback
        self.save(update_fields=['status', 'completed_at', 'error_message', 'traceback'])
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate task duration if started and completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_expired(self) -> bool:
        """Check if task has expired"""
        return self.expires_at and timezone.now() > self.expires_at
    
    def get_full_task_name(self) -> str:
        """Get full task name including module"""
        return f"{self.task_module}.{self.task_name}"


class TaskExecutionHistory(models.Model):
    """Task execution history for audit and monitoring"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(TaskQueue, on_delete=models.CASCADE, related_name='execution_history')
    
    # Execution details
    status = models.CharField(max_length=20, choices=TaskQueue.STATUS_CHOICES)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    # Worker information
    worker_id = models.CharField(max_length=100, blank=True)
    worker_hostname = models.CharField(max_length=255, blank=True)
    worker_pid = models.IntegerField(null=True, blank=True)
    
    # Result and error information
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    traceback = models.TextField(blank=True)
    
    # Performance metrics
    memory_usage_mb = models.IntegerField(null=True, blank=True)
    cpu_time_ms = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'task_execution_history'
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['created_at']),
        ]


class ScheduledTaskManager(models.Manager):
    """Manager for scheduled tasks"""
    
    def due_tasks(self):
        """Get tasks that are due for execution"""
        return self.filter(
            enabled=True,
            next_run_at__lte=timezone.now()
        ).exclude(
            one_off=True,
            last_run_at__isnull=False
        )
    
    def create_from_cron(self, name: str, task_name: str, task_module: str, 
                        cron_expr: str, **kwargs):
        """Create scheduled task from cron expression"""
        # Parse cron expression (minute hour day month day_of_week)
        cron_parts = cron_expr.split()
        if len(cron_parts) != 5:
            raise ValidationError("Cron expression must have 5 parts")
        
        return self.create(
            name=name,
            task_name=task_name,
            task_module=task_module,
            schedule_type='cron',
            cron_minute=cron_parts[0],
            cron_hour=cron_parts[1],
            cron_day_of_month=cron_parts[2],
            cron_month=cron_parts[3],
            cron_day_of_week=cron_parts[4],
            **kwargs
        )


class ScheduledTask(models.Model):
    """Scheduled task definitions (Celery Beat replacement)"""
    
    SCHEDULE_TYPE_CHOICES = [
        ('cron', 'Cron'),
        ('interval', 'Interval'),
        ('once', 'Once'),
    ]
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    task_name = models.CharField(max_length=255)
    task_module = models.CharField(max_length=255)
    
    # Scheduling configuration
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES)
    
    # Cron schedule
    cron_minute = models.CharField(max_length=20, blank=True)
    cron_hour = models.CharField(max_length=20, blank=True)
    cron_day_of_month = models.CharField(max_length=20, blank=True)
    cron_month = models.CharField(max_length=20, blank=True)
    cron_day_of_week = models.CharField(max_length=20, blank=True)
    
    # Interval schedule
    interval_seconds = models.IntegerField(null=True, blank=True)
    
    # Task configuration
    task_args = models.JSONField(default=list)
    task_kwargs = models.JSONField(default=dict)
    queue_name = models.CharField(max_length=100, default='default')
    priority = models.IntegerField(choices=TaskQueue.PRIORITY_CHOICES, default=5)
    
    # Control flags
    enabled = models.BooleanField(default=True, db_index=True)
    one_off = models.BooleanField(default=False)
    
    # Timing
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    tenant_id = models.IntegerField(null=True, blank=True)
    
    objects = ScheduledTaskManager()
    
    class Meta:
        db_table = 'scheduled_tasks'
        indexes = [
            models.Index(fields=['next_run_at'], name='idx_scheduled_next_run', condition=models.Q(enabled=True)),
            models.Index(fields=['name']),
            models.Index(fields=['enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.schedule_type})"
    
    def clean(self):
        """Validate scheduled task configuration"""
        if self.schedule_type == 'cron':
            required_fields = ['cron_minute', 'cron_hour', 'cron_day_of_month', 'cron_month', 'cron_day_of_week']
            for field in required_fields:
                if not getattr(self, field):
                    raise ValidationError(f"{field} is required for cron schedule")
        elif self.schedule_type == 'interval':
            if not self.interval_seconds or self.interval_seconds <= 0:
                raise ValidationError("interval_seconds must be positive for interval schedule")
    
    def calculate_next_run(self) -> Optional[datetime]:
        """Calculate next run time based on schedule type"""
        if not self.enabled:
            return None
            
        if self.schedule_type == 'once' and self.last_run_at:
            return None
            
        current_time = self.last_run_at or timezone.now()
        
        if self.schedule_type == 'interval':
            return current_time + timedelta(seconds=self.interval_seconds)
        elif self.schedule_type == 'cron':
            # Simple cron implementation - can be enhanced with proper cron library
            return current_time + timedelta(days=1)  # Placeholder
        
        return None
    
    def create_task_execution(self) -> TaskQueue:
        """Create a task execution from this scheduled task"""
        task = TaskQueue.objects.create(
            task_name=self.task_name,
            task_module=self.task_module,
            task_args=self.task_args,
            task_kwargs=self.task_kwargs,
            queue_name=self.queue_name,
            priority=self.priority,
            tenant_id=self.tenant_id,
            created_by=f"scheduled_task_{self.id}"
        )
        
        # Update last run time and calculate next run
        self.last_run_at = timezone.now()
        self.next_run_at = self.calculate_next_run()
        self.save(update_fields=['last_run_at', 'next_run_at'])
        
        # Log the execution
        ScheduledTaskExecution.objects.create(
            scheduled_task=self,
            task=task,
            next_run_at=self.next_run_at
        )
        
        return task


class ScheduledTaskExecution(models.Model):
    """Scheduled task execution log"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheduled_task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, related_name='executions')
    task = models.ForeignKey(TaskQueue, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Execution information
    executed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=TaskQueue.STATUS_CHOICES)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    # Result information
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Next run calculation
    next_run_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'scheduled_task_executions'


class TaskWorker(models.Model):
    """Active workers registry"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('idle', 'Idle'),
        ('busy', 'Busy'),
        ('stopping', 'Stopping'),
        ('stopped', 'Stopped'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker_id = models.CharField(max_length=100, unique=True)
    hostname = models.CharField(max_length=255)
    pid = models.IntegerField()
    
    # Worker configuration
    queues = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    max_concurrent_tasks = models.IntegerField(default=4)
    current_task_count = models.IntegerField(default=0)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    last_heartbeat = models.DateTimeField(auto_now=True, db_index=True)
    
    # Performance metrics
    total_tasks_processed = models.IntegerField(default=0)
    total_processing_time_ms = models.BigIntegerField(default=0)
    
    # Lifecycle
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    worker_version = models.CharField(max_length=50, blank=True)
    python_version = models.CharField(max_length=50, blank=True)
    environment = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'task_workers'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['last_heartbeat']),
        ]
    
    def __str__(self):
        return f"{self.worker_id} ({self.status})"
    
    def update_heartbeat(self, **metrics):
        """Update worker heartbeat with optional metrics"""
        self.last_heartbeat = timezone.now()
        
        # Update only writable fields on the worker model
        worker_fields = [
            'current_task_count', 'total_tasks_processed', 
            'total_processing_time_ms', 'status'
        ]
        
        for key, value in metrics.items():
            if key in worker_fields and hasattr(self, key):
                setattr(self, key, value)
        
        self.save()
        
        # Create heartbeat log entry with only valid heartbeat fields
        try:
            heartbeat_fields = [
                'cpu_percent', 'memory_percent', 'memory_mb', 'active_tasks',
                'queue_lengths', 'tasks_per_minute', 'avg_task_duration_ms'
            ]
            
            heartbeat_data = {k: v for k, v in metrics.items() if k in heartbeat_fields}
            
            if heartbeat_data:  # Only create if we have heartbeat data
                WorkerHeartbeat.objects.create(
                    worker_id=self.worker_id,
                    **heartbeat_data
                )
        except Exception as e:
            # If table doesn't exist, just log the error silently
            logger.debug(f"Could not create heartbeat log: {e}")
    
    @property
    def is_healthy(self) -> bool:
        """Check if worker is healthy based on last heartbeat"""
        if not self.last_heartbeat:
            return False
        
        # Consider worker unhealthy if no heartbeat in last 5 minutes
        threshold = timezone.now() - timedelta(minutes=5)
        return self.last_heartbeat > threshold
    
    @property
    def avg_task_duration_ms(self) -> int:
        """Calculate average task duration"""
        if self.total_tasks_processed > 0:
            return int(self.total_processing_time_ms / self.total_tasks_processed)
        return 0


class WorkerHeartbeat(models.Model):
    """Worker heartbeat log for monitoring"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker_id = models.CharField(max_length=100)
    
    # System metrics
    timestamp = models.DateTimeField(auto_now_add=True)
    cpu_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    memory_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    memory_mb = models.IntegerField(null=True, blank=True)
    active_tasks = models.IntegerField(null=True, blank=True)
    
    # Task queue status
    queue_lengths = models.JSONField(default=dict)
    
    # Performance metrics
    tasks_per_minute = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    avg_task_duration_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'worker_heartbeats'


class TaskDependency(models.Model):
    """Task dependencies for workflow management"""
    
    DEPENDENCY_TYPE_CHOICES = [
        ('success', 'Success'),
        ('completion', 'Completion'),
        ('failure', 'Failure'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(TaskQueue, on_delete=models.CASCADE, related_name='dependencies')
    depends_on_task = models.ForeignKey(TaskQueue, on_delete=models.CASCADE, related_name='dependents')
    dependency_type = models.CharField(max_length=20, choices=DEPENDENCY_TYPE_CHOICES, default='success')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_dependencies'
        unique_together = ['task', 'depends_on_task']


class TaskWorkflow(models.Model):
    """Task chains/workflows"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Workflow configuration
    workflow_definition = models.JSONField()  # DAG definition
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True)
    version = models.IntegerField(default=1)
    tenant_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'task_workflows'


class TaskPerformanceMetrics(models.Model):
    """Task performance metrics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_name = models.CharField(max_length=255, db_index=True)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Execution metrics
    total_executions = models.IntegerField(default=0)
    successful_executions = models.IntegerField(default=0)
    failed_executions = models.IntegerField(default=0)
    
    # Timing metrics
    avg_duration_ms = models.IntegerField(null=True, blank=True)
    min_duration_ms = models.IntegerField(null=True, blank=True)
    max_duration_ms = models.IntegerField(null=True, blank=True)
    p95_duration_ms = models.IntegerField(null=True, blank=True)
    p99_duration_ms = models.IntegerField(null=True, blank=True)
    
    # Throughput metrics
    tasks_per_hour = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Resource usage
    avg_memory_mb = models.IntegerField(null=True, blank=True)
    max_memory_mb = models.IntegerField(null=True, blank=True)
    avg_cpu_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_performance_metrics'
        indexes = [
            models.Index(fields=['task_name']),
            models.Index(fields=['period_start', 'period_end']),
        ]