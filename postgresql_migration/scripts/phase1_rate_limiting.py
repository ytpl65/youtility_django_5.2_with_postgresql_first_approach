#!/usr/bin/env python3
"""
Phase 1A: Rate Limiting Migration from Redis to PostgreSQL
Migrate login rate limiting from Redis to PostgreSQL for better persistence and auditability
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append('/home/satyam/Documents/YOUTILITY-MIGRATION-DJANGO5-POSTGRESQL/YOUTILITY3')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')
django.setup()

from django.db import connection, transaction
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()

class RateLimitingMigrator:
    def __init__(self):
        self.table_name = 'auth_rate_limit_attempts'
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🔒 {title}")
        print(f"{'='*60}")
    
    def analyze_current_rate_limiting(self):
        """Analyze current Redis-based rate limiting"""
        self.print_header("ANALYZING CURRENT RATE LIMITING")
        
        # Look for rate limiting middleware
        from django.conf import settings
        middleware = getattr(settings, 'MIDDLEWARE', [])
        
        rate_limit_middleware = [m for m in middleware if 'rate' in m.lower() or 'limit' in m.lower()]
        print(f"📋 Rate limiting middleware found:")
        for middleware_name in rate_limit_middleware:
            print(f"   • {middleware_name}")
        
        # Check current Redis usage for rate limiting
        try:
            # Test current rate limiting mechanism
            test_key = f"rate_limit_test_{datetime.now().timestamp()}"
            cache.set(test_key, 1, 60)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            
            if cached_value:
                print(f"✅ Redis cache is working for rate limiting")
                print(f"   Current mechanism: Redis-based with cache backend")
            else:
                print(f"❌ Redis cache test failed")
                
        except Exception as e:
            print(f"⚠️  Redis rate limiting test error: {str(e)}")
    
    def create_postgresql_rate_limit_table(self):
        """Create PostgreSQL table for rate limiting"""
        self.print_header("CREATING POSTGRESQL RATE LIMIT TABLE")
        
        with connection.cursor() as cursor:
            # Create the rate limiting table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    ip_address INET NOT NULL,
                    username VARCHAR(150),
                    user_agent TEXT,
                    attempt_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    attempt_type VARCHAR(50) DEFAULT 'login',
                    success BOOLEAN DEFAULT FALSE,
                    failure_reason VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            print(f"✅ Created table: {self.table_name}")
            
            # Create performance indexes
            indexes = [
                {
                    'name': f'{self.table_name}_ip_time_idx',
                    'sql': f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_ip_time_idx 
                        ON {self.table_name}(ip_address, attempt_time);
                    """
                },
                {
                    'name': f'{self.table_name}_username_time_idx', 
                    'sql': f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_username_time_idx
                        ON {self.table_name}(username, attempt_time);
                    """
                },
                {
                    'name': f'{self.table_name}_success_time_idx',
                    'sql': f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_success_time_idx
                        ON {self.table_name}(success, attempt_time);
                    """
                },
                {
                    'name': f'{self.table_name}_recent_attempts_idx',
                    'sql': f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_recent_attempts_idx
                        ON {self.table_name}(attempt_time) 
                        WHERE attempt_time > NOW() - INTERVAL '1 hour';
                    """
                }
            ]
            
            print(f"🗂️ Creating performance indexes:")
            for index in indexes:
                try:
                    cursor.execute(index['sql'])
                    print(f"   ✅ {index['name']}")
                except Exception as e:
                    print(f"   ⚠️  {index['name']}: {str(e)}")
    
    def create_rate_limiting_functions(self):
        """Create PostgreSQL functions for rate limiting logic"""
        self.print_header("CREATING RATE LIMITING FUNCTIONS")
        
        with connection.cursor() as cursor:
            # Function to check rate limits
            cursor.execute(f"""
                CREATE OR REPLACE FUNCTION check_rate_limit(
                    p_ip_address INET,
                    p_username VARCHAR(150) DEFAULT NULL,
                    p_time_window INTERVAL DEFAULT '15 minutes',
                    p_max_attempts INTEGER DEFAULT 5
                ) RETURNS JSON AS $$
                DECLARE
                    ip_attempts INTEGER;
                    user_attempts INTEGER;
                    total_attempts INTEGER;
                    result JSON;
                    is_blocked BOOLEAN DEFAULT FALSE;
                    block_reason TEXT DEFAULT '';
                BEGIN
                    -- Count failed attempts by IP in time window
                    SELECT COUNT(*) INTO ip_attempts
                    FROM {self.table_name}
                    WHERE ip_address = p_ip_address
                      AND attempt_time > NOW() - p_time_window
                      AND success = FALSE;
                    
                    -- Count failed attempts by username if provided
                    IF p_username IS NOT NULL THEN
                        SELECT COUNT(*) INTO user_attempts
                        FROM {self.table_name}
                        WHERE username = p_username
                          AND attempt_time > NOW() - p_time_window
                          AND success = FALSE;
                    ELSE
                        user_attempts := 0;
                    END IF;
                    
                    total_attempts := GREATEST(ip_attempts, user_attempts);
                    
                    -- Determine if blocked
                    IF ip_attempts >= p_max_attempts THEN
                        is_blocked := TRUE;
                        block_reason := 'IP address blocked due to too many failed attempts';
                    ELSIF user_attempts >= p_max_attempts THEN
                        is_blocked := TRUE;
                        block_reason := 'Username blocked due to too many failed attempts';
                    END IF;
                    
                    -- Build result JSON
                    result := json_build_object(
                        'is_blocked', is_blocked,
                        'ip_attempts', ip_attempts,
                        'user_attempts', user_attempts,
                        'total_attempts', total_attempts,
                        'max_attempts', p_max_attempts,
                        'block_reason', block_reason,
                        'time_window_minutes', EXTRACT(EPOCH FROM p_time_window) / 60
                    );
                    
                    RETURN result;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            print("✅ Created check_rate_limit() function")
            
            # Function to log rate limit attempts
            cursor.execute(f"""
                CREATE OR REPLACE FUNCTION log_rate_limit_attempt(
                    p_ip_address INET,
                    p_username VARCHAR(150) DEFAULT NULL,
                    p_user_agent TEXT DEFAULT NULL,
                    p_attempt_type VARCHAR(50) DEFAULT 'login',
                    p_success BOOLEAN DEFAULT FALSE,
                    p_failure_reason VARCHAR(255) DEFAULT NULL
                ) RETURNS INTEGER AS $$
                DECLARE
                    new_id INTEGER;
                BEGIN
                    INSERT INTO {self.table_name} (
                        ip_address, username, user_agent, 
                        attempt_type, success, failure_reason
                    ) VALUES (
                        p_ip_address, p_username, p_user_agent,
                        p_attempt_type, p_success, p_failure_reason
                    ) RETURNING id INTO new_id;
                    
                    RETURN new_id;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            print("✅ Created log_rate_limit_attempt() function")
            
            # Function to clean up old attempts
            cursor.execute(f"""
                CREATE OR REPLACE FUNCTION cleanup_old_rate_limit_attempts(
                    p_keep_duration INTERVAL DEFAULT '7 days'
                ) RETURNS INTEGER AS $$
                DECLARE
                    deleted_count INTEGER;
                BEGIN
                    DELETE FROM {self.table_name}
                    WHERE attempt_time < NOW() - p_keep_duration;
                    
                    GET DIAGNOSTICS deleted_count = ROW_COUNT;
                    
                    RETURN deleted_count;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            print("✅ Created cleanup_old_rate_limit_attempts() function")
    
    def create_django_model(self):
        """Create Django model for rate limiting"""
        self.print_header("CREATING DJANGO MODEL")
        
        model_code = f'''
# Add this to apps/core/models.py or create apps/auth/models.py

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
        db_table = '{self.table_name}'
        indexes = [
            models.Index(fields=['ip_address', 'attempt_time']),
            models.Index(fields=['username', 'attempt_time']), 
            models.Index(fields=['success', 'attempt_time']),
        ]
        ordering = ['-attempt_time']
    
    def __str__(self):
        return f"{{self.ip_address}} - {{self.username}} - {{self.attempt_time}}"
    
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
                f'{{time_window_minutes}} minutes',
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
        '''
        
        print("📝 Django Model Code:")
        print("Copy this code to your models.py file:")
        print("-" * 60)
        print(model_code)
        
        return model_code
    
    def create_rate_limiting_middleware(self):
        """Create Django middleware for PostgreSQL rate limiting"""
        self.print_header("CREATING RATE LIMITING MIDDLEWARE")
        
        middleware_code = '''
# Create apps/core/middleware/rate_limiting.py

from django.http import HttpResponseTooManyRequests
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

class PostgreSQLRateLimitMiddleware:
    """
    PostgreSQL-based rate limiting middleware
    Replaces Redis-based rate limiting with database storage
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuration
        self.rate_limit_paths = getattr(settings, 'RATE_LIMIT_PATHS', [
            '/login/',
            '/accounts/login/', 
            '/api/',
            '/reset-password/',
        ])
        
        self.time_window_minutes = getattr(settings, 'RATE_LIMIT_WINDOW_MINUTES', 15)
        self.max_attempts = getattr(settings, 'RATE_LIMIT_MAX_ATTEMPTS', 5)
        self.enable_rate_limiting = getattr(settings, 'ENABLE_RATE_LIMITING', True)
    
    def __call__(self, request):
        # Check if rate limiting is enabled and path should be rate limited
        if not self.enable_rate_limiting:
            return self.get_response(request)
            
        if not any(request.path.startswith(path) for path in self.rate_limit_paths):
            return self.get_response(request)
        
        # Get client information
        ip_address = self.get_client_ip(request)
        username = getattr(request.user, 'username', None) if hasattr(request, 'user') and request.user.is_authenticated else None
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check rate limit before processing request
        try:
            from apps.core.models import RateLimitAttempt  # Adjust import path
            
            rate_limit_result = RateLimitAttempt.check_rate_limit(
                ip_address=ip_address,
                username=username,
                time_window_minutes=self.time_window_minutes,
                max_attempts=self.max_attempts
            )
            
            if rate_limit_result.get('is_blocked', False):
                # Log the blocked attempt
                RateLimitAttempt.log_attempt(
                    ip_address=ip_address,
                    username=username,
                    user_agent=user_agent,
                    attempt_type='blocked_request',
                    success=False,
                    failure_reason=rate_limit_result.get('block_reason', 'Rate limit exceeded')
                )
                
                logger.warning(f"Rate limit exceeded for {ip_address} (user: {username})")
                
                # Return rate limit exceeded response
                return HttpResponseTooManyRequests(
                    json.dumps({
                        'error': 'Rate limit exceeded',
                        'message': rate_limit_result.get('block_reason'),
                        'retry_after_minutes': self.time_window_minutes
                    }),
                    content_type='application/json'
                )
                
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Continue processing if rate limiting fails (fail open)
        
        # Process the request
        response = self.get_response(request)
        
        # Log the attempt after processing (for login attempts)
        if request.method == 'POST' and any(request.path.startswith(path) for path in ['/login/', '/accounts/login/']):
            try:
                success = response.status_code in [200, 302]  # Successful login typically redirects
                failure_reason = None if success else f"HTTP {response.status_code}"
                
                RateLimitAttempt.log_attempt(
                    ip_address=ip_address,
                    username=request.POST.get('username') or username,
                    user_agent=user_agent,
                    attempt_type='login',
                    success=success,
                    failure_reason=failure_reason
                )
                
            except Exception as e:
                logger.error(f"Error logging rate limit attempt: {str(e)}")
        
        return response
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# Settings to add to your Django settings.py:
# ENABLE_RATE_LIMITING = True
# RATE_LIMIT_WINDOW_MINUTES = 15
# RATE_LIMIT_MAX_ATTEMPTS = 5
# RATE_LIMIT_PATHS = ['/login/', '/accounts/login/', '/api/']
        '''
        
        print("📝 Rate Limiting Middleware Code:")
        print("Create apps/core/middleware/rate_limiting.py with this code:")
        print("-" * 60)
        print(middleware_code)
        
        return middleware_code
    
    def test_postgresql_rate_limiting(self):
        """Test the PostgreSQL rate limiting functionality"""
        self.print_header("TESTING POSTGRESQL RATE LIMITING")
        
        with connection.cursor() as cursor:
            # Test the rate limiting functions
            test_ip = '192.168.1.100'
            test_username = 'test_user'
            
            print(f"🧪 Testing with IP: {test_ip}, Username: {test_username}")
            
            # Test 1: Check rate limit for clean slate
            cursor.execute("SELECT check_rate_limit(%s, %s)", [test_ip, test_username])
            result = cursor.fetchone()[0]
            print(f"✅ Initial rate limit check: {result}")
            
            # Test 2: Log some failed attempts
            print(f"📝 Logging 3 failed attempts...")
            for i in range(3):
                cursor.execute("""
                    SELECT log_rate_limit_attempt(%s, %s, %s, %s, %s, %s)
                """, [
                    test_ip, 
                    test_username,
                    'Mozilla/5.0 Test Browser',
                    'login',
                    False,  # Failed attempt
                    f'Invalid password attempt {i+1}'
                ])
                attempt_id = cursor.fetchone()[0]
                print(f"   Attempt {i+1} logged with ID: {attempt_id}")
            
            # Test 3: Check rate limit after failed attempts
            cursor.execute("SELECT check_rate_limit(%s, %s)", [test_ip, test_username])
            result = cursor.fetchone()[0]
            print(f"✅ Rate limit after 3 failures: {result}")
            
            # Test 4: Log 3 more attempts to trigger blocking
            print(f"📝 Logging 3 more failed attempts to trigger blocking...")
            for i in range(3):
                cursor.execute("""
                    SELECT log_rate_limit_attempt(%s, %s, %s, %s, %s, %s)
                """, [test_ip, test_username, 'Mozilla/5.0 Test Browser', 'login', False, f'Blocked attempt {i+1}'])
            
            # Test 5: Check if blocked
            cursor.execute("SELECT check_rate_limit(%s, %s)", [test_ip, test_username])
            result = cursor.fetchone()[0]
            print(f"✅ Rate limit after 6 failures: {result}")
            
            # Test 6: Log successful attempt
            print(f"✅ Logging successful attempt...")
            cursor.execute("""
                SELECT log_rate_limit_attempt(%s, %s, %s, %s, %s, %s)
            """, [test_ip, test_username, 'Mozilla/5.0 Test Browser', 'login', True, None])
            
            # Test 7: Cleanup test data
            cursor.execute(f"DELETE FROM {self.table_name} WHERE ip_address = %s", [test_ip])
            deleted_count = cursor.rowcount
            print(f"🧹 Cleaned up {deleted_count} test records")
            
        print(f"✅ PostgreSQL rate limiting functionality verified!")
    
    def generate_migration_instructions(self):
        """Generate step-by-step migration instructions"""
        self.print_header("MIGRATION INSTRUCTIONS")
        
        instructions = """
🎯 POSTGRESQL RATE LIMITING MIGRATION STEPS:

1. 📋 Database Setup (COMPLETED):
   ✅ Created auth_rate_limit_attempts table
   ✅ Created performance indexes
   ✅ Created PostgreSQL functions

2. 📝 Django Integration (MANUAL STEPS):
   
   Step 2.1: Add the model to your Django app
   - Copy the RateLimitAttempt model to apps/core/models.py
   - Run: python manage.py makemigrations
   - Run: python manage.py migrate
   
   Step 2.2: Create the middleware
   - Create apps/core/middleware/__init__.py (empty file)
   - Create apps/core/middleware/rate_limiting.py
   - Copy the PostgreSQLRateLimitMiddleware code
   
   Step 2.3: Update Django settings
   - Add to MIDDLEWARE (before AuthenticationMiddleware):
     'apps.core.middleware.rate_limiting.PostgreSQLRateLimitMiddleware',
   
   - Add rate limiting configuration:
     ENABLE_RATE_LIMITING = True
     RATE_LIMIT_WINDOW_MINUTES = 15
     RATE_LIMIT_MAX_ATTEMPTS = 5
     RATE_LIMIT_PATHS = ['/login/', '/accounts/login/', '/api/']

3. 🧪 Testing:
   - Test login with correct credentials
   - Test multiple failed login attempts
   - Verify blocking after max attempts
   - Check database records

4. 🔄 Gradual Rollout:
   - Start with ENABLE_RATE_LIMITING = False (monitoring only)
   - Monitor for 1-2 days to ensure no issues
   - Set ENABLE_RATE_LIMITING = True to activate blocking

5. 🧹 Maintenance:
   - Set up periodic cleanup: RateLimitAttempt.cleanup_old_attempts()
   - Monitor table size and performance
   - Consider adding this to your scheduled tasks

6. 📊 Benefits After Migration:
   ✅ Persistent rate limiting (survives restarts)
   ✅ Better audit trail and analytics
   ✅ No Redis dependency for rate limiting
   ✅ Configurable per-path rate limits
   ✅ Username + IP based blocking
        """
        
        print(instructions)
        
        return instructions

def main():
    print("🚀 Starting Phase 1A: Rate Limiting Migration")
    print(f"⏰ Migration started at: {datetime.now()}")
    
    migrator = RateLimitingMigrator()
    
    try:
        # Step 1: Analyze current rate limiting
        migrator.analyze_current_rate_limiting()
        
        # Step 2: Create PostgreSQL infrastructure
        migrator.create_postgresql_rate_limit_table()
        
        # Step 3: Create PostgreSQL functions
        migrator.create_rate_limiting_functions()
        
        # Step 4: Generate Django model
        model_code = migrator.create_django_model()
        
        # Step 5: Generate middleware
        middleware_code = migrator.create_rate_limiting_middleware()
        
        # Step 6: Test functionality
        migrator.test_postgresql_rate_limiting()
        
        # Step 7: Generate migration instructions
        migrator.generate_migration_instructions()
        
        print(f"\n✅ Phase 1A: Rate Limiting Migration preparation completed at: {datetime.now()}")
        print(f"🔄 Next: Follow the manual steps to integrate with Django")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()