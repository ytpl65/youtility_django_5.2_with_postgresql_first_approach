"""
Production Monitoring and Logging Configuration for YOUTILITY3
Comprehensive monitoring setup for production deployment
"""

import logging
import json
import time
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import connection
from django.core.management.base import BaseCommand
import threading


class ProductionMonitor:
    """Production monitoring system for YOUTILITY3"""
    
    def __init__(self):
        self.metrics = {
            'requests': 0,
            'errors': 0,
            'db_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'task_queue_size': 0,
            'active_sessions': 0
        }
        self.start_time = time.time()
        self.last_metrics_reset = timezone.now()
        
    def increment_metric(self, metric_name, value=1):
        """Increment a metric counter"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
    
    def get_metrics(self):
        """Get current metrics snapshot"""
        uptime = time.time() - self.start_time
        
        # Get database metrics
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_session WHERE expire_date > NOW()")
                active_sessions = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM auth_rate_limit_attempts WHERE attempt_time > NOW() - INTERVAL '1 hour'")
                recent_rate_limits = cursor.fetchone()[0]
        except:
            active_sessions = 0
            recent_rate_limits = 0
        
        return {
            'timestamp': timezone.now().isoformat(),
            'uptime_seconds': round(uptime, 2),
            'metrics': self.metrics.copy(),
            'database': {
                'active_sessions': active_sessions,
                'recent_rate_limits': recent_rate_limits
            },
            'system': {
                'debug_mode': getattr(settings, 'DEBUG', True),
                'environment': getattr(settings, 'ENVIRONMENT', 'unknown')
            }
        }
    
    def reset_metrics(self):
        """Reset metric counters"""
        for key in self.metrics:
            self.metrics[key] = 0
        self.last_metrics_reset = timezone.now()


# Global monitor instance
production_monitor = ProductionMonitor()


class ProductionLoggingMiddleware:
    """Middleware for production request logging and monitoring"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('production.requests')
    
    def __call__(self, request):
        start_time = time.time()
        
        # Log request start
        self.logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'remote_addr': self.get_client_ip(request),
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None
            }
        )
        
        # Increment request counter
        production_monitor.increment_metric('requests')
        
        try:
            response = self.get_response(request)
            
            # Log successful response
            duration = round((time.time() - start_time) * 1000, 2)
            self.logger.info(
                f"Request completed: {request.method} {request.path} - {response.status_code} ({duration}ms)",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': duration,
                    'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = round((time.time() - start_time) * 1000, 2)
            production_monitor.increment_metric('errors')
            
            self.logger.error(
                f"Request failed: {request.method} {request.path} - {str(e)} ({duration}ms)",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'error': str(e),
                    'duration_ms': duration,
                    'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None
                },
                exc_info=True
            )
            raise
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DatabaseQueryLoggingMiddleware:
    """Middleware for monitoring database query performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('production.database')
    
    def __call__(self, request):
        # Reset query tracking
        queries_before = len(connection.queries)
        
        response = self.get_response(request)
        
        # Log query statistics
        queries_after = len(connection.queries)
        query_count = queries_after - queries_before
        
        if query_count > 0:
            production_monitor.increment_metric('db_queries', query_count)
            
            # Log slow requests (>10 queries or >100ms total)
            total_time = sum(float(q['time']) for q in connection.queries[queries_before:])
            
            if query_count > 10 or total_time > 0.1:
                self.logger.warning(
                    f"High database usage: {request.method} {request.path} - {query_count} queries ({total_time:.3f}s)",
                    extra={
                        'method': request.method,
                        'path': request.path,
                        'query_count': query_count,
                        'total_time': total_time
                    }
                )
        
        return response


# Production logging configuration
PRODUCTION_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'production': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json': {
            'format': json.dumps({
                'timestamp': '%(asctime)s',
                'level': '%(levelname)s',
                'logger': '%(name)s',
                'message': '%(message)s',
                'module': '%(module)s',
                'funcName': '%(funcName)s',
                'lineno': '%(lineno)d'
            }),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'production_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(getattr(settings, 'LOG_DIR', '/var/log/youtility'), 'production.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'production'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(getattr(settings, 'LOG_DIR', '/var/log/youtility'), 'errors.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'production'
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(getattr(settings, 'LOG_DIR', '/var/log/youtility'), 'security.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'production'
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'production'
        }
    },
    'loggers': {
        'production.requests': {
            'handlers': ['production_file', 'console'],
            'level': 'INFO',
            'propagate': False
        },
        'production.database': {
            'handlers': ['production_file'],
            'level': 'INFO',
            'propagate': False
        },
        'production.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False
        },
        'django': {
            'handlers': ['production_file'],
            'level': 'WARNING',
            'propagate': False
        },
        'apps': {
            'handlers': ['production_file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'root': {
            'handlers': ['production_file', 'error_file', 'console'],
            'level': 'WARNING'
        }
    }
}


def setup_production_logging():
    """Setup production logging configuration"""
    import logging.config
    
    # Ensure log directory exists
    log_dir = getattr(settings, 'LOG_DIR', '/var/log/youtility')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.config.dictConfig(PRODUCTION_LOGGING_CONFIG)
    
    # Log startup
    logger = logging.getLogger('production.startup')
    logger.info("YOUTILITY3 production logging initialized")
    logger.info(f"Log directory: {log_dir}")
    logger.info(f"Debug mode: {getattr(settings, 'DEBUG', True)}")


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name, logger_name='production.performance'):
        self.operation_name = operation_name
        self.logger = logging.getLogger(logger_name)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(
                f"Operation completed: {self.operation_name} ({duration:.3f}s)",
                extra={'operation': self.operation_name, 'duration': duration}
            )
        else:
            self.logger.error(
                f"Operation failed: {self.operation_name} ({duration:.3f}s) - {exc_val}",
                extra={'operation': self.operation_name, 'duration': duration, 'error': str(exc_val)}
            )


def log_system_metrics():
    """Log current system metrics"""
    logger = logging.getLogger('production.metrics')
    metrics = production_monitor.get_metrics()
    
    logger.info(
        f"System metrics: {metrics['metrics']['requests']} requests, "
        f"{metrics['metrics']['errors']} errors, "
        f"{metrics['database']['active_sessions']} active sessions",
        extra=metrics
    )


# Automatic metrics logging (call this from a scheduled task)
def start_metrics_logging():
    """Start periodic metrics logging"""
    def log_metrics_periodically():
        while True:
            try:
                log_system_metrics()
                time.sleep(300)  # Log every 5 minutes
            except Exception as e:
                logging.getLogger('production.metrics').error(f"Metrics logging failed: {e}")
                time.sleep(60)  # Retry after 1 minute
    
    metrics_thread = threading.Thread(target=log_metrics_periodically, daemon=True)
    metrics_thread.start()
    
    logger = logging.getLogger('production.startup')
    logger.info("Metrics logging started - logging every 5 minutes")