"""
PostgreSQL Task Queue adapter for MQTT
Replaces Celery with PostgreSQL for MQTT task processing
"""

import json
import logging
from apps.core.models.task_queue import TaskQueue

logger = logging.getLogger(__name__)

class PostgreSQLTaskAdapter:
    """Adapter to replace Celery functionality for MQTT"""
    
    @staticmethod
    def delay_task(task_name, *args, **kwargs):
        """
        Submit a task to PostgreSQL queue (replaces celery.delay())
        Returns a task object with task_id and state properties
        """
        task = TaskQueue.objects.create(
            task_name=task_name,
            task_module='background_tasks.tasks',
            task_args=list(args),
            task_kwargs=kwargs,
            queue_name='mqtt',
            priority=3  # Medium priority for MQTT tasks
        )
        
        logger.info(f"Submitted MQTT task {task_name} to PostgreSQL queue: {task.id}")
        
        # Return a Celery-like result object
        return MockAsyncResult(task.id, task.status)
    
    @staticmethod
    def get_task_status(task_id):
        """Get status of a task by ID (replaces AsyncResult)"""
        try:
            task = TaskQueue.objects.get(id=task_id)
            return {
                'task_id': str(task.id),
                'status': task.status.upper(),  # Celery uses uppercase
                'state': task.status.upper(),
                'result': task.result
            }
        except TaskQueue.DoesNotExist:
            return {
                'task_id': task_id,
                'status': 'PENDING',
                'state': 'PENDING',
                'result': None
            }

class MockAsyncResult:
    """Mock AsyncResult class to maintain compatibility with MQTT code"""
    
    def __init__(self, task_id, status):
        self.task_id = str(task_id)
        self.state = status.upper()
        self.status = status.upper()
    
    def ready(self):
        """Check if task is complete"""
        return self.state in ['SUCCESS', 'FAILURE', 'COMPLETED', 'FAILED']
    
    def successful(self):
        """Check if task completed successfully"""
        return self.state in ['SUCCESS', 'COMPLETED']
    
    def failed(self):
        """Check if task failed"""
        return self.state in ['FAILURE', 'FAILED']

# Convenience functions for backward compatibility
def delay_task(task_name, *args, **kwargs):
    """Submit task to PostgreSQL queue"""
    return PostgreSQLTaskAdapter.delay_task(task_name, *args, **kwargs)

def get_task_status(task_id):
    """Get task status by ID"""
    return PostgreSQLTaskAdapter.get_task_status(task_id)

# Mock process_graphql_mutation_async for direct import compatibility
class MockTask:
    def delay(self, *args, **kwargs):
        return delay_task('process_graphql_mutation_async', *args, **kwargs)

# Create a mock task object that can be imported
process_graphql_mutation_async = MockTask()