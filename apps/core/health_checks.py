"""
Production Health Check System for YOUTILITY3
Provides comprehensive health monitoring for production deployment
"""

import json
import time
import logging
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.db import connection, connections
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


class HealthCheckManager:
    """Centralized health check management"""
    
    def __init__(self):
        self.checks = {}
        self.start_time = time.time()
    
    def register_check(self, name, check_func, critical=True):
        """Register a health check function"""
        self.checks[name] = {
            'func': check_func,
            'critical': critical,
            'last_run': None,
            'last_result': None
        }
    
    def run_check(self, name):
        """Run a specific health check"""
        if name not in self.checks:
            return {'status': 'error', 'message': f'Unknown check: {name}'}
        
        check = self.checks[name]
        start_time = time.time()
        
        try:
            result = check['func']()
            result['duration_ms'] = round((time.time() - start_time) * 1000, 2)
            result['timestamp'] = timezone.now().isoformat()
            
            check['last_run'] = timezone.now()
            check['last_result'] = result
            
            return result
        except Exception as e:
            logger.exception(f"Health check '{name}' failed")
            error_result = {
                'status': 'error',
                'message': str(e),
                'duration_ms': round((time.time() - start_time) * 1000, 2),
                'timestamp': timezone.now().isoformat()
            }
            check['last_result'] = error_result
            return error_result
    
    def run_all_checks(self):
        """Run all registered health checks"""
        results = {}
        overall_status = 'healthy'
        
        for name, check in self.checks.items():
            result = self.run_check(name)
            results[name] = result
            
            if result['status'] != 'healthy' and check['critical']:
                overall_status = 'unhealthy'
            elif result['status'] != 'healthy' and overall_status == 'healthy':
                overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'uptime_seconds': round(time.time() - self.start_time, 2),
            'checks': results
        }


# Global health check manager
health_manager = HealthCheckManager()


def check_database():
    """Check PostgreSQL database connectivity and performance"""
    try:
        start_time = time.time()
        
        # Test main database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Check database version and status
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]
        
        # Test performance with a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_session")
            session_count = cursor.fetchone()[0]
        
        query_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'status': 'healthy',
            'database_version': db_version.split()[0:2],  # PostgreSQL version
            'session_count': session_count,
            'query_time_ms': query_time,
            'connection_status': 'connected'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Database connection failed: {str(e)}',
            'connection_status': 'failed'
        }


def check_postgresql_functions():
    """Check if custom PostgreSQL functions are available"""
    try:
        functions_to_check = [
            'check_rate_limit',
            'cleanup_expired_sessions', 
            'cleanup_select2_cache',
            'refresh_select2_materialized_views'
        ]
        
        function_status = {}
        
        with connection.cursor() as cursor:
            for func_name in functions_to_check:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc 
                        WHERE proname = %s
                    )
                """, [func_name])
                exists = cursor.fetchone()[0]
                function_status[func_name] = 'available' if exists else 'missing'
        
        all_functions_available = all(status == 'available' for status in function_status.values())
        
        return {
            'status': 'healthy' if all_functions_available else 'error',
            'functions': function_status,
            'message': 'All PostgreSQL functions available' if all_functions_available else 'Some functions missing'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Function check failed: {str(e)}'
        }


def check_cache():
    """Check cache backend functionality"""
    try:
        # Test cache write and read
        test_key = f'health_check_{int(time.time())}'
        test_value = {'test': True, 'timestamp': timezone.now().isoformat()}
        
        cache.set(test_key, test_value, 10)
        retrieved_value = cache.get(test_key)
        
        if retrieved_value == test_value:
            cache.delete(test_key)
            return {
                'status': 'healthy',
                'backend': cache.__class__.__name__,
                'message': 'Cache read/write successful'
            }
        else:
            return {
                'status': 'error',
                'backend': cache.__class__.__name__,
                'message': 'Cache read/write failed'
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Cache check failed: {str(e)}'
        }


def check_task_queue():
    """Check PostgreSQL task queue status"""
    try:
        from apps.core.models import RateLimitAttempt
        
        # Check if task queue tables exist and are accessible
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name LIKE '%task%' OR table_name = 'auth_rate_limit_attempts'
            """)
            table_count = cursor.fetchone()[0]
        
        # Test rate limiting system (part of task queue infrastructure)
        recent_attempts = RateLimitAttempt.objects.filter(
            attempt_time__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        return {
            'status': 'healthy',
            'task_tables_available': table_count > 0,
            'recent_rate_limit_attempts': recent_attempts,
            'message': 'PostgreSQL task queue system operational'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Task queue check failed: {str(e)}'
        }


def check_application_status():
    """Check overall application health"""
    try:
        # Check if DEBUG is disabled in production
        debug_status = getattr(settings, 'DEBUG', True)
        
        # Check if required settings are configured
        required_settings = ['SECRET_KEY', 'ALLOWED_HOSTS', 'DATABASES']
        missing_settings = [setting for setting in required_settings 
                          if not hasattr(settings, setting)]
        
        # Check installed apps
        critical_apps = ['django.contrib.auth', 'django.contrib.sessions', 'apps.core']
        missing_apps = [app for app in critical_apps 
                       if app not in settings.INSTALLED_APPS]
        
        issues = []
        if debug_status:
            issues.append('DEBUG is enabled (should be False in production)')
        if missing_settings:
            issues.append(f'Missing settings: {missing_settings}')
        if missing_apps:
            issues.append(f'Missing critical apps: {missing_apps}')
        
        return {
            'status': 'healthy' if not issues else 'warning',
            'debug_enabled': debug_status,
            'missing_settings': missing_settings,
            'missing_apps': missing_apps,
            'issues': issues,
            'message': 'Application configuration OK' if not issues else f'{len(issues)} configuration issues'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Application status check failed: {str(e)}'
        }


# Register all health checks
health_manager.register_check('database', check_database, critical=True)
health_manager.register_check('postgresql_functions', check_postgresql_functions, critical=True)
health_manager.register_check('cache', check_cache, critical=False)
health_manager.register_check('task_queue', check_task_queue, critical=True)
health_manager.register_check('application', check_application_status, critical=False)


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Basic health check endpoint
    Returns 200 if application is healthy, 503 if unhealthy
    """
    try:
        result = health_manager.run_all_checks()
        
        status_code = 200
        if result['status'] == 'unhealthy':
            status_code = 503
        elif result['status'] == 'degraded':
            status_code = 200  # Still operational
        
        return JsonResponse(result, status=status_code)
    except Exception as e:
        logger.exception("Health check failed")
        return JsonResponse({
            'status': 'error',
            'message': f'Health check system error: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=503)


@csrf_exempt  
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check endpoint for container orchestration
    Returns 200 only if all critical systems are operational
    """
    try:
        result = health_manager.run_all_checks()
        
        # For readiness, we're stricter - any critical system failure = not ready
        if result['status'] in ['healthy', 'degraded']:
            return JsonResponse({
                'status': 'ready',
                'timestamp': result['timestamp'],
                'message': 'Application ready to serve traffic'
            }, status=200)
        else:
            return JsonResponse({
                'status': 'not_ready',
                'timestamp': result['timestamp'],
                'message': 'Application not ready - critical systems failing',
                'details': result['checks']
            }, status=503)
    except Exception as e:
        logger.exception("Readiness check failed")
        return JsonResponse({
            'status': 'not_ready',
            'message': f'Readiness check system error: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=503)


@csrf_exempt
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check endpoint for container orchestration
    Simple check to verify the application process is alive
    """
    try:
        return JsonResponse({
            'status': 'alive',
            'timestamp': timezone.now().isoformat(),
            'uptime_seconds': round(time.time() - health_manager.start_time, 2),
            'message': 'Application process is alive'
        }, status=200)
    except Exception as e:
        logger.exception("Liveness check failed")
        return HttpResponse("Application process error", status=503)


@csrf_exempt
@require_http_methods(["GET"])
def detailed_health_check(request):
    """
    Detailed health check with all system information
    For monitoring systems and debugging
    """
    try:
        result = health_manager.run_all_checks()
        
        # Add system information
        result['system_info'] = {
            'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
            'python_version': f"{settings.VERSION_INFO[0]}.{settings.VERSION_INFO[1]}" if hasattr(settings, 'VERSION_INFO') else 'unknown',
            'debug_mode': getattr(settings, 'DEBUG', True),
            'environment': getattr(settings, 'ENVIRONMENT', 'unknown')
        }
        
        return JsonResponse(result, status=200)
    except Exception as e:
        logger.exception("Detailed health check failed")
        return JsonResponse({
            'status': 'error',
            'message': f'Detailed health check failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=503)