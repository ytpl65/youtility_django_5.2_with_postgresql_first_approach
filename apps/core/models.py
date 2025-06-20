from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import ipaddress

User = get_user_model()

class RateLimitAttempt(models.Model):
    """
    PostgreSQL-based rate limiting for authentication attempts
    Replaces Redis-based rate limiting with persistent, auditable storage
    """
    
    ATTEMPT_TYPES = [
        ('login', 'Login Attempt'),
        ('password_reset', 'Password Reset'),
        ('api_access', 'API Access'),
        ('form_submission', 'Form Submission'),
    ]
    
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the request"
    )
    username = models.CharField(
        max_length=150, 
        blank=True, 
        null=True,
        help_text="Username attempted (if available)"
    )
    user_agent = models.TextField(
        blank=True, 
        null=True,
        help_text="Browser user agent string"
    )
    attempt_time = models.DateTimeField(
        default=timezone.now,
        help_text="When the attempt was made"
    )
    attempt_type = models.CharField(
        max_length=50,
        choices=ATTEMPT_TYPES,
        default='login',
        help_text="Type of attempt being rate limited"
    )
    success = models.BooleanField(
        default=False,
        help_text="Whether the attempt was successful"
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Reason for failure (invalid password, blocked, etc.)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created"
    )
    
    class Meta:
        db_table = 'auth_rate_limit_attempts'
        indexes = [
            models.Index(fields=['ip_address', 'attempt_time']),
            models.Index(fields=['username', 'attempt_time']), 
            models.Index(fields=['success', 'attempt_time']),
        ]
        ordering = ['-attempt_time']
    
    def __str__(self):
        return f"{self.ip_address} - {self.username} - {self.attempt_time}"
    
    @classmethod
    def check_rate_limit(cls, ip_address, username=None, time_window_minutes=15, max_attempts=5):
        """
        Check if IP address or username is rate limited
        
        Args:
            ip_address (str): IP address to check
            username (str, optional): Username to check  
            time_window_minutes (int): Time window in minutes (default: 15)
            max_attempts (int): Maximum failed attempts allowed (default: 5)
            
        Returns:
            dict: Rate limit status and details
        """
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT check_rate_limit(%s, %s, %s::INTERVAL, %s)
            """, [
                ip_address,
                username,
                f'{time_window_minutes} minutes',
                max_attempts
            ])
            
            result = cursor.fetchone()[0]
            return result
    
    @classmethod  
    def log_attempt(cls, ip_address, username=None, user_agent=None, 
                   attempt_type='login', success=False, failure_reason=None):
        """
        Log a rate limit attempt
        
        Args:
            ip_address (str): IP address making the attempt
            username (str, optional): Username being attempted
            user_agent (str, optional): Browser user agent
            attempt_type (str): Type of attempt (default: 'login')
            success (bool): Whether attempt was successful
            failure_reason (str, optional): Reason for failure
            
        Returns:
            RateLimitAttempt: Created instance
        """
        return cls.objects.create(
            ip_address=ip_address,
            username=username,
            user_agent=user_agent,
            attempt_type=attempt_type,
            success=success,
            failure_reason=failure_reason
        )
    
    @classmethod
    def cleanup_old_attempts(cls, keep_days=7):
        """
        Clean up old rate limit attempts
        
        Args:
            keep_days (int): Number of days to keep (default: 7)
            
        Returns:
            int: Number of deleted records
        """
        cutoff_date = timezone.now() - timedelta(days=keep_days)
        deleted_count, _ = cls.objects.filter(
            attempt_time__lt=cutoff_date
        ).delete()
        return deleted_count
        
