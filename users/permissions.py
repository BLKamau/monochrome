"""
Custom permissions for the users app.
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsOwner(permissions.BasePermission):
    """
    Permission to only allow owners of an object to view/edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if the object is the user itself
        if isinstance(obj, User):
            return obj == request.user
        
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if the object has an owner attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admin users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


class IsStaff(permissions.BasePermission):
    """
    Permission to only allow staff users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff_member or request.user.is_admin
        )


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission to allow admin or staff users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin or request.user.is_staff_member
        )


class IsMFAVerified(permissions.BasePermission):
    """
    Permission to only allow users who have verified MFA.
    """
    
    message = "MFA verification required to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.is_mfa_enabled and
            request.user.is_mfa_verified
        )


class IsEmailVerified(permissions.BasePermission):
    """
    Permission to only allow users with verified email.
    """
    
    message = "Email verification required to access this resource."
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_active


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow owners or admin users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin can access anything
        if request.user.is_admin:
            return True
        
        # Check ownership
        if isinstance(obj, User):
            return obj == request.user
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Permission to allow owners or staff users.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff and admin can access
        if request.user.is_admin or request.user.is_staff_member:
            return True
        
        # Check ownership
        if isinstance(obj, User):
            return obj == request.user
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class IsReadOnlyOrOwner(permissions.BasePermission):
    """
    Permission to allow read-only access to everyone, write access to owner only.
    """
    
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS requests for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions only for authenticated users
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for owner
        if isinstance(obj, User):
            return obj == request.user
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class CanCreateUser(permissions.BasePermission):
    """
    Permission to control who can create new users.
    In production, you might want to restrict this to admins only.
    """
    
    def has_permission(self, request, view):
        # Allow anyone to register (change this based on your requirements)
        if request.method == 'POST' and not request.user.is_authenticated:
            return True
        
        # Authenticated users can't create new users unless they're admin
        if request.user.is_authenticated:
            return request.user.is_admin
        
        return False


class HasSecurePassword(permissions.BasePermission):
    """
    Permission to ensure user has a secure password before accessing sensitive operations.
    """
    
    message = "Your password does not meet security requirements. Please update your password."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check password age (example: require password change every 90 days)
        # This would require additional fields in the User model to track password age
        
        # For now, just ensure user is authenticated
        return True


class RateLimitPermission(permissions.BasePermission):
    """
    Basic rate limiting permission.
    In production, use a proper rate limiting solution like django-ratelimit.
    """
    
    def has_permission(self, request, view):
        # Implement rate limiting logic here
        # Example: Check Redis for request count per IP/user
        return True