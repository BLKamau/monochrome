"""
Service layer for the users app.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import hashlib

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.template.loader import render_to_string
from django.db import transaction
import pyotp

from .models import TOTPDevice, BackupCode, LoginHistory

User = get_user_model()


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Custom token generator for email verification."""
    
    def _make_hash_value(self, user, timestamp):
        """
        Include user's email and active status in the hash.
        This ensures the token is invalidated when email is verified.
        """
        return f"{user.pk}{timestamp}{user.email}{user.is_active}"


class UserService:
    """Service class for user-related operations."""
    
    email_verification_token_generator = EmailVerificationTokenGenerator()
    password_reset_token_generator = PasswordResetTokenGenerator()
    
    @classmethod
    def send_verification_email(cls, user: User) -> bool:
        """Send email verification to user."""
        try:
            # Generate verification token
            token = cls.email_verification_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create verification link
            verification_link = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}"
            
            # Email context
            context = {
                'user': user,
                'verification_link': verification_link,
                'site_name': 'Monochrome',
            }
            
            # Send email
            subject = 'Verify your email - Monochrome'
            message = f"""
            Hello {user.username},
            
            Please verify your email by clicking the link below:
            {verification_link}
            
            If you didn't create an account, please ignore this email.
            
            Best regards,
            Monochrome Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return True
        except Exception as e:
            print(f"Error sending verification email: {str(e)}")
            return False
    
    @classmethod
    def verify_email_token(cls, token: str) -> Dict[str, any]:
        """Verify email verification token."""
        try:
            # Decode the token
            parts = token.split('/')
            if len(parts) != 2:
                return {
                    'success': False,
                    'message': 'Invalid token format.'
                }
            
            uid, token_value = parts
            
            # Get user
            try:
                uid = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return {
                    'success': False,
                    'message': 'Invalid token.'
                }
            
            # Check if already verified
            if user.is_active:
                return {
                    'success': False,
                    'message': 'Email already verified.'
                }
            
            # Verify token
            if cls.email_verification_token_generator.check_token(user, token_value):
                user.is_active = True
                user.save()
                
                return {
                    'success': True,
                    'message': 'Email verified successfully.',
                    'user_id': user.id
                }
            else:
                return {
                    'success': False,
                    'message': 'Invalid or expired token.'
                }
        except Exception as e:
            return {
                'success': False,
                'message': 'Error verifying token.'
            }
    
    @classmethod
    def send_password_reset_email(cls, user: User) -> bool:
        """Send password reset email to user."""
        try:
            # Generate reset token
            token = cls.password_reset_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset link
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
            
            # Send email
            subject = 'Password Reset - Monochrome'
            message = f"""
            Hello {user.username},
            
            You requested a password reset. Click the link below to reset your password:
            {reset_link}
            
            This link will expire in 24 hours.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            Monochrome Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return True
        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            return False
    
    @classmethod
    def reset_password_with_token(cls, token: str, new_password: str) -> Dict[str, any]:
        """Reset password using token."""
        try:
            # Decode the token
            parts = token.split('/')
            if len(parts) != 2:
                return {
                    'success': False,
                    'message': 'Invalid token format.'
                }
            
            uid, token_value = parts
            
            # Get user
            try:
                uid = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return {
                    'success': False,
                    'message': 'Invalid token.'
                }
            
            # Verify token
            if cls.password_reset_token_generator.check_token(user, token_value):
                # Set new password
                user.set_password(new_password)
                user.save()
                
                return {
                    'success': True,
                    'message': 'Password reset successfully.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Invalid or expired token.'
                }
        except Exception as e:
            return {
                'success': False,
                'message': 'Error resetting password.'
            }
    
    @classmethod
    def get_user_stats(cls, user: User) -> Dict[str, any]:
        """Get user statistics."""
        # Get login history stats
        login_history = LoginHistory.objects.filter(user=user)
        successful_logins = login_history.filter(success=True).count()
        failed_logins = login_history.filter(success=False).count()
        last_login = login_history.filter(success=True).first()
        
        # Get device stats
        active_devices = user.totp_devices.filter(verified=True).count()
        backup_codes_remaining = user.backup_codes.filter(used=False).count()
        
        return {
            'total_logins': successful_logins,
            'failed_attempts': failed_logins,
            'last_login': last_login.login_time if last_login else None,
            'last_login_ip': last_login.ip_address if last_login else None,
            'active_mfa_devices': active_devices,
            'backup_codes_remaining': backup_codes_remaining,
            'account_created': user.created_at,
            'email_verified': user.is_active,
            'mfa_enabled': user.is_mfa_enabled,
        }


class MFAService:
    """Service class for MFA-related operations."""
    
    @staticmethod
    def generate_backup_codes(user: User, count: int = 8) -> List[str]:
        """Generate backup codes for user."""
        codes = []
        
        with transaction.atomic():
            for _ in range(count):
                # Generate random 8-character code
                code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                
                # Hash the code before storing
                hashed_code = hashlib.sha256(code.encode()).hexdigest()
                
                # Store hashed version
                BackupCode.objects.create(
                    user=user,
                    code=hashed_code
                )
                
                # Return plain version to user
                codes.append(code)
        
        return codes
    
    @staticmethod
    def verify_backup_code(user: User, code: str) -> bool:
        """Verify a backup code."""
        # Hash the provided code
        hashed_code = hashlib.sha256(code.encode()).hexdigest()
        
        # Find matching unused code
        backup_code = user.backup_codes.filter(
            code=hashed_code,
            used=False
        ).first()
        
        if backup_code:
            backup_code.mark_as_used()
            return True
        
        return False
    
    @staticmethod
    def verify_totp_token(user: User, token: str) -> bool:
        """Verify TOTP token for user."""
        # Get verified devices
        devices = user.totp_devices.filter(verified=True)
        
        for device in devices:
            totp = pyotp.TOTP(device.decrypt_key())
            if totp.verify(token, valid_window=1):
                device.mark_as_used()
                return True
        
        return False
    
    @staticmethod
    def get_user_devices(user: User) -> List[Dict[str, any]]:
        """Get all MFA devices for user."""
        devices = []
        
        for device in user.totp_devices.all():
            devices.append({
                'id': device.id,
                'name': device.name,
                'verified': device.verified,
                'created_at': device.created_at,
                'last_used_at': device.last_used_at
            })
        
        return devices
    
    @staticmethod
    def remove_device(user: User, device_id: int) -> Tuple[bool, str]:
        """Remove an MFA device."""
        try:
            device = user.totp_devices.get(id=device_id)
            
            # Check if it's the last verified device
            if device.verified and user.totp_devices.filter(verified=True).count() == 1:
                return False, "Cannot remove the last verified device. Add another device first."
            
            device.delete()
            
            # If no verified devices remain, disable MFA
            if not user.totp_devices.filter(verified=True).exists():
                user.is_mfa_enabled = False
                user.is_mfa_verified = False
                user.save()
            
            return True, "Device removed successfully."
        except TOTPDevice.DoesNotExist:
            return False, "Device not found."
    
    @staticmethod
    def generate_recovery_key(user: User) -> str:
        """Generate a recovery key for account recovery."""
        # Generate a secure random key
        recovery_key = secrets.token_urlsafe(32)
        
        # Store hashed version (implement storage as needed)
        # This is a placeholder - you might want to create a RecoveryKey model
        
        return recovery_key


class SecurityService:
    """Service class for security-related operations."""
    
    @staticmethod
    def check_password_strength(password: str) -> Dict[str, any]:
        """Check password strength and return feedback."""
        feedback = {
            'score': 0,
            'feedback': [],
            'is_strong': False
        }
        
        # Length check
        if len(password) >= 8:
            feedback['score'] += 1
        else:
            feedback['feedback'].append('Password should be at least 8 characters long.')
        
        if len(password) >= 12:
            feedback['score'] += 1
        
        # Complexity checks
        if any(c.isupper() for c in password):
            feedback['score'] += 1
        else:
            feedback['feedback'].append('Include at least one uppercase letter.')
        
        if any(c.islower() for c in password):
            feedback['score'] += 1
        else:
            feedback['feedback'].append('Include at least one lowercase letter.')
        
        if any(c.isdigit() for c in password):
            feedback['score'] += 1
        else:
            feedback['feedback'].append('Include at least one number.')
        
        if any(c in string.punctuation for c in password):
            feedback['score'] += 1
        else:
            feedback['feedback'].append('Include at least one special character.')
        
        # Overall assessment
        feedback['is_strong'] = feedback['score'] >= 4
        
        return feedback
    
    @staticmethod
    def get_location_from_ip(ip_address: str) -> Optional[str]:
        """Get approximate location from IP address."""
        # This is a placeholder - integrate with a GeoIP service
        # Examples: MaxMind GeoIP2, ipapi.co, etc.
        return None
    
    @staticmethod
    def detect_suspicious_activity(user: User, request) -> bool:
        """Detect suspicious login activity."""
        # Get recent login history
        recent_logins = LoginHistory.objects.filter(
            user=user,
            login_time__gte=timezone.now() - timedelta(hours=24)
        )
        
        # Check for multiple failed attempts
        failed_attempts = recent_logins.filter(success=False).count()
        if failed_attempts >= 5:
            return True
        
        # Check for logins from different IPs in short time
        ip_addresses = recent_logins.values_list('ip_address', flat=True).distinct()
        if len(ip_addresses) > 3:
            return True
        
        # Add more sophisticated checks as needed
        
        return False
    
# Add missing FRONTEND_URL setting
@classmethod
def get_frontend_url(cls) -> str:
    """Get frontend URL from settings."""
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

def check_password_strength(self, password: str) -> Dict[str, any]:
    """Check password strength and return feedback."""
    feedback = {
        'score': 0,
        'feedback': [],
        'is_strong': False
    }
    
    # Length check
    if len(password) >= 8:
        feedback['score'] += 1
    else:
        feedback['feedback'].append('Password should be at least 8 characters long.')
    
    if len(password) >= 12:
        feedback['score'] += 1
    
    # Complexity checks
    if any(c.isupper() for c in password):
        feedback['score'] += 1
    else:
        feedback['feedback'].append('Include at least one uppercase letter.')
    
    if any(c.islower() for c in password):
        feedback['score'] += 1
    else:
        feedback['feedback'].append('Include at least one lowercase letter.')
    
    if any(c.isdigit() for c in password):
        feedback['score'] += 1
    else:
        feedback['feedback'].append('Include at least one number.')
    
    if any(c in string.punctuation for c in password):
        feedback['score'] += 1
    else:
        feedback['feedback'].append('Include at least one special character.')
    
    # Overall assessment
    feedback['is_strong'] = feedback['score'] >= 4
    
    return feedback
    
    @staticmethod
    def get_location_from_ip(ip_address: str) -> Optional[str]:
        """Get approximate location from IP address."""
        # This is a placeholder - integrate with a GeoIP service
        # Examples: MaxMind GeoIP2, ipapi.co, etc.
        return None
    
    @staticmethod
    def detect_suspicious_activity(user: User, request) -> bool:
        """Detect suspicious login activity."""
        # Get recent login history
        recent_logins = LoginHistory.objects.filter(
            user=user,
            login_time__gte=timezone.now() - timedelta(hours=24)
        )
        
        # Check for multiple failed attempts
        failed_attempts = recent_logins.filter(success=False).count()
        if failed_attempts >= 5:
            return True
        
        # Check for logins from different IPs in short time
        ip_addresses = recent_logins.values_list('ip_address', flat=True).distinct()
        if len(ip_addresses) > 3:
            return True
        
        # Add more sophisticated checks as needed
        
        return False