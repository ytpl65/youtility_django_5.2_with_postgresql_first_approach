"""
Comprehensive input validation and XSS prevention for YOUTILITY3.
"""
import re
import html
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe
from typing import Union, List, Dict, Any, Optional
import logging

# Try to import bleach, fallback to Django utilities if not available
try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

logger = logging.getLogger('validation')


class XSSPrevention:
    """
    Utility class for preventing XSS attacks through input sanitization.
    """
    
    # Allowed HTML tags for rich text fields (very restrictive)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
    }
    
    # Allowed URL protocols
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']
    
    @staticmethod
    def sanitize_html(text: str, allow_tags: bool = False) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.
        
        Args:
            text: Input text that may contain HTML
            allow_tags: Whether to allow safe HTML tags
        
        Returns:
            Sanitized text safe for display
        """
        if not text:
            return text
        
        if allow_tags and HAS_BLEACH:
            # Use bleach to sanitize while preserving safe HTML
            return bleach.clean(
                text,
                tags=XSSPrevention.ALLOWED_TAGS,
                attributes=XSSPrevention.ALLOWED_ATTRIBUTES,
                protocols=XSSPrevention.ALLOWED_PROTOCOLS,
                strip=True
            )
        elif allow_tags:
            # Fallback: strip dangerous tags but allow basic formatting
            # This is less secure than bleach but better than nothing
            return XSSPrevention._fallback_sanitize(text)
        else:
            # For plain text fields, use fallback sanitization and then escape
            # This ensures we remove dangerous content AND escape HTML
            sanitized = XSSPrevention._fallback_sanitize(text)
            return html.escape(sanitized)
    
    @staticmethod
    def sanitize_input(value: Any) -> Any:
        """
        Sanitize various input types.
        
        Args:
            value: Input value of any type
        
        Returns:
            Sanitized value
        """
        if isinstance(value, str):
            return XSSPrevention.sanitize_html(value, allow_tags=False)
        elif isinstance(value, (list, tuple)):
            return [XSSPrevention.sanitize_input(item) for item in value]
        elif isinstance(value, dict):
            return {key: XSSPrevention.sanitize_input(val) for key, val in value.items()}
        else:
            return value
    
    @staticmethod
    def _fallback_sanitize(text: str) -> str:
        """
        Fallback sanitization when bleach is not available.
        Less secure but better than nothing.
        """
        # Remove script tags and other dangerous elements
        dangerous_patterns = [
            r'<\s*script[^>]*>.*?</\s*script\s*>',
            r'<\s*iframe[^>]*>.*?</\s*iframe\s*>',
            r'<\s*object[^>]*>.*?</\s*object\s*>',
            r'<\s*embed[^>]*>.*?</\s*embed\s*>',
            r'<\s*form[^>]*>.*?</\s*form\s*>',
            r'javascript\s*:[^"\']*',  # More comprehensive javascript: removal
            r'vbscript\s*:[^"\']*',
            r'data\s*:\s*text/html[^"\']*',
            r'on\w+\s*=[^"\']*',  # Event handlers
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove all HTML tags for safety (since we don't have bleach)
        text = re.sub(r'<[^>]*>', '', text)
        
        return text
    
    @staticmethod
    def validate_no_script_tags(value: str) -> str:
        """
        Validate that input contains no script tags.
        
        Args:
            value: String to validate
        
        Returns:
            Original value if valid
        
        Raises:
            ValidationError: If script tags are found
        """
        if not value:
            return value
        
        # Check for script tags (case insensitive)
        script_pattern = re.compile(r'<\s*script[^>]*>.*?<\s*/\s*script\s*>', re.IGNORECASE | re.DOTALL)
        if script_pattern.search(value):
            raise ValidationError("Script tags are not allowed in input")
        
        # Check for javascript: URLs
        js_pattern = re.compile(r'javascript\s*:', re.IGNORECASE)
        if js_pattern.search(value):
            raise ValidationError("JavaScript URLs are not allowed")
        
        # Check for on* event handlers
        event_pattern = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
        if event_pattern.search(value):
            raise ValidationError("HTML event handlers are not allowed")
        
        return value


class InputValidator:
    """
    Comprehensive input validation utility.
    """
    
    # Common validation patterns
    PATTERNS = {
        'name': re.compile(r'^[a-zA-Z0-9\s\-_@#.]+$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'phone': re.compile(r'^[\+]?[1-9]?[0-9]{7,15}$'),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'numeric': re.compile(r'^[0-9]+$'),
        'decimal': re.compile(r'^[0-9]+\.?[0-9]*$'),
        'safe_filename': re.compile(r'^[a-zA-Z0-9\-_.\s]+$'),
        'asset_code': re.compile(r'^[a-zA-Z0-9\-_#]+$'),
        'location_code': re.compile(r'^[a-zA-Z0-9\-_/]+$'),
    }
    
    @staticmethod
    def validate_pattern(value: str, pattern_name: str) -> str:
        """
        Validate input against a predefined pattern.
        
        Args:
            value: Input value to validate
            pattern_name: Name of the pattern to use
        
        Returns:
            Original value if valid
        
        Raises:
            ValidationError: If validation fails
        """
        if not value:
            return value
        
        pattern = InputValidator.PATTERNS.get(pattern_name)
        if not pattern:
            raise ValueError(f"Unknown validation pattern: {pattern_name}")
        
        if not pattern.match(value):
            raise ValidationError(f"Invalid {pattern_name} format")
        
        return value
    
    @staticmethod
    def validate_length(value: str, min_length: int = 0, max_length: int = None) -> str:
        """
        Validate string length.
        
        Args:
            value: String to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length
        
        Returns:
            Original value if valid
        
        Raises:
            ValidationError: If length validation fails
        """
        if not value:
            value = ""
        
        if len(value) < min_length:
            raise ValidationError(f"Input must be at least {min_length} characters long")
        
        if max_length and len(value) > max_length:
            raise ValidationError(f"Input must not exceed {max_length} characters")
        
        return value
    
    @staticmethod
    def validate_numeric_range(value: Union[int, float], min_value: float = None, max_value: float = None) -> Union[int, float]:
        """
        Validate numeric range.
        
        Args:
            value: Numeric value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        
        Returns:
            Original value if valid
        
        Raises:
            ValidationError: If range validation fails
        """
        if value is None:
            return value
        
        if min_value is not None and value < min_value:
            raise ValidationError(f"Value must be at least {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValidationError(f"Value must not exceed {max_value}")
        
        return value
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> str:
        """
        Validate file extension.
        
        Args:
            filename: Name of the file
            allowed_extensions: List of allowed extensions (without dots)
        
        Returns:
            Original filename if valid
        
        Raises:
            ValidationError: If extension is not allowed
        """
        if not filename:
            return filename
        
        # Extract extension
        parts = filename.lower().split('.')
        if len(parts) < 2:
            raise ValidationError("File must have an extension")
        
        extension = parts[-1]
        if extension not in [ext.lower() for ext in allowed_extensions]:
            raise ValidationError(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        return filename


class SecureFormMixin:
    """
    Mixin to add security features to Django forms.
    """
    
    # XSS protection settings
    xss_protect_fields = []  # List of field names to protect
    allow_html_fields = []   # List of field names that allow safe HTML
    
    def clean(self):
        """Override to add XSS protection to all fields."""
        cleaned_data = super().clean()
        
        # Apply XSS protection to specified fields
        for field_name in self.xss_protect_fields:
            if field_name in cleaned_data:
                allow_html = field_name in self.allow_html_fields
                cleaned_data[field_name] = XSSPrevention.sanitize_html(
                    cleaned_data[field_name], 
                    allow_tags=allow_html
                )
                
                # Also validate for script tags
                try:
                    XSSPrevention.validate_no_script_tags(cleaned_data[field_name])
                except ValidationError as e:
                    self.add_error(field_name, e)
        
        return cleaned_data


class FileUploadValidator:
    """
    Validator for file uploads with security checks.
    """
    
    # Dangerous file extensions that should never be allowed
    DANGEROUS_EXTENSIONS = [
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
        'php', 'asp', 'aspx', 'jsp', 'py', 'rb', 'pl', 'sh', 'ps1'
    ]
    
    # Maximum file sizes by type (in bytes)
    MAX_FILE_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB for images
        'document': 50 * 1024 * 1024,  # 50MB for documents
        'video': 500 * 1024 * 1024,  # 500MB for videos
        'default': 5 * 1024 * 1024,  # 5MB default
    }
    
    # Allowed MIME types by category
    ALLOWED_MIME_TYPES = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'spreadsheet': ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'text': ['text/plain', 'text/csv'],
    }
    
    @staticmethod
    def validate_file(uploaded_file, file_category: str = 'default'):
        """
        Comprehensive file validation.
        
        Args:
            uploaded_file: Django UploadedFile object
            file_category: Category of file (image, document, etc.)
        
        Raises:
            ValidationError: If file validation fails
        """
        # Validate filename
        filename = uploaded_file.name
        InputValidator.validate_pattern(filename, 'safe_filename')
        
        # Check for dangerous extensions
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        if extension in FileUploadValidator.DANGEROUS_EXTENSIONS:
            raise ValidationError(f"File type '{extension}' is not allowed for security reasons")
        
        # Check file size
        max_size = FileUploadValidator.MAX_FILE_SIZES.get(file_category, FileUploadValidator.MAX_FILE_SIZES['default'])
        if uploaded_file.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValidationError(f"File size exceeds maximum allowed size of {max_size_mb:.1f}MB")
        
        # Validate MIME type if specified
        if file_category in FileUploadValidator.ALLOWED_MIME_TYPES:
            allowed_types = FileUploadValidator.ALLOWED_MIME_TYPES[file_category]
            if uploaded_file.content_type not in allowed_types:
                raise ValidationError(f"File type not allowed. Allowed types: {', '.join(allowed_types)}")
        
        # Check for suspicious content (basic checks)
        FileUploadValidator._check_suspicious_content(uploaded_file)
    
    @staticmethod
    def _check_suspicious_content(uploaded_file):
        """
        Check for suspicious content in uploaded files.
        
        Args:
            uploaded_file: Django UploadedFile object
        
        Raises:
            ValidationError: If suspicious content is found
        """
        # Read first 1KB to check for suspicious patterns
        uploaded_file.seek(0)
        content = uploaded_file.read(1024).decode('utf-8', errors='ignore')
        uploaded_file.seek(0)  # Reset file pointer
        
        # Check for script tags in any file
        if re.search(r'<\s*script[^>]*>', content, re.IGNORECASE):
            raise ValidationError("File contains suspicious script content")
        
        # Check for embedded PHP/ASP code
        if re.search(r'<\?php|<\?=|<%.*%>', content, re.IGNORECASE):
            raise ValidationError("File contains server-side script content")


# Custom form fields with built-in validation
class SecureCharField(forms.CharField):
    """CharField with XSS protection."""
    
    def __init__(self, *args, **kwargs):
        self.pattern_name = kwargs.pop('pattern_name', None)
        super().__init__(*args, **kwargs)
    
    def clean(self, value):
        value = super().clean(value)
        if value:
            # Apply XSS protection
            value = XSSPrevention.sanitize_html(value)
            XSSPrevention.validate_no_script_tags(value)
            
            # Apply pattern validation if specified
            if self.pattern_name:
                value = InputValidator.validate_pattern(value, self.pattern_name)
        
        return value


class SecureEmailField(forms.EmailField):
    """Email field with additional validation."""
    
    def clean(self, value):
        value = super().clean(value)
        if value:
            # Apply XSS protection
            value = XSSPrevention.sanitize_html(value)
            # Validate email pattern
            value = InputValidator.validate_pattern(value, 'email')
        
        return value


class SecureFileField(forms.FileField):
    """File field with security validation."""
    
    def __init__(self, *args, **kwargs):
        self.file_category = kwargs.pop('file_category', 'default')
        super().__init__(*args, **kwargs)
    
    def clean(self, value, initial=None):
        value = super().clean(value, initial)
        if value:
            FileUploadValidator.validate_file(value, self.file_category)
        
        return value


def validate_json_schema(data: dict, schema: dict) -> dict:
    """
    Validate JSON data against a schema.
    
    Args:
        data: JSON data to validate
        schema: Schema definition
    
    Returns:
        Validated data
    
    Raises:
        ValidationError: If validation fails
    """
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return data
    except ImportError:
        logger.warning("jsonschema package not available, performing basic validation")
        # Basic validation fallback
        return _basic_json_validation(data, schema)
    except Exception as e:
        if 'jsonschema' in str(type(e)):
            raise ValidationError(f"Invalid JSON data: {str(e)}")
        else:
            raise ValidationError(f"JSON validation failed: {str(e)}")


def _basic_json_validation(data: dict, schema: dict) -> dict:
    """
    Basic JSON validation fallback when jsonschema is not available.
    """
    # Check required fields
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Check field types and basic constraints
    properties = schema.get('properties', {})
    for field, value in data.items():
        if field in properties:
            field_schema = properties[field]
            field_type = field_schema.get('type')
            
            # Basic type checking
            if field_type == 'string' and not isinstance(value, str):
                raise ValidationError(f"Field '{field}' must be a string")
            elif field_type == 'integer' and not isinstance(value, int):
                raise ValidationError(f"Field '{field}' must be an integer")
            elif field_type == 'number' and not isinstance(value, (int, float)):
                raise ValidationError(f"Field '{field}' must be a number")
            
            # Basic length checking for strings
            if field_type == 'string' and isinstance(value, str):
                min_length = field_schema.get('minLength')
                max_length = field_schema.get('maxLength')
                if min_length and len(value) < min_length:
                    raise ValidationError(f"Field '{field}' is too short")
                if max_length and len(value) > max_length:
                    raise ValidationError(f"Field '{field}' is too long")
    
    return data