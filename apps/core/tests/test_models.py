"""
Tests for core app models
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.core.models import RateLimitAttempt


@pytest.mark.django_db
class TestRateLimitAttempt:
    """Test suite for RateLimitAttempt model"""
    
    def test_rate_limit_attempt_creation(self):
        """Test basic rate limit attempt creation"""
        attempt = RateLimitAttempt.objects.create(
            ip_address='192.168.1.100',
            username='testuser',
            user_agent='Mozilla/5.0 Test Browser',
            attempt_type='login',
            success=False,
            failure_reason='Invalid password'
        )
        
        assert attempt.id is not None
        assert attempt.ip_address == '192.168.1.100'
        assert attempt.username == 'testuser'
        assert attempt.attempt_type == 'login'
        assert attempt.success is False
        assert attempt.failure_reason == 'Invalid password'
        assert attempt.created_at is not None
        assert attempt.attempt_time is not None
    
    
    def test_rate_limit_attempt_str_representation(self, rate_limit_attempt):
        """Test string representation of rate limit attempt"""
        expected = f"{rate_limit_attempt.ip_address} - {rate_limit_attempt.username} - {rate_limit_attempt.attempt_time}"
        assert str(rate_limit_attempt) == expected
    
    
    def test_rate_limit_attempt_choices(self):
        """Test attempt type choices validation"""
        valid_types = ['login', 'password_reset', 'api_access', 'form_submission']
        
        for attempt_type in valid_types:
            attempt = RateLimitAttempt.objects.create(
                ip_address='192.168.1.101',
                username=f'user_{attempt_type}',
                attempt_type=attempt_type,
                success=True
            )
            assert attempt.attempt_type == attempt_type
    
    
    def test_rate_limit_attempt_defaults(self):
        """Test default values for fields"""
        attempt = RateLimitAttempt.objects.create(
            ip_address='192.168.1.102',
            username='defaultuser'
        )
        
        assert attempt.attempt_type == 'login'  # Default
        assert attempt.success is False  # Default
        assert attempt.user_agent is None  # Can be null
        assert attempt.failure_reason is None  # Can be null
    
    
    def test_ipv6_address_support(self):
        """Test IPv6 address support"""
        attempt = RateLimitAttempt.objects.create(
            ip_address='2001:db8::1',
            username='ipv6user',
            attempt_type='login',
            success=True
        )
        
        assert attempt.ip_address == '2001:db8::1'
    
    
    def test_rate_limit_attempt_ordering(self, multiple_rate_limit_attempts):
        """Test default ordering by attempt_time descending"""
        attempts = RateLimitAttempt.objects.all()
        
        # Should be ordered by attempt_time descending
        for i in range(len(attempts) - 1):
            assert attempts[i].attempt_time >= attempts[i + 1].attempt_time
    
    
    @patch('django.db.connection.cursor')
    def test_check_rate_limit_method(self, mock_cursor):
        """Test rate limit checking method"""
        # Mock the PostgreSQL function response
        mock_cursor_instance = Mock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        mock_cursor_instance.fetchone.return_value = ({
            'is_blocked': True,
            'attempts_count': 6,
            'time_window': '15 minutes',
            'last_attempt': '2024-01-01 12:00:00'
        },)
        
        result = RateLimitAttempt.check_rate_limit(
            ip_address='192.168.1.100',
            username='testuser',
            time_window_minutes=15,
            max_attempts=5
        )
        
        # Verify the function was called with correct parameters
        mock_cursor_instance.execute.assert_called_once()
        call_args = mock_cursor_instance.execute.call_args
        assert 'check_rate_limit' in call_args[0][0]
        
        # Verify parameters passed to SQL function
        params = call_args[0][1]
        assert params[0] == '192.168.1.100'  # IP address
        assert params[1] == 'testuser'        # Username
        assert params[2] == '15 minutes'      # Time window
        assert params[3] == 5                 # Max attempts
    
    
    def test_log_attempt_method(self):
        """Test logging attempt method"""
        attempt = RateLimitAttempt.log_attempt(
            ip_address='192.168.1.200',
            username='loguser',
            user_agent='Test Agent',
            attempt_type='login',
            success=True,
            failure_reason=None
        )
        
        assert attempt.ip_address == '192.168.1.200'
        assert attempt.username == 'loguser'
        assert attempt.user_agent == 'Test Agent'
        assert attempt.attempt_type == 'login'
        assert attempt.success is True
        assert attempt.failure_reason is None
    
    
    def test_log_attempt_method_with_defaults(self):
        """Test logging attempt with default values"""
        attempt = RateLimitAttempt.log_attempt(
            ip_address='192.168.1.201',
            username='defaultloguser'
        )
        
        assert attempt.ip_address == '192.168.1.201'
        assert attempt.username == 'defaultloguser'
        assert attempt.attempt_type == 'login'  # Default
        assert attempt.success is False  # Default
        assert attempt.user_agent is None
        assert attempt.failure_reason is None
    
    
    def test_cleanup_old_attempts(self, multiple_rate_limit_attempts):
        """Test cleanup of old attempts"""
        # Create some old attempts
        old_time = timezone.now() - timedelta(days=10)
        old_attempts = []
        for i in range(5):
            attempt = RateLimitAttempt.objects.create(
                ip_address='192.168.1.50',
                username=f'olduser{i}',
                attempt_type='login',
                success=False
            )
            # Manually update the attempt_time to be old
            attempt.attempt_time = old_time
            attempt.save()
            old_attempts.append(attempt)
        
        initial_count = RateLimitAttempt.objects.count()
        
        # Cleanup attempts older than 7 days
        deleted_count = RateLimitAttempt.cleanup_old_attempts(keep_days=7)
        
        assert deleted_count == 5  # Should delete the 5 old attempts
        assert RateLimitAttempt.objects.count() == initial_count - 5
        
        # Verify old attempts are gone
        for old_attempt in old_attempts:
            assert not RateLimitAttempt.objects.filter(id=old_attempt.id).exists()
    
    
    def test_cleanup_old_attempts_custom_days(self):
        """Test cleanup with custom retention period"""
        # Create attempts of different ages
        now = timezone.now()
        
        # Recent attempt (should be kept)
        recent = RateLimitAttempt.objects.create(
            ip_address='192.168.1.60',
            username='recentuser',
            attempt_type='login'
        )
        
        # Old attempt (should be deleted)
        old = RateLimitAttempt.objects.create(
            ip_address='192.168.1.61',
            username='olduser',
            attempt_type='login'
        )
        old.attempt_time = now - timedelta(days=4)
        old.save()
        
        # Cleanup with 3 days retention
        deleted_count = RateLimitAttempt.cleanup_old_attempts(keep_days=3)
        
        assert deleted_count == 1
        assert RateLimitAttempt.objects.filter(id=recent.id).exists()
        assert not RateLimitAttempt.objects.filter(id=old.id).exists()
    
    
    def test_database_indexes_exist(self):
        """Test that database indexes are properly created"""
        # This test verifies that the model's Meta configuration is correct
        meta = RateLimitAttempt._meta
        
        # Check that indexes are defined
        assert len(meta.indexes) == 3
        
        # Check specific index fields
        index_fields = [list(index.fields) for index in meta.indexes]
        assert ['ip_address', 'attempt_time'] in index_fields
        assert ['username', 'attempt_time'] in index_fields
        assert ['success', 'attempt_time'] in index_fields
    
    
    def test_meta_table_name(self):
        """Test custom database table name"""
        assert RateLimitAttempt._meta.db_table == 'auth_rate_limit_attempts'
    
    
    def test_successful_and_failed_attempts_tracking(self):
        """Test tracking both successful and failed attempts"""
        # Create successful attempt
        success = RateLimitAttempt.objects.create(
            ip_address='192.168.1.70',
            username='successuser',
            attempt_type='login',
            success=True
        )
        
        # Create failed attempt
        failure = RateLimitAttempt.objects.create(
            ip_address='192.168.1.70',
            username='successuser',
            attempt_type='login',
            success=False,
            failure_reason='Invalid credentials'
        )
        
        # Query by success status
        successful_attempts = RateLimitAttempt.objects.filter(
            ip_address='192.168.1.70',
            success=True
        )
        failed_attempts = RateLimitAttempt.objects.filter(
            ip_address='192.168.1.70',
            success=False
        )
        
        assert successful_attempts.count() == 1
        assert failed_attempts.count() == 1
        assert successful_attempts.first().failure_reason is None
        assert failed_attempts.first().failure_reason == 'Invalid credentials'
    
    
    def test_attempt_types_tracking(self):
        """Test tracking different attempt types"""
        attempt_types = ['login', 'password_reset', 'api_access', 'form_submission']
        
        for attempt_type in attempt_types:
            RateLimitAttempt.objects.create(
                ip_address='192.168.1.80',
                username='typeuser',
                attempt_type=attempt_type,
                success=True
            )
        
        # Verify each type is tracked
        for attempt_type in attempt_types:
            attempts = RateLimitAttempt.objects.filter(
                ip_address='192.168.1.80',
                attempt_type=attempt_type
            )
            assert attempts.count() == 1
    
    
    def test_large_user_agent_string(self):
        """Test handling of large user agent strings"""
        large_user_agent = "Mozilla/5.0 " + "X" * 2000  # Very long user agent
        
        attempt = RateLimitAttempt.objects.create(
            ip_address='192.168.1.90',
            username='largeua',
            user_agent=large_user_agent,
            attempt_type='login'
        )
        
        assert attempt.user_agent == large_user_agent
        assert len(attempt.user_agent) > 2000
    
    
    def test_concurrent_attempts_tracking(self):
        """Test tracking concurrent attempts from same IP"""
        ip_address = '192.168.1.100'
        
        # Simulate concurrent attempts
        attempts = []
        for i in range(10):
            attempt = RateLimitAttempt.objects.create(
                ip_address=ip_address,
                username=f'user{i}',
                attempt_type='login',
                success=i % 2 == 0  # Alternate success/failure
            )
            attempts.append(attempt)
        
        # Verify all attempts are tracked
        ip_attempts = RateLimitAttempt.objects.filter(ip_address=ip_address)
        assert ip_attempts.count() == 10
        
        # Verify success/failure distribution
        successful = ip_attempts.filter(success=True).count()
        failed = ip_attempts.filter(success=False).count()
        assert successful == 5
        assert failed == 5