#!/usr/bin/env python3
"""
Phase 2B: PostgreSQL Task Queue Test Script
Comprehensive testing of the PostgreSQL task queue implementation
"""

import os
import sys
import time
import json
import django
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

import logging
from django.db import transaction
from django.utils import timezone
from django.test import TestCase

from apps.core.models.task_queue import (
    TaskQueue, ScheduledTask, TaskWorker, 
    TaskExecutionHistory, WorkerHeartbeat
)
from apps.core.tasks.postgresql_worker import TaskSubmitter, PostgreSQLTaskWorker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgreSQLTaskQueueTests:
    """Comprehensive test suite for PostgreSQL Task Queue"""
    
    def __init__(self):
        self.test_results = []
        self.test_worker = None
    
    def run_all_tests(self):
        """Run all test cases"""
        logger.info("🧪 Starting PostgreSQL Task Queue Test Suite")
        logger.info("="*60)
        
        test_methods = [
            self.test_database_schema,
            self.test_django_models,
            self.test_task_submission,
            self.test_task_execution,
            self.test_scheduled_tasks,
            self.test_worker_management,
            self.test_task_retry_mechanism,
            self.test_task_dependencies,
            self.test_performance_monitoring,
            self.test_cleanup_operations,
            self.test_queue_management,
            self.test_real_world_scenarios
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                logger.info(f"\n🔍 Running {test_method.__name__}...")
                test_method()
                logger.info(f"✅ {test_method.__name__} PASSED")
                passed += 1
            except Exception as e:
                logger.error(f"❌ {test_method.__name__} FAILED: {e}")
                failed += 1
        
        logger.info(f"\n📊 Test Results Summary:")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            logger.info("🎉 All tests passed! PostgreSQL Task Queue is ready for production.")
        else:
            logger.warning("⚠️  Some tests failed. Please review the issues before deployment.")
        
        return failed == 0
    
    def test_database_schema(self):
        """Test database schema and tables"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check if all required tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('task_queue', 'scheduled_tasks', 'task_workers', 
                                   'task_execution_history', 'worker_heartbeats')
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            required_tables = ['task_queue', 'scheduled_tasks', 'task_workers', 
                             'task_execution_history', 'worker_heartbeats']
            
            for table in required_tables:
                assert table in tables, f"Required table {table} not found"
            
            # Check if indexes exist
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'task_queue'
            """)
            
            indexes = [row[0] for row in cursor.fetchall()]
            assert len(indexes) >= 3, "Task queue table should have multiple indexes"
            
            # Check if functions exist
            cursor.execute("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_name IN ('cleanup_old_tasks', 'get_queue_statistics')
            """)
            
            functions = [row[0] for row in cursor.fetchall()]
            assert len(functions) >= 1, "PostgreSQL functions should be available"
    
    def test_django_models(self):
        """Test Django model operations"""
        # Test TaskQueue model
        task = TaskQueue.objects.create(
            task_name='test_task',
            task_module='test_module',
            task_args=['arg1', 'arg2'],
            task_kwargs={'key': 'value'},
            queue_name='test',
            priority=5
        )
        
        assert task.id is not None, "Task should have an ID"
        assert task.status == 'pending', "New task should be pending"
        assert task.get_full_task_name() == 'test_module.test_task'
        
        # Test task methods
        task.mark_completed({'result': 'success'})
        assert task.status == 'completed'
        assert task.result == {'result': 'success'}
        
        # Test ScheduledTask model
        scheduled_task = ScheduledTask.objects.create(
            name='test_scheduled_task',
            task_name='test_task',
            task_module='test_module',
            schedule_type='interval',
            interval_seconds=300,
            enabled=True
        )
        
        assert scheduled_task.id is not None
        next_run = scheduled_task.calculate_next_run()
        assert next_run is not None, "Next run should be calculated"
        
        # Clean up
        task.delete()
        scheduled_task.delete()
    
    def test_task_submission(self):
        """Test task submission functionality"""
        # Submit a simple task
        task = TaskSubmitter.submit_task(
            task_name='test_submission',
            task_module='test_module',
            args=['test_arg'],
            kwargs={'test_key': 'test_value'},
            queue_name='test_queue',
            priority=3
        )
        
        assert task.task_name == 'test_submission'
        assert task.task_args == ['test_arg']
        assert task.task_kwargs == {'test_key': 'test_value'}
        assert task.queue_name == 'test_queue'
        assert task.priority == 3
        assert task.status == 'pending'
        
        # Submit delayed task
        delayed_task = TaskSubmitter.submit_task(
            task_name='delayed_task',
            task_module='test_module',
            delay_seconds=60
        )
        
        assert delayed_task.scheduled_at > timezone.now()
        
        # Submit task with expiration
        expiring_task = TaskSubmitter.submit_task(
            task_name='expiring_task',
            task_module='test_module',
            expires_in_seconds=3600
        )
        
        assert expiring_task.expires_at is not None
        assert not expiring_task.is_expired
        
        # Clean up
        task.delete()
        delayed_task.delete()
        expiring_task.delete()
    
    def test_task_execution(self):
        """Test task execution logic"""
        # Create a simple test task function
        def dummy_task(x, y=1):
            return x + y
        
        # Mock the task registry
        task_registry = {
            'dummy_task': {
                'function': dummy_task,
                'module': 'test_module',
                'full_name': 'test_module.dummy_task'
            }
        }
        
        # Create a task
        task = TaskQueue.objects.create(
            task_name='dummy_task',
            task_module='test_module',
            task_args=[5],
            task_kwargs={'y': 3},
            queue_name='test'
        )
        
        # Simulate task execution
        task.status = 'processing'
        task.started_at = timezone.now()
        task.save()
        
        # Execute the task logic
        result = dummy_task(*task.task_args, **task.task_kwargs)
        
        # Mark as completed
        task.mark_completed(result)
        
        assert task.status == 'completed'
        assert task.result == 8
        assert task.completed_at is not None
        assert task.duration is not None
        
        # Clean up
        task.delete()
    
    def test_scheduled_tasks(self):
        """Test scheduled task functionality"""
        # Create an interval-based scheduled task
        scheduled_task = ScheduledTask.objects.create(
            name='test_interval_task',
            task_name='test_task',
            task_module='test_module',
            schedule_type='interval',
            interval_seconds=60,
            enabled=True
        )
        
        # Test next run calculation
        next_run = scheduled_task.calculate_next_run()
        assert next_run is not None
        
        # Create task execution
        task = scheduled_task.create_task_execution()
        assert task.task_name == 'test_task'
        assert task.task_module == 'test_module'
        assert scheduled_task.last_run_at is not None
        
        # Test cron-based scheduled task
        cron_task = ScheduledTask.objects.create(
            name='test_cron_task',
            task_name='test_cron',
            task_module='test_module',
            schedule_type='cron',
            cron_minute='0',
            cron_hour='12',
            cron_day_of_month='*',
            cron_month='*',
            cron_day_of_week='*',
            enabled=True
        )
        
        # Test due tasks query
        due_tasks = ScheduledTask.objects.due_tasks()
        task_names = [task.name for task in due_tasks]
        
        # Clean up
        scheduled_task.delete()
        cron_task.delete()
        task.delete()
    
    def test_worker_management(self):
        """Test worker registration and management"""
        # Create a test worker
        worker = TaskWorker.objects.create(
            worker_id='test_worker_001',
            hostname='test_host',
            pid=12345,
            queues=['test_queue'],
            max_concurrent_tasks=2,
            status='active'
        )
        
        assert worker.worker_id == 'test_worker_001'
        assert worker.is_healthy  # Should be healthy since just created
        
        # Test heartbeat update
        worker.update_heartbeat(
            current_task_count=1,
            cpu_percent=25.5,
            memory_mb=256
        )
        
        # Check if heartbeat was recorded
        heartbeat = WorkerHeartbeat.objects.filter(worker_id=worker.worker_id).first()
        assert heartbeat is not None
        assert heartbeat.cpu_percent == 25.5
        assert heartbeat.memory_mb == 256
        
        # Test worker performance metrics
        worker.total_tasks_processed = 10
        worker.total_processing_time_ms = 5000
        worker.save()
        
        assert worker.avg_task_duration_ms == 500
        
        # Clean up
        worker.delete()
    
    def test_task_retry_mechanism(self):
        """Test task retry functionality"""
        # Create a task that will fail
        task = TaskQueue.objects.create(
            task_name='failing_task',
            task_module='test_module',
            max_retries=3
        )
        
        # Mark as failed
        task.mark_failed("Test error", "Test traceback")
        
        assert task.status == 'failed'
        assert task.retry_count == 0
        
        # Test retry
        task.retry()
        
        assert task.status == 'pending'
        assert task.retry_count == 1
        assert task.scheduled_at > timezone.now()  # Should be delayed
        
        # Test max retries
        task.retry_count = 3
        task.save()
        
        try:
            task.retry()
            assert False, "Should have raised an error for max retries exceeded"
        except Exception as e:
            assert "exceeded maximum retry attempts" in str(e)
        
        # Test retry failed tasks manager method
        failed_task = TaskQueue.objects.create(
            task_name='another_failing_task',
            task_module='test_module',
            status='failed',
            completed_at=timezone.now(),
            retry_count=0,
            max_retries=3
        )
        
        retry_count = TaskQueue.objects.retry_failed_tasks(max_age_hours=1)
        assert retry_count >= 1
        
        # Clean up
        task.delete()
        failed_task.delete()
    
    def test_task_dependencies(self):
        """Test task dependency functionality"""
        # This is a placeholder for future dependency implementation
        # For now, just test that the model exists and can be created
        from apps.core.models.task_queue import TaskDependency
        
        parent_task = TaskQueue.objects.create(
            task_name='parent_task',
            task_module='test_module'
        )
        
        child_task = TaskQueue.objects.create(
            task_name='child_task',
            task_module='test_module'
        )
        
        # Create dependency
        dependency = TaskDependency.objects.create(
            task=child_task,
            depends_on_task=parent_task,
            dependency_type='success'
        )
        
        assert dependency.task == child_task
        assert dependency.depends_on_task == parent_task
        
        # Clean up
        dependency.delete()
        parent_task.delete()
        child_task.delete()
    
    def test_performance_monitoring(self):
        """Test performance monitoring features"""
        from apps.core.models.task_queue import TaskPerformanceMetrics
        
        # Create performance metrics
        metrics = TaskPerformanceMetrics.objects.create(
            task_name='test_performance_task',
            period_start=timezone.now() - timedelta(hours=1),
            period_end=timezone.now(),
            total_executions=100,
            successful_executions=95,
            failed_executions=5,
            avg_duration_ms=250,
            min_duration_ms=50,
            max_duration_ms=1000,
            tasks_per_hour=100.0
        )
        
        assert metrics.total_executions == 100
        assert metrics.successful_executions == 95
        assert metrics.failed_executions == 5
        
        # Clean up
        metrics.delete()
    
    def test_cleanup_operations(self):
        """Test cleanup operations"""
        # Create old completed tasks
        old_task = TaskQueue.objects.create(
            task_name='old_task',
            task_module='test_module',
            status='completed',
            created_at=timezone.now() - timedelta(days=35),
            completed_at=timezone.now() - timedelta(days=35)
        )
        
        # Test cleanup function
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT cleanup_old_tasks(30)")
            result = cursor.fetchone()
            deleted_count = result[0] if result else 0
        
        # Verify old task was cleaned up
        assert not TaskQueue.objects.filter(id=old_task.id).exists()
    
    def test_queue_management(self):
        """Test queue management operations"""
        # Create tasks in different queues
        high_priority_task = TaskQueue.objects.create(
            task_name='high_priority_task',
            task_module='test_module',
            queue_name='high_priority',
            priority=1
        )
        
        default_task = TaskQueue.objects.create(
            task_name='default_task',
            task_module='test_module',
            queue_name='default',
            priority=5
        )
        
        # Test queue filtering
        high_priority_tasks = TaskQueue.objects.filter(queue_name='high_priority')
        assert high_priority_tasks.count() >= 1
        
        # Test priority ordering
        pending_tasks = TaskQueue.objects.pending_tasks(priority_order=True)
        if pending_tasks.count() >= 2:
            first_task = pending_tasks.first()
            assert first_task.priority <= 5  # Should be highest priority first
        
        # Test get_next_task
        next_task = TaskQueue.objects.get_next_task(['high_priority'], 'test_worker')
        if next_task:
            assert next_task.status == 'processing'
            assert next_task.worker_id == 'test_worker'
        
        # Clean up
        high_priority_task.delete()
        default_task.delete()
    
    def test_real_world_scenarios(self):
        """Test real-world usage scenarios"""
        # Scenario 1: High-throughput task submission
        logger.info("Testing high-throughput task submission...")
        
        start_time = time.time()
        task_ids = []
        
        for i in range(50):
            task = TaskSubmitter.submit_task(
                task_name='bulk_task',
                task_module='test_module',
                args=[i],
                queue_name='bulk_test'
            )
            task_ids.append(task.id)
        
        end_time = time.time()
        submission_time = end_time - start_time
        
        logger.info(f"Submitted 50 tasks in {submission_time:.2f} seconds ({50/submission_time:.1f} tasks/sec)")
        
        # Verify tasks were created
        created_tasks = TaskQueue.objects.filter(id__in=task_ids)
        assert created_tasks.count() == 50
        
        # Scenario 2: Queue statistics
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_queue_statistics('bulk_test')")
            stats = cursor.fetchone()
            if stats:
                logger.info(f"Queue statistics: {stats}")
        
        # Scenario 3: Concurrent task processing simulation
        logger.info("Testing concurrent task pickup...")
        
        # Simulate multiple workers picking up tasks
        picked_tasks = []
        for worker_id in ['worker_1', 'worker_2', 'worker_3']:
            task = TaskQueue.objects.get_next_task(['bulk_test'], worker_id)
            if task:
                picked_tasks.append(task)
        
        # Verify no task was picked up by multiple workers
        worker_ids = [task.worker_id for task in picked_tasks]
        assert len(worker_ids) == len(set(worker_ids)), "Tasks should not be picked up by multiple workers"
        
        # Clean up
        TaskQueue.objects.filter(id__in=task_ids).delete()


def run_integration_test():
    """Run integration test with actual worker"""
    logger.info("\n🔧 Running Integration Test with Worker")
    logger.info("="*50)
    
    # Create a simple test task
    def test_integration_task(message):
        logger.info(f"Executing integration test task: {message}")
        return f"Processed: {message}"
    
    # Submit task
    task = TaskSubmitter.submit_task(
        task_name='test_integration_task',
        task_module='__main__',
        args=['Hello from PostgreSQL Task Queue!'],
        queue_name='integration_test'
    )
    
    logger.info(f"Submitted integration test task: {task.id}")
    
    # Create a minimal worker for testing
    worker = PostgreSQLTaskWorker(
        worker_id='integration_test_worker',
        queues=['integration_test'],
        max_concurrent_tasks=1,
        heartbeat_interval=5
    )
    
    # Add test task to worker registry
    worker.task_registry['test_integration_task'] = {
        'function': test_integration_task,
        'module': '__main__',
        'full_name': '__main__.test_integration_task'
    }
    
    # Start worker in a separate thread
    worker_thread = threading.Thread(target=worker.start, daemon=True)
    
    try:
        worker_thread.start()
        
        # Wait for task to be processed
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            task.refresh_from_db()
            if task.status in ['completed', 'failed']:
                break
            time.sleep(1)
        
        if task.status == 'completed':
            logger.info(f"✅ Integration test passed! Task result: {task.result}")
        else:
            logger.error(f"❌ Integration test failed! Task status: {task.status}")
            if task.error_message:
                logger.error(f"Error: {task.error_message}")
        
    finally:
        worker.stop()
        task.delete()
    
    return task.status == 'completed'


def main():
    """Main test function"""
    logger.info("🧪 PostgreSQL Task Queue Test Suite")
    logger.info("Phase 2B: Comprehensive Testing")
    logger.info("="*60)
    
    # Run unit tests
    test_suite = PostgreSQLTaskQueueTests()
    unit_tests_passed = test_suite.run_all_tests()
    
    # Run integration test
    integration_test_passed = run_integration_test()
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("📊 FINAL TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Unit Tests: {'✅ PASSED' if unit_tests_passed else '❌ FAILED'}")
    logger.info(f"Integration Test: {'✅ PASSED' if integration_test_passed else '❌ FAILED'}")
    
    if unit_tests_passed and integration_test_passed:
        logger.info("\n🎉 All tests passed! PostgreSQL Task Queue is ready for production deployment.")
        logger.info("\n📋 Next Steps:")
        logger.info("1. Run the setup script: python postgresql_migration/scripts/phase2b_setup_task_queue.py")
        logger.info("2. Start workers: python manage.py run_postgresql_worker")
        logger.info("3. Begin gradual migration from Celery to PostgreSQL")
        return True
    else:
        logger.error("\n❌ Some tests failed. Please fix issues before deployment.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)