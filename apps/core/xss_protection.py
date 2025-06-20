"""
XSS Protection middleware for automatic input sanitization.
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseBadRequest
from apps.core.validation import XSSPrevention
from apps.core.error_handling import ErrorHandler

logger = logging.getLogger('security')


class XSSProtectionMiddleware(MiddlewareMixin):
    """
    Middleware to automatically sanitize request parameters and detect XSS attempts.
    """
    
    def __init__(self, get_response=None):
        """Initialize middleware with get_response callable."""
        self.get_response = get_response
        super().__init__(get_response)
    
    # Paths to exclude from XSS scanning (admin, API endpoints that handle their own validation)
    EXCLUDED_PATHS = [
        '/admin/',
        '/api/',
        '/static/',
        '/media/',
        '/health/',
    ]
    
    # Parameters to exclude from sanitization (may contain legitimate HTML)
    EXCLUDED_PARAMS = [
        'csrfmiddlewaretoken',
        'password',
        'password1',
        'password2',
    ]
    
    def process_request(self, request):
        """
        Process incoming request to detect and sanitize XSS attempts.
        """
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return None
        
        # Check and sanitize GET parameters
        if request.GET:
            cleaned_get = self._sanitize_querydict(request.GET, request)
            if cleaned_get != request.GET:
                request.GET = cleaned_get
        
        # Check and sanitize POST parameters
        if request.POST:
            cleaned_post = self._sanitize_querydict(request.POST, request)
            if cleaned_post != request.POST:
                request.POST = cleaned_post
        
        return None
    
    def _sanitize_querydict(self, querydict, request):
        """
        Sanitize a QueryDict and detect XSS attempts.
        
        Args:
            querydict: Django QueryDict to sanitize
            request: HTTP request object
        
        Returns:
            Sanitized QueryDict or None if malicious content detected
        """
        suspicious_detected = False
        sanitized_data = {}
        
        for key, values in querydict.lists():
            # Skip excluded parameters
            if key in self.EXCLUDED_PARAMS:
                sanitized_data[key] = values
                continue
            
            sanitized_values = []
            for value in values:
                try:
                    # Check for obvious XSS attempts
                    if self._is_xss_attempt(value):
                        suspicious_detected = True
                        self._log_xss_attempt(request, key, value)
                        # Replace with safe placeholder
                        sanitized_values.append('[SANITIZED]')
                    else:
                        # Sanitize the value
                        sanitized_value = XSSPrevention.sanitize_html(value)
                        sanitized_values.append(sanitized_value)
                        
                except Exception as e:
                    # Log sanitization error
                    ErrorHandler.handle_exception(
                        e,
                        context={
                            'middleware': 'XSSProtectionMiddleware',
                            'parameter': key,
                            'value_length': len(str(value))
                        },
                        level='warning'
                    )
                    sanitized_values.append('[ERROR_SANITIZING]')
            
            sanitized_data[key] = sanitized_values
        
        # Return original if no changes needed, otherwise create new QueryDict
        if not suspicious_detected and sanitized_data == dict(querydict.lists()):
            return querydict
        else:
            # Create new QueryDict with sanitized data
            from django.http import QueryDict
            new_querydict = QueryDict(mutable=True)
            for key, values in sanitized_data.items():
                for value in values:
                    new_querydict.appendlist(key, value)
            new_querydict._mutable = False
            return new_querydict
    
    def _is_xss_attempt(self, value):
        """
        Check if a value appears to be an XSS attempt.
        
        Args:
            value: String value to check
        
        Returns:
            True if value appears to be malicious
        """
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        # Check for script tags
        if '<script' in value_lower or '</script>' in value_lower:
            return True
        
        # Check for javascript: URLs
        if 'javascript:' in value_lower:
            return True
        
        # Check for common XSS patterns
        xss_patterns = [
            'eval(',
            'alert(',
            'confirm(',
            'prompt(',
            'document.cookie',
            'document.write',
            'window.location',
            'onerror=',
            'onload=',
            'onclick=',
            'onmouseover=',
            'onfocus=',
            'onblur=',
            '<iframe',
            '<object',
            '<embed',
            '<form',
            'vbscript:',
            'data:text/html',
        ]
        
        for pattern in xss_patterns:
            if pattern in value_lower:
                return True
        
        # Check for encoded script attempts
        if '%3Cscript' in value_lower or '%3C%73%63%72%69%70%74' in value_lower:
            return True
        
        return False
    
    def _log_xss_attempt(self, request, parameter, value):
        """
        Log XSS attempt with request details.
        
        Args:
            request: HTTP request object
            parameter: Parameter name containing XSS
            value: Malicious value
        """
        client_ip = self._get_client_ip(request)
        user = str(request.user) if request.user.is_authenticated else 'Anonymous'
        
        logger.warning(
            f"XSS attempt detected - IP: {client_ip}, User: {user}, "
            f"Path: {request.path}, Parameter: {parameter}, "
            f"Value: {value[:100]}{'...' if len(value) > 100 else ''}"
        )
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CSRFHeaderMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers for XSS and CSRF protection.
    """
    
    def __init__(self, get_response=None):
        """Initialize middleware with get_response callable."""
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_response(self, request, response):
        """
        Add security headers to response.
        """
        # XSS Protection header
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Type Options header
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Referrer Policy header
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (development-friendly)
        if not response.get('Content-Security-Policy'):
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://ajax.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://ajax.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "img-src 'self' data: https: blob:; "
                "font-src 'self' data: https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "object-src 'none';"
            )
            response['Content-Security-Policy'] = csp
        
        return response


def sanitize_template_context(context):
    """
    Sanitize template context to prevent XSS in templates.
    
    Args:
        context: Template context dictionary
    
    Returns:
        Sanitized context dictionary
    """
    if not isinstance(context, dict):
        return context
    
    sanitized = {}
    for key, value in context.items():
        if isinstance(value, str):
            # Only sanitize string values that are not marked as safe
            from django.utils.safestring import SafeData
            if not isinstance(value, SafeData):
                sanitized[key] = XSSPrevention.sanitize_html(value)
            else:
                sanitized[key] = value
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                XSSPrevention.sanitize_html(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            sanitized[key] = sanitize_template_context(value)
        else:
            sanitized[key] = value
    
    return sanitized