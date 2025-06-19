"""
Custom exceptions and exception handlers for the Monochrome authentication system.
"""

from typing import Optional, Dict, Any

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class MonochromeAPIException(APIException):
    """Base exception class for Monochrome API."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'An error occurred.'
    default_code = 'error'
    
    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail, code)


class AuthenticationFailed(MonochromeAPIException):
    """Exception for authentication failures."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication failed.'
    default_code = 'authentication_failed'


class MFARequired(MonochromeAPIException):
    """Exception when MFA is required but not provided."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Multi-factor authentication required.'
    default_code = 'mfa_required'
    
    def __init__(self, user_id: Optional[int] = None, detail=None):
        super().__init__(detail)
        self.user_id = user_id


class AccountLocked(MonochromeAPIException):
    """Exception when account is locked."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Account is locked due to security reasons.'
    default_code = 'account_locked'
    
    def __init__(self, locked_until=None, detail=None):
        super().__init__(detail)
        self.locked_until = locked_until


class EmailNotVerified(MonochromeAPIException):
    """Exception when email is not verified."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Email verification required.'
    default_code = 'email_not_verified'


class InvalidToken(MonochromeAPIException):
    """Exception for invalid tokens."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid or expired token.'
    default_code = 'invalid_token'


class RateLimitExceeded(MonochromeAPIException):
    """Exception when rate limit is exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Rate limit exceeded. Please try again later.'
    default_code = 'rate_limit_exceeded'
    
    def __init__(self, wait_time: Optional[int] = None, detail=None):
        super().__init__(detail)
        self.wait_time = wait_time


class InvalidMFAToken(MonochromeAPIException):
    """Exception for invalid MFA tokens."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid MFA token.'
    default_code = 'invalid_mfa_token'


class MFASetupRequired(MonochromeAPIException):
    """Exception when MFA setup is required."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'MFA setup required before proceeding.'
    default_code = 'mfa_setup_required'


class PasswordTooWeak(MonochromeAPIException):
    """Exception for weak passwords."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Password does not meet security requirements.'
    default_code = 'password_too_weak'
    
    def __init__(self, issues: Optional[list] = None, detail=None):
        super().__init__(detail)
        self.issues = issues or []


class DuplicateEmail(MonochromeAPIException):
    """Exception for duplicate email addresses."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Email address already registered.'
    default_code = 'duplicate_email'


class DuplicateUsername(MonochromeAPIException):
    """Exception for duplicate usernames."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Username already taken.'
    default_code = 'duplicate_username'


class InsufficientPermissions(MonochromeAPIException):
    """Exception for insufficient permissions."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Insufficient permissions to perform this action.'
    default_code = 'insufficient_permissions'


class ResourceNotFound(MonochromeAPIException):
    """Exception for resource not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Resource not found.'
    default_code = 'not_found'


class InvalidRequest(MonochromeAPIException):
    """Exception for invalid requests."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid request.'
    default_code = 'invalid_request'


class ServiceUnavailable(MonochromeAPIException):
    """Exception when a service is unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable.'
    default_code = 'service_unavailable'


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    Custom exception handler that provides consistent error responses.
    """
    # Call DRF's default exception handler first
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response_data = {
            'success': False,
            'message': 'An error occurred',
            'errors': {}
        }
        
        # Handle different exception types
        if isinstance(exc, MonochromeAPIException):
            custom_response_data['message'] = str(exc.detail)
            custom_response_data['code'] = exc.default_code
            
            # Add extra data for specific exceptions
            if isinstance(exc, MFARequired) and exc.user_id:
                custom_response_data['user_id'] = exc.user_id
                custom_response_data['requires_mfa'] = True
            elif isinstance(exc, AccountLocked) and exc.locked_until:
                custom_response_data['locked_until'] = exc.locked_until
            elif isinstance(exc, RateLimitExceeded) and exc.wait_time:
                custom_response_data['wait_time'] = exc.wait_time
            elif isinstance(exc, PasswordTooWeak) and exc.issues:
                custom_response_data['errors']['password'] = exc.issues
        
        elif isinstance(exc, Http404):
            custom_response_data['message'] = 'Resource not found'
            custom_response_data['code'] = 'not_found'
        
        elif isinstance(exc, PermissionDenied):
            custom_response_data['message'] = 'Permission denied'
            custom_response_data['code'] = 'permission_denied'
        
        elif isinstance(exc, DjangoValidationError):
            custom_response_data['message'] = 'Validation error'
            custom_response_data['errors'] = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
        
        else:
            # For other exceptions, try to extract meaningful error data
            if hasattr(response, 'data'):
                if isinstance(response.data, dict):
                    if 'detail' in response.data:
                        custom_response_data['message'] = str(response.data['detail'])
                    # Handle field errors
                    for key, value in response.data.items():
                        if key != 'detail':
                            custom_response_data['errors'][key] = value if isinstance(value, list) else [value]
                elif isinstance(response.data, list):
                    custom_response_data['errors']['detail'] = response.data
                else:
                    custom_response_data['message'] = str(response.data)
        
        response.data = custom_response_data
    
    return response


class ExceptionMiddleware:
    """
    Middleware to catch and handle exceptions globally.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception as e:
            # Log the exception
            import logging
            logger = logging.getLogger('monochrome')
            logger.exception(f"Unhandled exception: {str(e)}")
            
            # Return a generic error response
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': 'An unexpected error occurred',
                'code': 'internal_error'
            }, status=500)
        
        return response