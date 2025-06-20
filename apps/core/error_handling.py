"""
Centralized error handling framework for YOUTILITY3.
Provides structured error responses, correlation IDs, and proper logging.
"""
import logging
import traceback
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Union
from django.http import JsonResponse, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, DatabaseError
from django.shortcuts import render

logger = logging.getLogger('error_handler')


class CorrelationIDMiddleware(MiddlewareMixin):
    """
    Middleware to add correlation IDs to all requests for error tracking.
    """
    
    def __init__(self, get_response=None):
        """Initialize middleware with get_response callable."""
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Add correlation ID to request."""
        correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id
        
        # Add to response headers later
        request._correlation_id = correlation_id
        return None
    
    def process_response(self, request, response):
        """Add correlation ID to response headers."""
        if hasattr(request, '_correlation_id'):
            response['X-Correlation-ID'] = request._correlation_id
        return response


class GlobalExceptionMiddleware(MiddlewareMixin):
    """
    Global exception handler middleware for structured error responses.
    """
    
    def __init__(self, get_response=None):
        """Initialize middleware with get_response callable."""
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_exception(self, request, exception):
        """Handle uncaught exceptions with structured responses."""
        correlation_id = getattr(request, 'correlation_id', str(uuid.uuid4()))
        
        # Log the exception with correlation ID
        error_context = {
            'correlation_id': correlation_id,
            'path': request.path,
            'method': request.method,
            'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
        }
        
        logger.error(f"Unhandled exception: {error_context}")
        
        # Determine response type based on request
        if self._is_api_request(request):
            return self._create_api_error_response(exception, correlation_id)
        else:
            return self._create_web_error_response(request, exception, correlation_id)
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_api_request(self, request):
        """Determine if request is for API endpoint."""
        return (
            request.path.startswith('/api/') or 
            request.path.startswith('/graphql/') or
            request.META.get('HTTP_ACCEPT', '').startswith('application/json') or
            request.META.get('CONTENT_TYPE', '').startswith('application/json')
        )
    
    def _create_api_error_response(self, exception, correlation_id):
        """Create structured JSON error response for API requests."""
        if isinstance(exception, ValidationError):
            status_code = 400
            error_code = 'VALIDATION_ERROR'
            message = 'Invalid input data'
        elif isinstance(exception, PermissionDenied):
            status_code = 403
            error_code = 'PERMISSION_DENIED'
            message = 'Access denied'
        elif isinstance(exception, (IntegrityError, DatabaseError)):
            status_code = 500
            error_code = 'DATABASE_ERROR'
            message = 'Database operation failed'
        else:
            status_code = 500
            error_code = 'INTERNAL_ERROR'
            message = 'An unexpected error occurred'
        
        error_response = {
            'error': {
                'code': error_code,
                'message': message,
                'correlation_id': correlation_id,
                'timestamp': datetime.now().isoformat(),
            }
        }
        
        # Add debug info in development
        if settings.DEBUG:
            error_response['error']['debug'] = {
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
            }
        
        return JsonResponse(error_response, status=status_code)
    
    def _create_web_error_response(self, request, exception, correlation_id):
        """Create user-friendly error page for web requests."""
        if isinstance(exception, PermissionDenied):
            template = 'errors/403.html'
            status_code = 403
        elif isinstance(exception, ValidationError):
            template = 'errors/400.html'
            status_code = 400
        else:
            template = 'errors/500.html'
            status_code = 500
        
        context = {
            'correlation_id': correlation_id,
            'error_message': 'An error occurred while processing your request.',
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@youtility.com'),
        }
        
        # Add debug info in development
        if settings.DEBUG:
            context['debug_info'] = {
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
            }
        
        try:
            return render(request, template, context, status=status_code)
        except Exception:
            # Fallback if template rendering fails
            return HttpResponse(
                f'Error {status_code}: An error occurred. Correlation ID: {correlation_id}',
                status=status_code
            )


class ErrorHandler:
    """
    Centralized error handling utility class.
    """
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        level: str = 'error'
    ) -> str:
        """
        Handle an exception with proper logging and return correlation ID.
        
        Args:
            exception: The exception to handle
            context: Additional context information
            correlation_id: Optional correlation ID (will generate if not provided)
            level: Log level ('error', 'warning', 'critical')
        
        Returns:
            Correlation ID for the error
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        error_data = {
            'correlation_id': correlation_id,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc(),
        }
        
        if context:
            error_data['context'] = context
        
        # Log based on level
        log_method = getattr(logger, level, logger.error)
        log_method(f"Exception handled: {error_data}")
        
        return correlation_id
    
    @staticmethod
    def safe_execute(
        func,
        default_return=None,
        exception_types: tuple = (Exception,),
        context: Optional[Dict[str, Any]] = None,
        log_level: str = 'error'
    ):
        """
        Safely execute a function with proper exception handling.
        
        Args:
            func: Function to execute
            default_return: Default value to return on exception
            exception_types: Tuple of exception types to catch
            context: Additional context for logging
            log_level: Log level for exceptions
        
        Returns:
            Function result or default_return on exception
        """
        try:
            return func()
        except exception_types as e:
            ErrorHandler.handle_exception(
                e, 
                context=context, 
                level=log_level
            )
            return default_return
    
    @staticmethod
    def create_error_response(
        message: str,
        error_code: str = 'GENERIC_ERROR',
        status_code: int = 500,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> JsonResponse:
        """
        Create a structured error response for API endpoints.
        
        Args:
            message: User-friendly error message
            error_code: Application-specific error code
            status_code: HTTP status code
            correlation_id: Correlation ID for tracking
            details: Additional error details
        
        Returns:
            JsonResponse with structured error data
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        error_response = {
            'error': {
                'code': error_code,
                'message': message,
                'correlation_id': correlation_id,
                'timestamp': datetime.now().isoformat(),
            }
        }
        
        if details:
            error_response['error']['details'] = details
        
        return JsonResponse(error_response, status=status_code)


class ValidationError(Exception):
    """Custom validation error with structured details."""
    
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class BusinessLogicError(Exception):
    """Custom exception for business logic violations."""
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)


def handle_db_exception(func):
    """
    Decorator to handle database exceptions with proper logging.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            correlation_id = ErrorHandler.handle_exception(
                e,
                context={'function': func.__name__, 'args': str(args)[:100]},
                level='warning'
            )
            raise BusinessLogicError(
                f"Data integrity constraint violated. Correlation ID: {correlation_id}"
            )
        except DatabaseError as e:
            correlation_id = ErrorHandler.handle_exception(
                e,
                context={'function': func.__name__, 'args': str(args)[:100]},
                level='error'
            )
            raise BusinessLogicError(
                f"Database operation failed. Correlation ID: {correlation_id}"
            )
    
    return wrapper


def handle_validation_exception(func):
    """
    Decorator to handle validation exceptions with proper logging.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, TypeError) as e:
            correlation_id = ErrorHandler.handle_exception(
                e,
                context={'function': func.__name__, 'args': str(args)[:100]},
                level='warning'
            )
            raise ValidationError(
                f"Invalid input data. Correlation ID: {correlation_id}"
            )
    
    return wrapper