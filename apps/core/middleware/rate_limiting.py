from django.http import HttpResponse
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
            
        should_rate_limit = any(request.path.startswith(path) for path in self.rate_limit_paths)
        if not should_rate_limit:
            return self.get_response(request)
        
        # Debug logging
        logger.info(f"Rate limiting middleware processing: {request.method} {request.path}")
        
        # Get client information
        ip_address = self.get_client_ip(request)
        username = getattr(request.user, 'username', None) if hasattr(request, 'user') and request.user.is_authenticated else None
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check rate limit before processing request
        try:
            from apps.core.models import RateLimitAttempt  # Adjust import path
            
            # For GET requests, we don't have username yet, so skip blocking
            # Rate limiting should only apply to POST (actual login attempts)
            if request.method == 'GET':
                # No blocking on GET requests
                rate_limit_result = {'is_blocked': False}
            else:
                # For POST requests, get the attempted username
                attempted_username = request.POST.get('username') or request.POST.get('loginid')
                
                if attempted_username:
                    # Check rate limit for this specific username (not IP)
                    rate_limit_result = RateLimitAttempt.check_rate_limit(
                        ip_address=ip_address,  # Still log IP for security records
                        username=attempted_username,  # But rate limit by username
                        time_window_minutes=self.time_window_minutes,
                        max_attempts=self.max_attempts
                    )
                else:
                    # No username provided, allow request to proceed (will fail validation anyway)
                    rate_limit_result = {'is_blocked': False}
            
            if rate_limit_result.get('is_blocked', False):
                # Get the attempted username for blocking
                attempted_username = request.POST.get('username') or request.POST.get('loginid') or username
                
                # Log the blocked attempt
                RateLimitAttempt.log_attempt(
                    ip_address=ip_address,
                    username=attempted_username,
                    user_agent=user_agent,
                    attempt_type='blocked_request',
                    success=False,
                    failure_reason=rate_limit_result.get('block_reason', 'Rate limit exceeded')
                )
                
                blocking_strategy = rate_limit_result.get('blocking_strategy', 'unknown')
                logger.warning(f"Rate limit exceeded for {ip_address} (user: {attempted_username}, strategy: {blocking_strategy})")
                
                # For login pages, show user-friendly error on the form
                if request.path in ['/', '/login/', '/accounts/login/']:
                    from django.shortcuts import render
                    from apps.peoples.forms import LoginForm
                    
                    # Create empty form (don't add errors to avoid validation issues)
                    form = LoginForm()
                    
                    # Calculate retry time
                    retry_minutes = self.time_window_minutes
                    
                    # Get current year for template
                    from datetime import datetime
                    current_year = datetime.now().year
                    
                    # Render the login template with rate limiting flag
                    return render(request, 'peoples/login.html', {
                        'loginform': form,
                        'rate_limited': True,
                        'retry_after_minutes': retry_minutes,
                        'current_year': current_year
                    })
                else:
                    # For API endpoints, return JSON response
                    response = HttpResponse(
                        json.dumps({
                            'error': 'Rate limit exceeded',
                            'message': rate_limit_result.get('block_reason'),
                            'retry_after_minutes': self.time_window_minutes
                        }),
                        content_type='application/json',
                        status=429  # HTTP 429 Too Many Requests
                    )
                    response['Retry-After'] = str(self.time_window_minutes * 60)
                    return response
                
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Continue processing if rate limiting fails (fail open)
        
        # Process the request
        response = self.get_response(request)
        
        # Log the attempt after processing (for login attempts)
        if request.method == 'POST' and any(request.path.startswith(path) for path in ['/', '/login/', '/accounts/login/']):
            try:
                # Better detection of login success/failure
                # Successful login redirects (302) OR contains no form errors
                is_redirect = response.status_code == 302
                
                # Check if response contains login form errors (indicates failure)
                has_form_errors = False
                if hasattr(response, 'content') and response.content:
                    content_str = response.content.decode('utf-8', errors='ignore')
                    # Look for common error indicators in your login form
                    error_indicators = [
                        'alert-danger',
                        'Sorry that didn\'t work',
                        'please try again',
                        'invalid-details',
                        'Authentication failed'
                    ]
                    has_form_errors = any(indicator in content_str for indicator in error_indicators)
                
                # Login is successful if it redirects AND no form errors
                success = is_redirect and not has_form_errors
                
                if not success:
                    if has_form_errors:
                        failure_reason = "Invalid credentials"
                    elif response.status_code != 302:
                        failure_reason = f"HTTP {response.status_code}"
                    else:
                        failure_reason = "Login failed"
                else:
                    failure_reason = None
                
                username_attempted = request.POST.get('username') or request.POST.get('loginid') or username
                
                logger.info(f"Logging login attempt: IP={ip_address}, Username={username_attempted}, Success={success}")
                
                attempt = RateLimitAttempt.log_attempt(
                    ip_address=ip_address,
                    username=username_attempted,
                    user_agent=user_agent,
                    attempt_type='login',
                    success=success,
                    failure_reason=failure_reason
                )
                
                logger.info(f"Logged attempt with ID: {attempt.id}")
                
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