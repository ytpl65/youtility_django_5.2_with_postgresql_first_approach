"""
Tests for core app health check system
"""
import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.test import RequestFactory, Client
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from apps.core.health_checks import (
    HealthCheckManager, health_manager,
    check_database, check_postgresql_functions, check_cache,
    check_task_queue, check_application_status,
    health_check, readiness_check, liveness_check, detailed_health_check
)


@pytest.mark.django_db
class TestHealthCheckManager:
    """Test suite for HealthCheckManager"""
    
    def test_health_check_manager_initialization(self):
        """Test health check manager initialization"""
        manager = HealthCheckManager()
        
        assert manager.checks == {}
        assert isinstance(manager.start_time, float)
        assert manager.start_time <= time.time()
    
    
    def test_register_check(self):
        """Test registering health checks"""
        manager = HealthCheckManager()
        
        def dummy_check():
            return {'status': 'healthy'}
        
        manager.register_check('test_check', dummy_check, critical=True)
        
        assert 'test_check' in manager.checks
        assert manager.checks['test_check']['func'] == dummy_check
        assert manager.checks['test_check']['critical'] is True
        assert manager.checks['test_check']['last_run'] is None
        assert manager.checks['test_check']['last_result'] is None
    
    
    def test_register_check_defaults(self):
        """Test registering check with default critical value"""
        manager = HealthCheckManager()
        
        def dummy_check():
            return {'status': 'healthy'}
        
        manager.register_check('test_check', dummy_check)
        
        assert manager.checks['test_check']['critical'] is True  # Default
    
    
    def test_run_check_success(self):
        """Test running a successful health check"""
        manager = HealthCheckManager()
        
        def healthy_check():
            return {'status': 'healthy', 'message': 'All good'}
        
        manager.register_check('healthy_test', healthy_check)
        result = manager.run_check('healthy_test')
        
        assert result['status'] == 'healthy'
        assert result['message'] == 'All good'
        assert 'duration_ms' in result
        assert 'timestamp' in result
        assert isinstance(result['duration_ms'], float)
        
        # Check that last_run and last_result are updated
        check_info = manager.checks['healthy_test']
        assert check_info['last_run'] is not None
        assert check_info['last_result'] == result
    
    
    def test_run_check_failure(self):
        """Test running a failing health check"""
        manager = HealthCheckManager()
        
        def failing_check():
            raise Exception("Database connection failed")
        
        manager.register_check('failing_test', failing_check)
        result = manager.run_check('failing_test')
        
        assert result['status'] == 'error'
        assert 'Database connection failed' in result['message']
        assert 'duration_ms' in result
        assert 'timestamp' in result
    
    
    def test_run_check_unknown(self):
        """Test running an unknown health check"""
        manager = HealthCheckManager()
        result = manager.run_check('unknown_check')
        
        assert result['status'] == 'error'
        assert 'Unknown check' in result['message']
    
    
    def test_run_all_checks_healthy(self):
        """Test running all checks when all are healthy"""
        manager = HealthCheckManager()
        
        def check1():
            return {'status': 'healthy'}
        
        def check2():
            return {'status': 'healthy'}
        
        manager.register_check('check1', check1, critical=True)
        manager.register_check('check2', check2, critical=False)
        
        result = manager.run_all_checks()
        
        assert result['status'] == 'healthy'
        assert 'timestamp' in result
        assert 'uptime_seconds' in result
        assert 'checks' in result
        assert len(result['checks']) == 2
        assert result['checks']['check1']['status'] == 'healthy'
        assert result['checks']['check2']['status'] == 'healthy'
    
    
    def test_run_all_checks_unhealthy(self):
        """Test running all checks when critical check fails"""
        manager = HealthCheckManager()
        
        def healthy_check():
            return {'status': 'healthy'}
        
        def critical_failing_check():
            return {'status': 'error', 'message': 'Critical failure'}
        
        manager.register_check('healthy', healthy_check, critical=False)
        manager.register_check('critical_fail', critical_failing_check, critical=True)
        
        result = manager.run_all_checks()
        
        assert result['status'] == 'unhealthy'
        assert result['checks']['healthy']['status'] == 'healthy'
        assert result['checks']['critical_fail']['status'] == 'error'
    
    
    def test_run_all_checks_degraded(self):
        """Test running all checks when non-critical check fails"""
        manager = HealthCheckManager()
        
        def healthy_critical_check():
            return {'status': 'healthy'}
        
        def failing_non_critical_check():
            return {'status': 'warning', 'message': 'Non-critical issue'}
        
        manager.register_check('critical_healthy', healthy_critical_check, critical=True)
        manager.register_check('non_critical_fail', failing_non_critical_check, critical=False)
        
        result = manager.run_all_checks()
        
        assert result['status'] == 'degraded'


@pytest.mark.django_db
class TestDatabaseHealthCheck:
    """Test suite for database health check"""
    
    @patch('django.db.connection.cursor')
    def test_check_database_success(self, mock_cursor):
        """Test successful database health check"""
        mock_cursor_instance = Mock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        
        # Mock database responses
        mock_cursor_instance.fetchone.side_effect = [
            (1,),  # SELECT 1
            ('PostgreSQL 14.8 on x86_64-pc-linux-gnu',),  # version()
            (150,)  # session count
        ]
        
        result = check_database()
        
        assert result['status'] == 'healthy'
        assert 'database_version' in result
        assert 'session_count' in result
        assert result['session_count'] == 150
        assert 'query_time_ms' in result
        assert result['connection_status'] == 'connected'
    
    
    @patch('django.db.connection.cursor')
    def test_check_database_failure(self, mock_cursor):
        """Test database health check failure"""
        mock_cursor.side_effect = Exception("Connection refused")
        
        result = check_database()
        
        assert result['status'] == 'error'
        assert 'Connection refused' in result['message']
        assert result['connection_status'] == 'failed'


@pytest.mark.django_db 
class TestPostgreSQLFunctionsCheck:
    """Test suite for PostgreSQL functions health check"""
    
    @patch('django.db.connection.cursor')
    def test_check_postgresql_functions_all_available(self, mock_cursor):
        """Test when all PostgreSQL functions are available"""
        mock_cursor_instance = Mock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        
        # Mock all functions as existing
        mock_cursor_instance.fetchone.side_effect = [
            (True,),  # check_rate_limit
            (True,),  # cleanup_expired_sessions
            (True,),  # cleanup_select2_cache
            (True,)   # refresh_select2_materialized_views
        ]
        
        result = check_postgresql_functions()
        
        assert result['status'] == 'healthy'
        assert 'functions' in result
        assert all(status == 'available' for status in result['functions'].values())
        assert 'All PostgreSQL functions available' in result['message']
    
    
    @patch('django.db.connection.cursor')
    def test_check_postgresql_functions_missing(self, mock_cursor):
        """Test when some PostgreSQL functions are missing"""
        mock_cursor_instance = Mock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        
        # Mock some functions as missing
        mock_cursor_instance.fetchone.side_effect = [
            (True,),   # check_rate_limit
            (False,),  # cleanup_expired_sessions (missing)
            (True,),   # cleanup_select2_cache
            (False,)   # refresh_select2_materialized_views (missing)
        ]
        
        result = check_postgresql_functions()
        
        assert result['status'] == 'error'
        assert result['functions']['check_rate_limit'] == 'available'
        assert result['functions']['cleanup_expired_sessions'] == 'missing'
        assert result['functions']['cleanup_select2_cache'] == 'available'
        assert result['functions']['refresh_select2_materialized_views'] == 'missing'
        assert 'Some functions missing' in result['message']
    
    
    @patch('django.db.connection.cursor')
    def test_check_postgresql_functions_error(self, mock_cursor):
        """Test PostgreSQL functions check error"""
        mock_cursor.side_effect = Exception("Database error")
        
        result = check_postgresql_functions()
        
        assert result['status'] == 'error'
        assert 'Database error' in result['message']


class TestCacheHealthCheck:
    """Test suite for cache health check"""
    
    @patch('apps.core.health_checks.cache')
    def test_check_cache_success(self, mock_cache):
        """Test successful cache health check"""
        # Configure the mock cache to simulate successful read/write
        def mock_get(key):
            # Return the exact same value that was set
            return mock_cache._test_value
        
        def mock_set(key, value, timeout):
            # Store the value for retrieval
            mock_cache._test_value = value
            return True
        
        mock_cache.set.side_effect = mock_set
        mock_cache.get.side_effect = mock_get
        mock_cache.delete.return_value = True
        mock_cache.__class__.__name__ = 'DatabaseCache'
        
        result = check_cache()
        
        assert result['status'] == 'healthy'
        assert result['backend'] == 'DatabaseCache'
        assert 'Cache read/write successful' in result['message']
    
    
    @patch('apps.core.health_checks.cache')
    def test_check_cache_read_write_failure(self, mock_cache):
        """Test cache read/write failure"""
        # Mock cache returning different value than set
        test_value = {'test': True, 'timestamp': timezone.now().isoformat()}
        mock_cache.set.return_value = True
        mock_cache.get.return_value = {'different': 'value'}
        mock_cache.__class__.__name__ = 'DatabaseCache'
        
        result = check_cache()
        
        assert result['status'] == 'error'
        assert 'Cache read/write failed' in result['message']
    
    
    @patch('apps.core.health_checks.cache')
    def test_check_cache_exception(self, mock_cache):
        """Test cache check exception"""
        mock_cache.set.side_effect = Exception("Cache connection failed")
        
        result = check_cache()
        
        assert result['status'] == 'error'
        assert 'Cache connection failed' in result['message']


@pytest.mark.django_db
class TestTaskQueueHealthCheck:
    """Test suite for task queue health check"""
    
    @patch('apps.core.models.RateLimitAttempt.objects')
    @patch('django.db.connection.cursor')
    def test_check_task_queue_success(self, mock_cursor, mock_rate_limit):
        """Test successful task queue health check"""
        mock_cursor_instance = Mock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        mock_cursor_instance.fetchone.return_value = (5,)  # 5 task tables found
        
        # Mock RateLimitAttempt query
        mock_rate_limit.filter.return_value.count.return_value = 10
        
        result = check_task_queue()
        
        assert result['status'] == 'healthy'
        assert result['task_tables_available'] is True
        assert 'recent_rate_limit_attempts' in result
        assert 'PostgreSQL task queue system operational' in result['message']
    
    
    @patch('django.db.connection.cursor')
    def test_check_task_queue_failure(self, mock_cursor):
        """Test task queue health check failure"""
        mock_cursor.side_effect = Exception("Task queue error")
        
        result = check_task_queue()
        
        assert result['status'] == 'error'
        assert 'Task queue error' in result['message']


class TestApplicationStatusCheck:
    """Test suite for application status health check"""
    
    @patch('django.conf.settings')
    def test_check_application_status_healthy(self, mock_settings):
        """Test healthy application status"""
        mock_settings.DEBUG = False
        mock_settings.SECRET_KEY = 'secret'
        mock_settings.ALLOWED_HOSTS = ['localhost']
        mock_settings.DATABASES = {'default': {}}
        mock_settings.INSTALLED_APPS = [
            'django.contrib.auth',
            'django.contrib.sessions', 
            'apps.core'
        ]
        
        result = check_application_status()
        
        assert result['status'] == 'healthy'
        assert result['debug_enabled'] is False
        assert result['missing_settings'] == []
        assert result['missing_apps'] == []
        assert result['issues'] == []
    
    
    @patch('apps.core.health_checks.settings')
    def test_check_application_status_warnings(self, mock_settings):
        """Test application status with warnings"""
        mock_settings.DEBUG = True  # Should be False in production
        mock_settings.SECRET_KEY = 'secret'
        mock_settings.ALLOWED_HOSTS = ['localhost']
        mock_settings.DATABASES = {'default': {}}
        mock_settings.INSTALLED_APPS = ['django.contrib.sessions']  # Missing some critical apps
        
        result = check_application_status()
        
        assert result['status'] == 'warning'
        assert result['debug_enabled'] is True
        assert 'django.contrib.auth' in result['missing_apps']
        assert 'apps.core' in result['missing_apps']
        assert len(result['issues']) > 0
        assert any('DEBUG is enabled' in issue for issue in result['issues'])


@pytest.mark.django_db
class TestHealthCheckViews:
    """Test suite for health check view endpoints"""
    
    def test_health_check_view_healthy(self, client):
        """Test health check view with healthy status"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.return_value = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'uptime_seconds': 3600,
                'checks': {}
            }
            
            response = client.get('/health/')
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['status'] == 'healthy'
    
    
    def test_health_check_view_unhealthy(self, client):
        """Test health check view with unhealthy status"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.return_value = {
                'status': 'unhealthy',
                'timestamp': timezone.now().isoformat(),
                'uptime_seconds': 3600,
                'checks': {}
            }
            
            response = client.get('/health/')
            
            assert response.status_code == 503
            data = json.loads(response.content)
            assert data['status'] == 'unhealthy'
    
    
    def test_health_check_view_degraded(self, client):
        """Test health check view with degraded status"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.return_value = {
                'status': 'degraded',
                'timestamp': timezone.now().isoformat(),
                'uptime_seconds': 3600,
                'checks': {}
            }
            
            response = client.get('/health/')
            
            assert response.status_code == 200  # Still operational
            data = json.loads(response.content)
            assert data['status'] == 'degraded'
    
    
    def test_readiness_check_view_ready(self, client):
        """Test readiness check view when ready"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.return_value = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'checks': {}
            }
            
            response = client.get('/ready/')
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['status'] == 'ready'
    
    
    def test_readiness_check_view_not_ready(self, client):
        """Test readiness check view when not ready"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.return_value = {
                'status': 'unhealthy',
                'timestamp': timezone.now().isoformat(),
                'checks': {}
            }
            
            response = client.get('/ready/')
            
            assert response.status_code == 503
            data = json.loads(response.content)
            assert data['status'] == 'not_ready'
    
    
    def test_liveness_check_view(self, client):
        """Test liveness check view"""
        response = client.get('/alive/')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'alive'
        assert 'uptime_seconds' in data
        assert 'timestamp' in data
    
    
    def test_detailed_health_check_view(self, client):
        """Test detailed health check view"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.return_value = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'uptime_seconds': 3600,
                'checks': {}
            }
            
            response = client.get('/health/detailed/')
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['status'] == 'healthy'
            assert 'system_info' in data
    
    
    def test_health_check_view_exception(self, client):
        """Test health check view with exception"""
        with patch.object(health_manager, 'run_all_checks') as mock_run:
            mock_run.side_effect = Exception("Health check system error")
            
            response = client.get('/health/')
            
            assert response.status_code == 503
            data = json.loads(response.content)
            assert data['status'] == 'error'
            assert 'Health check system error' in data['message']


class TestHealthCheckIntegration:
    """Integration tests for health check system"""
    
    def test_global_health_manager_registration(self):
        """Test that global health manager has checks registered"""
        # The global health_manager should have checks registered from module import
        assert 'database' in health_manager.checks
        assert 'postgresql_functions' in health_manager.checks
        assert 'cache' in health_manager.checks
        assert 'task_queue' in health_manager.checks
        assert 'application' in health_manager.checks
        
        # Check critical flags
        assert health_manager.checks['database']['critical'] is True
        assert health_manager.checks['postgresql_functions']['critical'] is True
        assert health_manager.checks['cache']['critical'] is False
        assert health_manager.checks['task_queue']['critical'] is True
        assert health_manager.checks['application']['critical'] is False
    
    
    def test_health_check_performance(self):
        """Test health check performance"""
        start_time = time.time()
        
        # Mock all checks to be fast
        with patch.object(health_manager, 'run_check') as mock_run:
            mock_run.return_value = {
                'status': 'healthy',
                'duration_ms': 10.0,
                'timestamp': timezone.now().isoformat()
            }
            
            result = health_manager.run_all_checks()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Health checks should complete quickly
        assert duration < 1.0  # Less than 1 second
        assert result['status'] == 'healthy'