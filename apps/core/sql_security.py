"""
SQL Injection Protection Middleware
Provides protection against SQL injection attacks at the middleware level.
"""

import logging
import re
from django.http import HttpResponseBadRequest
from django.core.exceptions import SuspiciousOperation
from .error_handling import ErrorHandler

logger = logging.getLogger(__name__)


class SQLInjectionProtectionMiddleware:
    """
    Middleware to detect and prevent SQL injection attempts.
    
    This middleware analyzes incoming requests for common SQL injection patterns
    and blocks suspicious requests before they reach the application logic.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.error_handler = ErrorHandler()
        
        # Common SQL injection patterns to detect
        self.sql_patterns = [
            # Basic SQL injection patterns
            r"('\s*(or|and)\s*'[^']*'|'\s*(or|and)\s*\d+\s*=\s*\d+)",
            r"('\s*;\s*(drop|delete|update|insert|create|alter)\s+)",
            r"('\s*union\s+(all\s+)?select\s+)",
            r"('\s*or\s+\d+\s*=\s*\d+)",
            r"('\s*and\s+\d+\s*=\s*\d+)",
            
            # Advanced SQL injection patterns
            r"(exec\s*\(|execute\s*\(|sp_executesql)",
            r"(xp_cmdshell|sp_makewebtask|sp_oacreate)",
            r"(waitfor\s+delay|benchmark\s*\(|sleep\s*\()",
            
            # Union-based injection
            r"(union\s+(all\s+)?select\s+null)",
            r"(union\s+(all\s+)?select\s+\d+)",
            
            # Boolean-based blind injection
            r"(\s+and\s+\d+\s*=\s*\d+\s*--)",
            r"(\s+or\s+\d+\s*=\s*\d+\s*--)",
            
            # Time-based blind injection
            r"(if\s*\(\s*\d+\s*=\s*\d+\s*,\s*sleep\s*\(\s*\d+\s*\))",
            
            # Comment-based injection
            r"(/\*.*\*/|--\s+|#)",
            
            # Hex encoding attempts
            r"(0x[0-9a-f]+)",
            
            # Schema discovery attempts
            r"(information_schema|sys\.tables|sys\.columns)",
        ]
        
        # Compile regex patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_patterns]
    
    def __call__(self, request):
        # Check for SQL injection attempts
        if self._detect_sql_injection(request):
            return self._handle_sql_injection_attempt(request)
        
        response = self.get_response(request)
        return response
    
    def _detect_sql_injection(self, request):
        """
        Detect SQL injection attempts in request parameters.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            bool: True if SQL injection pattern detected, False otherwise
        """
        # Check GET parameters
        for param, value in request.GET.items():
            if self._check_value_for_sql_injection(value):
                logger.warning(
                    f"SQL injection attempt detected in GET parameter '{param}': {value}",
                    extra={
                        'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                        'ip': self._get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'path': request.path,
                        'method': request.method,
                    }
                )
                return True
        
        # Check POST parameters
        if hasattr(request, 'POST'):
            for param, value in request.POST.items():
                if self._check_value_for_sql_injection(value):
                    logger.warning(
                        f"SQL injection attempt detected in POST parameter '{param}': {value}",
                        extra={
                            'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                            'ip': self._get_client_ip(request),
                            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                            'path': request.path,
                            'method': request.method,
                        }
                    )
                    return True
        
        # Check JSON body for API requests
        if hasattr(request, 'body') and request.content_type == 'application/json':
            try:
                body_str = request.body.decode('utf-8')
                if self._check_value_for_sql_injection(body_str):
                    logger.warning(
                        f"SQL injection attempt detected in JSON body",
                        extra={
                            'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                            'ip': self._get_client_ip(request),
                            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                            'path': request.path,
                            'method': request.method,
                        }
                    )
                    return True
            except (UnicodeDecodeError, AttributeError):
                # If we can't decode the body, let it pass and be handled elsewhere
                pass
        
        return False
    
    def _check_value_for_sql_injection(self, value):
        """
        Check a single value for SQL injection patterns.
        
        Args:
            value: String value to check
            
        Returns:
            bool: True if SQL injection pattern found, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        # Check against all compiled patterns
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                return True
        
        return False
    
    def _handle_sql_injection_attempt(self, request):
        """
        Handle detected SQL injection attempt.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            HttpResponse: Error response
        """
        error_message = "Suspicious input detected. Request blocked for security reasons."
        
        # Log the attempt
        logger.error(
            f"SQL injection attempt blocked from {self._get_client_ip(request)}",
            extra={
                'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                'ip': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'path': request.path,
                'method': request.method,
                'referer': request.META.get('HTTP_REFERER', ''),
            }
        )
        
        # Return appropriate error response
        if request.path.startswith('/graphql/') or request.content_type == 'application/json':
            # API request - return JSON error
            return self.error_handler.handle_api_error(
                request, 
                SuspiciousOperation(error_message),
                status_code=400
            )
        else:
            # Web request - return HTTP 400
            return HttpResponseBadRequest(error_message)
    
    def _get_client_ip(self, request):
        """
        Get the client IP address from request.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip