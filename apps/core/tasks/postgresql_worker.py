"""
PostgreSQL Task Queue Worker
Phase 2B: Celery/Redis to PostgreSQL Migration

Multi-threaded worker implementation to replace Celery workers
"""

import os
import sys
import time
import json
import uuid
import signal
import logging
import threading
import traceback
import importlib
import multiprocessing
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import psutil
from django.db import transaction, connections
from django.utils import timezone
from django.conf import settings

from apps.core.models.task_queue import (
    TaskQueue, TaskWorker, WorkerHeartbeat, 
    TaskExecutionHistory, ScheduledTask, serialize_result
)

logger = logging.getLogger(__name__)


class PostgreSQLTaskWorker:
    """
    Multi-threaded PostgreSQL task worker to replace Celery
    """
    
    def __init__(self, 
                 worker_id: str = None,
                 queues: List[str] = None,
                 max_concurrent_tasks: int = 4,
                 heartbeat_interval: int = 30,
                 max_task_execution_time: int = 3600,
                 enable_scheduler: bool = True):
        """
        Initialize PostgreSQL task worker
        
        Args:
            worker_id: Unique worker identifier
            queues: List of queue names to process
            max_concurrent_tasks: Maximum concurrent tasks
            heartbeat_interval: Heartbeat interval in seconds
            max_task_execution_time: Maximum task execution time in seconds
            enable_scheduler: Enable scheduler thread for scheduled tasks
        """
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.queues = queues or ['default']
        self.max_concurrent_tasks = max_concurrent_tasks
        self.heartbeat_interval = heartbeat_interval
        self.max_task_execution_time = max_task_execution_time
        self.enable_scheduler = enable_scheduler
        
        # Worker state
        self.running = False
        self.stopping = False
        self.executor = None
        self.heartbeat_thread = None
        self.scheduler_thread = None
        
        # Performance tracking
        self.total_tasks_processed = 0
        self.total_processing_time_ms = 0
        self.current_tasks = {}
        
        # Task registry
        self.task_registry = {}
        self._load_task_registry()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _load_task_registry(self):
        """Load all available tasks from Django apps"""
        print("🔄 Loading task registry...")
        logger.info("Loading task registry...")
        
        # List of modules to scan for tasks
        modules_to_scan = []
        
        # Try to import each module individually
        try:
            from background_tasks import tasks as bg_tasks
            modules_to_scan.append(('background_tasks.tasks', bg_tasks))
            print("✅ Loaded background_tasks.tasks module")
            logger.info("✅ Loaded background_tasks.tasks module")
        except ImportError as e:
            print(f"⚠️  Could not import background_tasks.tasks: {e}")
            logger.warning(f"Could not import background_tasks.tasks: {e}")
        
        try:
            from apps.core import tasks as core_tasks
            modules_to_scan.append(('apps.core.tasks', core_tasks))
            print("✅ Loaded apps.core.tasks module")
            logger.info("✅ Loaded apps.core.tasks module")
        except ImportError as e:
            print(f"⚠️  Could not import apps.core.tasks: {e}")
            logger.warning(f"Could not import apps.core.tasks: {e}")
        
        # Scan for task functions in each loaded module
        for module_name, module in modules_to_scan:
            print(f"🔍 Scanning {module_name} for task functions...")
            logger.info(f"Scanning {module_name} for task functions...")
            module_tasks = 0
            
            for attr_name in dir(module):
                if attr_name.startswith('_'):
                    continue
                    
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '__name__'):
                    # Skip imported functions and classes
                    if hasattr(attr, '__module__') and attr.__module__ == module.__name__:
                        full_name = f"{module_name}.{attr_name}"
                        self.task_registry[attr_name] = {
                            'function': attr,
                            'module': module_name,
                            'full_name': full_name
                        }
                        module_tasks += 1
                        print(f"  📋 Registered task: {attr_name}")
                        logger.debug(f"  - Registered task: {attr_name}")
            
            print(f"✅ Found {module_tasks} tasks in {module_name}")
            logger.info(f"✅ Found {module_tasks} tasks in {module_name}")
        
        print(f"🎯 Total tasks loaded: {len(self.task_registry)}")
        logger.info(f"🎯 Total tasks loaded: {len(self.task_registry)}")
        
        if len(self.task_registry) > 0:
            print("📋 Available tasks:")
            logger.info("Available tasks:")
            for task_name in sorted(self.task_registry.keys()):
                task_info = self.task_registry[task_name]
                print(f"  - {task_name} ({task_info['module']})")
                logger.info(f"  - {task_name} ({task_info['module']})")
        else:
            print("⚠️  No tasks found in registry!")
            logger.warning("⚠️  No tasks found in registry!")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
    
    def start(self):
        """Start the worker"""
        logger.info(f"Starting PostgreSQL task worker {self.worker_id}")
        
        try:
            # Register worker in database
            self._register_worker()
            
            # Start thread pool executor
            self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_tasks)
            self.running = True
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            
            # Start scheduler thread (for scheduled tasks) if enabled
            if self.enable_scheduler:
                self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
                self.scheduler_thread.start()
                logger.info("Scheduler thread started for scheduled tasks")
            
            # Main worker loop
            self._worker_loop()
            
        except Exception as e:
            logger.error(f"Error starting worker: {e}")
            logger.error(traceback.format_exc())
            self.stop()
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping worker {self.worker_id}")
        self.stopping = True
        self.running = False
        
        if self.executor:
            logger.info("Waiting for running tasks to complete...")
            self.executor.shutdown(wait=True)
    
    def _register_worker(self):
        """Register worker in database"""
        try:
            worker, created = TaskWorker.objects.get_or_create(
                worker_id=self.worker_id,
                defaults={
                    'hostname': os.uname().nodename,
                    'pid': os.getpid(),
                    'queues': self.queues,
                    'max_concurrent_tasks': self.max_concurrent_tasks,
                    'status': 'active',
                    'worker_version': '1.0.0',
                    'python_version': sys.version.split()[0],
                    'environment': {
                        'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
                        'debug': settings.DEBUG,
                        'database': settings.DATABASES['default']['ENGINE']
                    }
                }
            )
            
            if not created:
                # Update existing worker
                worker.hostname = os.uname().nodename
                worker.pid = os.getpid()
                worker.queues = self.queues
                worker.max_concurrent_tasks = self.max_concurrent_tasks
                worker.status = 'active'
                worker.started_at = timezone.now()
                worker.stopped_at = None
                worker.save()
            
            logger.info(f"Registered worker {self.worker_id} in database")
            
        except Exception as e:
            logger.error(f"Error registering worker: {e}")
            raise
    
    def _worker_loop(self):
        """Main worker loop to process tasks"""
        logger.info(f"Worker {self.worker_id} started processing tasks")
        
        while self.running and not self.stopping:
            try:
                # Get next available task
                task = TaskQueue.objects.get_next_task(
                    queue_names=self.queues,
                    worker_id=self.worker_id
                )
                
                if task:
                    # Submit task to thread pool
                    future = self.executor.submit(self._execute_task, task)
                    self.current_tasks[task.id] = {
                        'task': task,
                        'future': future,
                        'started_at': timezone.now()
                    }
                    
                    logger.debug(f"Submitted task {task.task_name} ({task.id}) for execution")
                else:
                    # No tasks available, sleep briefly
                    time.sleep(1)
                
                # Clean up completed tasks
                self._cleanup_completed_tasks()
                
                # Check for stuck tasks
                self._check_stuck_tasks()
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(5)  # Back off on error
    
    def _execute_task(self, task: TaskQueue) -> Any:
        """Execute a single task"""
        start_time = time.time()
        execution_history = None
        
        try:
            logger.info(f"Executing task {task.task_name} ({task.id})")
            
            # Create execution history record
            execution_history = TaskExecutionHistory.objects.create(
                task=task,
                status='processing',
                started_at=timezone.now(),
                worker_id=self.worker_id,
                worker_hostname=os.uname().nodename,
                worker_pid=os.getpid()
            )
            
            # Get task function from registry
            if task.task_name not in self.task_registry:
                raise ValueError(f"Task {task.task_name} not found in registry")
            
            task_info = self.task_registry[task.task_name]
            task_function = task_info['function']
            
            # Prepare task arguments
            args = task.task_args or []
            kwargs = task.task_kwargs or {}
            
            # Execute the task
            result = task_function(*args, **kwargs)
            
            # Calculate execution time
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)
            
            # Mark task as completed
            task.mark_completed(result)
            
            # Update execution history
            execution_history.status = 'completed'
            execution_history.completed_at = timezone.now()
            execution_history.duration_ms = duration_ms
            execution_history.result = serialize_result(result)
            execution_history.save()
            
            # Update worker statistics
            self.total_tasks_processed += 1
            self.total_processing_time_ms += duration_ms
            
            logger.info(f"Completed task {task.task_name} ({task.id}) in {duration_ms}ms")
            
            return result
            
        except Exception as e:
            error_message = str(e)
            error_traceback = traceback.format_exc()
            
            logger.error(f"Error executing task {task.task_name} ({task.id}): {error_message}")
            logger.error(error_traceback)
            
            # Mark task as failed
            task.mark_failed(error_message, error_traceback)
            
            # Update execution history
            if execution_history:
                execution_history.status = 'failed'
                execution_history.completed_at = timezone.now()
                execution_history.error_message = error_message
                execution_history.traceback = error_traceback
                execution_history.save()
            
            # Decide whether to retry
            if task.retry_count < task.max_retries:
                logger.info(f"Scheduling retry for task {task.task_name} ({task.id})")
                task.retry()
            
            raise
        
        finally:
            # Remove task from current tasks
            if task.id in self.current_tasks:
                del self.current_tasks[task.id]
    
    def _cleanup_completed_tasks(self):
        """Clean up completed tasks from current_tasks dict"""
        completed_task_ids = []
        
        for task_id, task_info in self.current_tasks.items():
            future = task_info['future']
            if future.done():
                completed_task_ids.append(task_id)
                
                # Log any exceptions
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
        
        # Remove completed tasks
        for task_id in completed_task_ids:
            del self.current_tasks[task_id]
    
    def _check_stuck_tasks(self):
        """Check for stuck tasks and handle them"""
        current_time = timezone.now()
        stuck_threshold = timedelta(seconds=self.max_task_execution_time)
        
        stuck_task_ids = []
        for task_id, task_info in self.current_tasks.items():
            started_at = task_info['started_at']
            if current_time - started_at > stuck_threshold:
                stuck_task_ids.append(task_id)
                logger.warning(f"Task {task_id} appears to be stuck (running for {current_time - started_at})")
        
        # Cancel stuck tasks
        for task_id in stuck_task_ids:
            task_info = self.current_tasks[task_id]
            future = task_info['future']
            task = task_info['task']
            
            # Try to cancel the future
            if future.cancel():
                logger.info(f"Cancelled stuck task {task_id}")
                task.mark_failed("Task cancelled due to timeout", "")
            else:
                logger.warning(f"Could not cancel stuck task {task_id}")
            
            del self.current_tasks[task_id]
    
    def _heartbeat_loop(self):
        """Heartbeat loop to update worker status"""
        while self.running and not self.stopping:
            try:
                self._send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(self.heartbeat_interval)
    
    def _send_heartbeat(self):
        """Send worker heartbeat with metrics"""
        try:
            # Get system metrics
            process = psutil.Process()
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss // 1024 // 1024
            memory_percent = process.memory_percent()
            
            # Get queue lengths
            queue_lengths = {}
            for queue_name in self.queues:
                count = TaskQueue.objects.filter(
                    status='pending',
                    queue_name=queue_name
                ).count()
                queue_lengths[queue_name] = count
            
            # Calculate performance metrics
            tasks_per_minute = 0
            avg_task_duration_ms = 0
            
            if self.total_tasks_processed > 0:
                # Calculate tasks per minute based on total processing time
                total_time_seconds = self.total_processing_time_ms / 1000
                if total_time_seconds > 0:
                    tasks_per_minute = (self.total_tasks_processed * 60) / total_time_seconds
                avg_task_duration_ms = self.total_processing_time_ms // self.total_tasks_processed
            
            # Update worker record
            worker = TaskWorker.objects.get(worker_id=self.worker_id)
            worker.update_heartbeat(
                current_task_count=len(self.current_tasks),
                total_tasks_processed=self.total_tasks_processed,
                total_processing_time_ms=self.total_processing_time_ms,
                status='busy' if self.current_tasks else 'idle'
            )
            
            # Create heartbeat log entry with additional metrics
            WorkerHeartbeat.objects.create(
                worker_id=self.worker_id,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                active_tasks=len(self.current_tasks),
                queue_lengths=queue_lengths,
                tasks_per_minute=tasks_per_minute,
                avg_task_duration_ms=avg_task_duration_ms
            )
            
            logger.debug(f"Sent heartbeat for worker {self.worker_id}")
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    
    def _scheduler_loop(self):
        """Scheduler loop to process scheduled tasks"""
        while self.running and not self.stopping:
            try:
                self._process_scheduled_tasks()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _process_scheduled_tasks(self):
        """Process due scheduled tasks"""
        try:
            due_tasks = ScheduledTask.objects.due_tasks()
            
            for scheduled_task in due_tasks:
                try:
                    logger.info(f"Creating execution for scheduled task: {scheduled_task.name}")
                    task = scheduled_task.create_task_execution()
                    logger.info(f"Created task {task.id} from scheduled task {scheduled_task.name}")
                    
                except Exception as e:
                    logger.error(f"Error creating execution for scheduled task {scheduled_task.name}: {e}")
                    logger.error(traceback.format_exc())
            
        except Exception as e:
            logger.error(f"Error processing scheduled tasks: {e}")
            logger.error(traceback.format_exc())
    
    def _cleanup(self):
        """Clean up worker resources"""
        try:
            # Update worker status to stopped
            worker = TaskWorker.objects.get(worker_id=self.worker_id)
            worker.status = 'stopped'
            worker.stopped_at = timezone.now()
            worker.save()
            
            logger.info(f"Worker {self.worker_id} stopped")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class TaskSubmitter:
    """
    Utility class to submit tasks to PostgreSQL queue
    """
    
    @staticmethod
    def submit_task(task_name: str,
                   task_module: str = 'background_tasks.tasks',
                   args: List[Any] = None,
                   kwargs: Dict[str, Any] = None,
                   queue_name: str = 'default',
                   priority: int = 5,
                   delay_seconds: int = 0,
                   expires_in_seconds: int = None,
                   max_retries: int = 3,
                   tenant_id: int = None) -> TaskQueue:
        """
        Submit a task to the PostgreSQL queue
        
        Args:
            task_name: Name of the task function
            task_module: Module containing the task
            args: Task arguments
            kwargs: Task keyword arguments
            queue_name: Queue name
            priority: Task priority (1-10, 1=highest)
            delay_seconds: Delay execution by seconds
            expires_in_seconds: Task expiration time in seconds
            max_retries: Maximum retry attempts
            tenant_id: Tenant ID for multi-tenant apps
            
        Returns:
            TaskQueue instance
        """
        scheduled_at = timezone.now()
        if delay_seconds > 0:
            scheduled_at += timedelta(seconds=delay_seconds)
        
        expires_at = None
        if expires_in_seconds:
            expires_at = timezone.now() + timedelta(seconds=expires_in_seconds)
        
        task = TaskQueue.objects.create(
            task_name=task_name,
            task_module=task_module,
            task_args=args or [],
            task_kwargs=kwargs or {},
            queue_name=queue_name,
            priority=priority,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
            max_retries=max_retries,
            tenant_id=tenant_id
        )
        
        logger.info(f"Submitted task {task_name} ({task.id}) to queue {queue_name}")
        return task
    
    @staticmethod
    def submit_scheduled_task(name: str,
                            task_name: str,
                            task_module: str,
                            cron_expr: str = None,
                            interval_seconds: int = None,
                            args: List[Any] = None,
                            kwargs: Dict[str, Any] = None,
                            queue_name: str = 'default',
                            priority: int = 5,
                            description: str = '',
                            enabled: bool = True) -> ScheduledTask:
        """
        Submit a scheduled task
        
        Args:
            name: Unique task name
            task_name: Task function name
            task_module: Module containing the task
            cron_expr: Cron expression (e.g., "0 */8 * * *")
            interval_seconds: Interval in seconds
            args: Task arguments
            kwargs: Task keyword arguments
            queue_name: Queue name
            priority: Task priority
            description: Task description
            enabled: Whether task is enabled
            
        Returns:
            ScheduledTask instance
        """
        if cron_expr:
            scheduled_task = ScheduledTask.objects.create_from_cron(
                name=name,
                task_name=task_name,
                task_module=task_module,
                cron_expr=cron_expr,
                task_args=args or [],
                task_kwargs=kwargs or {},
                queue_name=queue_name,
                priority=priority,
                description=description,
                enabled=enabled
            )
        elif interval_seconds:
            scheduled_task = ScheduledTask.objects.create(
                name=name,
                task_name=task_name,
                task_module=task_module,
                schedule_type='interval',
                interval_seconds=interval_seconds,
                task_args=args or [],
                task_kwargs=kwargs or {},
                queue_name=queue_name,
                priority=priority,
                description=description,
                enabled=enabled
            )
        else:
            raise ValueError("Either cron_expr or interval_seconds must be provided")
        
        logger.info(f"Created scheduled task {name}")
        return scheduled_task


def run_worker():
    """Main function to run the PostgreSQL task worker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PostgreSQL Task Worker')
    parser.add_argument('--worker-id', help='Worker ID')
    parser.add_argument('--queues', nargs='+', default=['default'], help='Queue names to process')
    parser.add_argument('--max-concurrent', type=int, default=4, help='Max concurrent tasks')
    parser.add_argument('--heartbeat-interval', type=int, default=30, help='Heartbeat interval in seconds')
    parser.add_argument('--log-level', default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start worker
    worker = PostgreSQLTaskWorker(
        worker_id=args.worker_id,
        queues=args.queues,
        max_concurrent_tasks=args.max_concurrent,
        heartbeat_interval=args.heartbeat_interval
    )
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        worker.stop()


if __name__ == '__main__':
    run_worker()