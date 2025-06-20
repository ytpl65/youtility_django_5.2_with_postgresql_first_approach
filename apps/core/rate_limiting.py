"""
Rate limiting utilities for login attempts and other security-sensitive operations.
"""
from django.core.cache import cache
from django.http import HttpResponse
from functools import wraps
import time
import logging

logger = logging.getLogger('security')

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass

def get_client_ip(request):
    """Get the real client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_rate_limit(key, limit=5, window=300):
    """
    Check if rate limit is exceeded for a given key.
    
    Args:
        key: Unique identifier for rate limiting (e.g., IP address + action)
        limit: Maximum number of attempts allowed
        window: Time window in seconds (default: 5 minutes)
    
    Returns:
        dict: {'allowed': bool, 'remaining': int, 'reset_time': int}
    """
    current_time = int(time.time())
    cache_key = f"rate_limit:{key}"
    
    # Get current attempts
    attempts = cache.get(cache_key, [])
    
    # Remove old attempts outside the window
    attempts = [attempt_time for attempt_time in attempts 
               if current_time - attempt_time < window]
    
    if len(attempts) >= limit:
        # Rate limit exceeded
        oldest_attempt = min(attempts) if attempts else current_time
        reset_time = oldest_attempt + window
        
        logger.warning(f"Rate limit exceeded for key: {key}. "
                      f"Attempts: {len(attempts)}/{limit}")
        
        return {
            'allowed': False,
            'remaining': 0,
            'reset_time': reset_time
        }
    
    # Add current attempt
    attempts.append(current_time)
    cache.set(cache_key, attempts, window)
    
    return {
        'allowed': True,
        'remaining': limit - len(attempts),
        'reset_time': current_time + window
    }

def rate_limit_login(max_attempts=5, window=300):
    """
    Decorator for rate limiting login attempts per IP address.
    
    Args:
        max_attempts: Maximum login attempts allowed
        window: Time window in seconds (default: 5 minutes)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(self, request, *args, **kwargs):
            if request.method == 'POST':
                client_ip = get_client_ip(request)
                rate_limit_key = f"login_attempts:{client_ip}"
                
                rate_limit_result = check_rate_limit(
                    rate_limit_key, 
                    limit=max_attempts, 
                    window=window
                )
                
                if not rate_limit_result['allowed']:
                    logger.warning(f"Login rate limit exceeded for IP: {client_ip}")
                    
                    # Create rate limit response (HTTP 429)
                    response = HttpResponse(
                        "Too many login attempts. Please try again later.",
                        status=429
                    )
                    response['X-RateLimit-Limit'] = str(max_attempts)
                    response['X-RateLimit-Remaining'] = '0'
                    response['X-RateLimit-Reset'] = str(rate_limit_result['reset_time'])
                    return response
            
            return view_func(self, request, *args, **kwargs)
        return wrapped_view
    return decorator

def record_failed_login(request, username=None):
    """
    Record a failed login attempt for monitoring and additional rate limiting.
    
    Args:
        request: Django request object
        username: Username that was attempted (optional)
    """
    client_ip = get_client_ip(request)
    
    # Rate limit by IP
    ip_key = f"failed_login_ip:{client_ip}"
    check_rate_limit(ip_key, limit=10, window=3600)  # 10 attempts per hour
    
    # Rate limit by username if provided
    if username:
        username_key = f"failed_login_user:{username}"
        check_rate_limit(username_key, limit=3, window=1800)  # 3 attempts per 30 minutes
        
        logger.warning(f"Failed login attempt - IP: {client_ip}, Username: {username}")
    else:
        logger.warning(f"Failed login attempt - IP: {client_ip}")

def is_ip_blocked(request):
    """
    Check if an IP address should be blocked due to excessive failed attempts.
    
    Returns:
        bool: True if IP should be blocked
    """
    client_ip = get_client_ip(request)
    ip_key = f"failed_login_ip:{client_ip}"
    
    rate_limit_result = check_rate_limit(ip_key, limit=10, window=3600)
    return not rate_limit_result['allowed']

def is_username_blocked(username):
    """
    Check if a username should be blocked due to excessive failed attempts.
    
    Returns:
        bool: True if username should be blocked
    """
    username_key = f"failed_login_user:{username}"
    rate_limit_result = check_rate_limit(username_key, limit=3, window=1800)
    return not rate_limit_result['allowed']