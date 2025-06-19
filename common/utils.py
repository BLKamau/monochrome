"""
Common utilities for the Monochrome authentication system.
"""

import re
import uuid
import hashlib
from typing import Dict, Any, Optional, List
from functools import wraps

from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status


class StandardResponseMixin:
    """
    Mixin to provide standardized API responses.
    """
    
    @staticmethod
    def success_response(data: Any = None, message: str = "Success", status_code: int = status.HTTP_200_OK) -> Response:
        """Return a standardized success response."""
        response_data = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response_data['data'] = data
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error_response(message: str = "Error", errors: Dict = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
        """Return a standardized error response."""
        response_data = {
            'success': False,
            'message': message,
        }
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def paginated_response(data: List, page: int, total_pages: int, total_items: int, message: str = "Success") -> Response:
        """Return a standardized paginated response."""
        return Response({
            'success': True,
            'message': message,
            'data': data,
            'pagination': {
                'page': page,
                'total_pages': total_pages,
                'total_items': total_items,
                'items_per_page': len(data)
            }
        }, status=status.HTTP_200_OK)


def generate_unique_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def hash_string(value: str, algorithm: str = 'sha256') -> str:
    """Hash a string using the specified algorithm."""
    if algorithm == 'sha256':
        return hashlib.sha256(value.encode()).hexdigest()
    elif algorithm == 'md5':
        return hashlib.md5(value.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def validate_email_format(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username_format(username: str) -> bool:
    """Validate username format."""
    # Username should be 3-30 characters, alphanumeric with underscores
    pattern = r'^[a-zA-Z0-9_]{3,30}$'
    return re.match(pattern, username) is not None


def mask_email(email: str) -> str:
    """Mask email address for privacy."""
    if '@' not in email:
        return email
    
    username, domain = email.split('@')
    if len(username) <= 3:
        masked_username = '*' * len(username)
    else:
        masked_username = username[:2] + '*' * (len(username) - 3) + username[-1]
    
    return f"{masked_username}@{domain}"


def mask_phone_number(phone: str) -> str:
    """Mask phone number for privacy."""
    if len(phone) < 10:
        return '*' * len(phone)
    
    # Show first 3 and last 2 digits
    return phone[:3] + '*' * (len(phone) - 5) + phone[-2:]


def get_client_info(request) -> Dict[str, str]:
    """Extract client information from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    return {
        'ip_address': ip_address,
        'user_agent': user_agent,
        'referer': request.META.get('HTTP_REFERER', ''),
        'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
    }


def cache_key_wrapper(prefix: str):
    """Decorator to add prefix to cache keys."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Modify cache key if provided
            if 'cache_key' in kwargs:
                kwargs['cache_key'] = f"{prefix}:{kwargs['cache_key']}"
            return func(*args, **kwargs)
        return wrapper
    return decorator


class CacheManager:
    """Manager for handling cache operations."""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get value from cache."""
        return cache.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in cache."""
        if timeout is None:
            timeout = getattr(settings, 'CACHE_TIMEOUT', 300)
        cache.set(key, value, timeout)
    
    @staticmethod
    def delete(key: str) -> None:
        """Delete value from cache."""
        cache.delete(key)
    
    @staticmethod
    def clear_pattern(pattern: str) -> None:
        """Clear all cache keys matching pattern."""
        # Note: This requires a cache backend that supports pattern deletion
        # For Redis: cache._cache.delete_pattern(f"*{pattern}*")
        pass


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove any path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace problematic characters
    filename = re.sub(r'[^\w\s.-]', '_', filename)
    
    # Remove multiple spaces/underscores
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 255 - len(ext) - 1
        filename = f"{name[:max_name_length]}.{ext}" if ext else name[:255]
    
    return filename


def parse_bool(value: Any) -> bool:
    """Parse various representations of boolean values."""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on', 't', 'y')
    
    return bool(value)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to specified length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def generate_random_string(length: int = 32, chars: str = None) -> str:
    """Generate a random string of specified length."""
    import string
    import secrets
    
    if chars is None:
        chars = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(chars) for _ in range(length))


def calculate_password_entropy(password: str) -> float:
    """Calculate password entropy in bits."""
    import math
    
    charset_size = 0
    
    if any(c.islower() for c in password):
        charset_size += 26
    if any(c.isupper() for c in password):
        charset_size += 26
    if any(c.isdigit() for c in password):
        charset_size += 10
    if any(c in string.punctuation for c in password):
        charset_size += len(string.punctuation)
    
    if charset_size == 0:
        return 0.0
    
    entropy = len(password) * math.log2(charset_size)
    return round(entropy, 2)


class APIThrottle:
    """Simple API throttling utility."""
    
    def __init__(self, rate: str = "100/hour"):
        """
        Initialize throttle with rate string.
        Example: "100/hour", "10/minute", "1000/day"
        """
        self.parse_rate(rate)
    
    def parse_rate(self, rate: str) -> None:
        """Parse rate string."""
        num, period = rate.split('/')
        self.num_requests = int(num)
        
        period_seconds = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400,
        }
        
        self.duration = period_seconds.get(period, 3600)
    
    def allow_request(self, identifier: str) -> bool:
        """Check if request is allowed."""
        key = f"throttle:{identifier}"
        current_count = CacheManager.get(key, 0)
        
        if current_count >= self.num_requests:
            return False
        
        CacheManager.set(key, current_count + 1, self.duration)
        return True
    
    def get_wait_time(self, identifier: str) -> Optional[int]:
        """Get wait time in seconds until next request is allowed."""
        # This is a simplified implementation
        # In production, store timestamps for accurate wait time
        return self.duration


def validate_password_complexity(password: str) -> Dict[str, Any]:
    """Validate password complexity and return detailed feedback."""
    issues = []
    score = 0
    
    # Length check
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    else:
        score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
    
    # Character type checks
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    if not has_lower:
        issues.append("Password must contain lowercase letters")
    else:
        score += 1
    
    if not has_upper:
        issues.append("Password must contain uppercase letters")
    else:
        score += 1
    
    if not has_digit:
        issues.append("Password must contain numbers")
    else:
        score += 1
    
    if not has_special:
        issues.append("Password must contain special characters")
    else:
        score += 1
    
    # Common password check (simplified)
    common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein']
    if password.lower() in common_passwords:
        issues.append("Password is too common")
        score = max(0, score - 3)
    
    # Calculate entropy
    entropy = calculate_password_entropy(password)
    
    # Determine strength
    if score >= 6 and entropy >= 60:
        strength = "strong"
    elif score >= 4 and entropy >= 40:
        strength = "medium"
    else:
        strength = "weak"
    
    return {
        'valid': len(issues) == 0,
        'strength': strength,
        'score': score,
        'entropy': entropy,
        'issues': issues
    }