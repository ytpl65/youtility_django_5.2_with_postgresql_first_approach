"""
JSON parsing utilities for handling HTML-encoded JSON data
"""

import json
import html
import urllib.parse
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def safe_json_parse(json_string: str, fallback: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Safely parse JSON string with HTML entity decoding and URL decoding
    
    Args:
        json_string: Raw JSON string that may contain HTML entities or URL encoding
        fallback: Default dict to return if parsing fails
        
    Returns:
        Parsed JSON as dict, or fallback dict if parsing fails
    """
    if fallback is None:
        fallback = {}
        
    if not json_string or json_string in ['null', None, '']:
        return fallback
    
    try:
        # URL decode if necessary
        if json_string.startswith('%'):
            json_string = urllib.parse.unquote(json_string)
        
        # Decode HTML entities (fix for &quot;, &amp;, etc.)
        if '&quot;' in json_string or '&amp;' in json_string or '&#' in json_string:
            decoded_string = html.unescape(json_string)
            logger.debug(f"Decoded HTML entities: {json_string} -> {decoded_string}")
            json_string = decoded_string
        
        return json.loads(json_string)
        
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse JSON: {json_string}, error: {e}")
        return fallback


def safe_json_parse_params(request_get, param_name: str = 'params') -> Dict[str, Any]:
    """
    Safely parse JSON parameters from request.GET with default date range
    
    Args:
        request_get: Django request.GET QueryDict
        param_name: Parameter name to extract from request.GET
        
    Returns:
        Parsed parameters with default 'from' and 'to' date range
    """
    params_raw = request_get.get(param_name, '{}')
    
    # Parse the JSON with HTML entity support
    parsed = safe_json_parse(params_raw, {})
    
    # Ensure required keys exist with default values (last 7 days)
    today = date.today()
    parsed.setdefault('from', (today - timedelta(days=7)).strftime('%Y-%m-%d'))
    parsed.setdefault('to', today.strftime('%Y-%m-%d'))
    
    return parsed


def safe_json_parse_request_params(request_get, param_name: str = 'params') -> Dict[str, Any]:
    """
    Enhanced version of safe_json_parse_params with additional validation
    
    Args:
        request_get: Django request.GET QueryDict
        param_name: Parameter name to extract from request.GET
        
    Returns:
        Parsed parameters with validation and sanitization
    """
    params_raw = request_get.get(param_name, '{}')
    
    # Parse the JSON with HTML entity support
    parsed = safe_json_parse(params_raw, {})
    
    # Validate and sanitize common parameters
    if 'from' in parsed:
        try:
            # Validate date format
            from datetime import datetime
            datetime.strptime(parsed['from'], '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Invalid 'from' date format: {parsed['from']}, using default")
            parsed['from'] = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    if 'to' in parsed:
        try:
            # Validate date format
            from datetime import datetime
            datetime.strptime(parsed['to'], '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Invalid 'to' date format: {parsed['to']}, using default")
            parsed['to'] = date.today().strftime('%Y-%m-%d')
    
    # Ensure required keys exist with default values
    today = date.today()
    parsed.setdefault('from', (today - timedelta(days=7)).strftime('%Y-%m-%d'))
    parsed.setdefault('to', today.strftime('%Y-%m-%d'))
    
    return parsed