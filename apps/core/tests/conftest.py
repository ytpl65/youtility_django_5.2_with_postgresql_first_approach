"""
Test configuration and fixtures for core app
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from apps.core.models import RateLimitAttempt
from apps.onboarding.models import Bt

User = get_user_model()


@pytest.fixture
def rf():
    """Request factory"""
    return RequestFactory()


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """Create an admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def test_client_bt():
    """Create a test client business unit"""
    return Bt.objects.create(
        bucode='TESTCORE',
        buname='Core Test Client',
        enable=True
    )


@pytest.fixture
def rate_limit_attempt():
    """Create a test rate limit attempt"""
    return RateLimitAttempt.objects.create(
        ip_address='192.168.1.100',
        username='testuser',
        user_agent='Mozilla/5.0 Test Browser',
        attempt_type='login',
        success=False,
        failure_reason='Invalid password'
    )


@pytest.fixture
def multiple_rate_limit_attempts():
    """Create multiple rate limit attempts for testing"""
    attempts = []
    base_time = timezone.now() - timedelta(minutes=30)
    
    for i in range(10):
        attempt = RateLimitAttempt.objects.create(
            ip_address='192.168.1.100',
            username='testuser',
            user_agent='Mozilla/5.0 Test Browser',
            attempt_type='login',
            success=i % 3 == 0,  # Every 3rd attempt is successful
            failure_reason='Invalid password' if i % 3 != 0 else None,
            attempt_time=base_time + timedelta(minutes=i * 2)
        )
        attempts.append(attempt)
    
    return attempts


@pytest.fixture
def mock_database_cursor():
    """Mock database cursor for testing PostgreSQL functions"""
    with patch('django.db.connection.cursor') as mock_cursor:
        mock_cursor_instance = Mock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        yield mock_cursor_instance


@pytest.fixture
def mock_cache():
    """Mock Django cache for testing"""
    with patch('django.core.cache.cache') as mock_cache:
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache.delete.return_value = True
        yield mock_cache


@pytest.fixture
def mock_health_manager():
    """Mock health manager for testing"""
    from apps.core.health_checks import HealthCheckManager
    
    manager = HealthCheckManager()
    manager.start_time = time.time() - 3600  # 1 hour uptime
    return manager


@pytest.fixture
def authenticated_request(rf, user, test_client_bt):
    """Create an authenticated request with session data"""
    request = rf.get("/")
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    
    # Set session data
    request.session['client_id'] = test_client_bt.id
    request.session['bu_id'] = test_client_bt.id
    request.session['user_id'] = user.id
    request.user = user
    
    return request


@pytest.fixture
def mock_postgresql_function_exists():
    """Mock PostgreSQL function existence check"""
    def _mock_function_exists(function_names=None):
        if function_names is None:
            function_names = [
                'check_rate_limit',
                'cleanup_expired_sessions',
                'cleanup_select2_cache',
                'refresh_select2_materialized_views'
            ]
        
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_cursor_instance = Mock()
            mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
            
            # Mock function existence results
            mock_cursor_instance.fetchone.side_effect = [
                (True,) for _ in function_names
            ]
            
            yield mock_cursor_instance
    
    return _mock_function_exists


@pytest.fixture
def mock_settings():
    """Mock Django settings for testing"""
    mock_settings_obj = Mock()
    mock_settings_obj.DEBUG = False
    mock_settings_obj.SECRET_KEY = 'test-secret-key'
    mock_settings_obj.ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    mock_settings_obj.DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql'}}
    mock_settings_obj.INSTALLED_APPS = [
        'django.contrib.auth',
        'django.contrib.sessions',
        'apps.core'
    ]
    
    return mock_settings_obj