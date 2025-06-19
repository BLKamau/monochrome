"""
Custom middleware for the Monochrome authentication system.
"""

from django.http import JsonResponse
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class MFARequiredMiddleware(MiddlewareMixin):
    """
    Middleware to enforce MFA verification for protected endpoints.
    """
    
    # URLs that don't require MFA
    EXEMPT_URLS = [
        reverse('users:register'),
        reverse('users:login'),
        reverse('users:verify_email'),
        reverse('users:resend_verification'),
        reverse('users:mfa_setup'),
        reverse('users:mfa_verify'),
        reverse('users:mfa_login'),
        reverse('users:password_reset_request'),
        reverse('users:password_reset_confirm'),
        reverse('users:token_refresh'),
        reverse('users:token_verify'),
        '/admin/',
        '/api/docs/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """Check if request requires MFA verification."""
        # Skip for exempt URLs
        for exempt_url in self.EXEMPT_URLS:
            if request.path.startswith(exempt_url):
                return None
        
        # Skip for non-API endpoints
        if not request.path.startswith('/api/'):
            return None
        
        # Try to authenticate the request
        try:
            jwt_auth = JWTAuthentication()
            user, token = jwt_auth.authenticate(request)
            
            if user and user.is_authenticated:
                # Check if user has MFA enabled but not verified in this session
                if user.is_mfa_enabled and not getattr(token, 'is_mfa_verified', False):
                    return JsonResponse({
                        'error': 'MFA verification required',
                        'message': 'Please complete MFA verification to access this resource.',
                        'requires_mfa': True
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Attach user to request for later use
                request.user = user
                request.auth = token
        except (InvalidToken, TokenError):
            # Let DRF handle authentication errors
            pass
        except Exception:
            # Let other middleware/views handle other errors
            pass
        
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.
    """
    
    def process_response(self, request, response):
        """Add security headers to response."""
        # Prevent XSS attacks
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Enable HSTS for HTTPS connections
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content Security Policy
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all API requests for debugging and monitoring.
    """
    
    def process_request(self, request):
        """Log incoming request."""
        # Skip logging for certain paths
        skip_paths = ['/static/', '/media/', '/admin/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Log request details
        import logging
        logger = logging.getLogger('monochrome')
        
        logger.info(f"Request: {request.method} {request.path} from {self.get_client_ip(request)}")
        
        return None
    
    def process_response(self, request, response):
        """Log response status."""
        # Skip logging for certain paths
        skip_paths = ['/static/', '/media/', '/admin/']
        if any(request.path.startswith(path) for path in skip_paths):
            return response
        
        # Log response status
        import logging
        logger = logging.getLogger('monochrome')
        
        logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware(MiddlewareMixin):
    """
    Basic rate limiting middleware.
    In production, use a proper solution like django-ratelimit or Redis-based rate limiting.
    """
    
    # Simple in-memory storage (not suitable for production)
    request_counts = {}
    
    def process_request(self, request):
        """Check rate limits."""
        # Skip for certain paths
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
        
        # Get client identifier (IP or user)
        client_id = self.get_client_id(request)
        
        # Check rate limit (example: 100 requests per minute)
        from datetime import datetime, timedelta
        current_time = datetime.now()
        minute_ago = current_time - timedelta(minutes=1)
        
        # Clean old entries
        self.request_counts = {
            k: v for k, v in self.request_counts.items()
            if v['timestamp'] > minute_ago
        }
        
        # Check current client
        if client_id in self.request_counts:
            if self.request_counts[client_id]['count'] >= 100:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                self.request_counts[client_id]['count'] += 1
        else:
            self.request_counts[client_id] = {
                'count': 1,
                'timestamp': current_time
            }
        
        return None
    
    def get_client_id(self, request):
        """Get unique client identifier."""
        if request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            return f"ip_{self.get_client_ip(request)}"
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip