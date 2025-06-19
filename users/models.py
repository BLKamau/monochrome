"""
User models for the Monochrome authentication system.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import os


class UserType(models.TextChoices):
    """User role choices."""
    ADMIN = 'ADMIN', _('Admin')
    STAFF = 'STAFF', _('Staff')
    USER = 'USER', _('User')


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """
    email = models.EmailField(
        _('email address'),
        unique=True,
        validators=[EmailValidator()],
        error_messages={
            'unique': _("A user with that email already exists."),
        },
    )
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.USER,
        help_text=_("The role/type of the user")
    )
    is_mfa_enabled = models.BooleanField(
        default=False,
        help_text=_("Whether MFA is enabled for this user")
    )
    is_mfa_verified = models.BooleanField(
        default=False,
        help_text=_("Whether the user has verified their MFA setup")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("User's phone number for SMS-based MFA (optional)")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text=_("IP address of last login")
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of consecutive failed login attempts")
    )
    locked_until = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("Account locked until this time due to failed attempts")
    )

    class Meta:
        db_table = 'users'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['user_type']),
        ]

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def is_admin(self):
        """Check if user is an admin."""
        return self.user_type == UserType.ADMIN

    @property
    def is_staff_member(self):
        """Check if user is a staff member."""
        return self.user_type == UserType.STAFF

    @property
    def is_regular_user(self):
        """Check if user is a regular user."""
        return self.user_type == UserType.USER

    @property
    def is_account_locked(self):
        """Check if the account is currently locked."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def increment_failed_login_attempts(self):
        """Increment failed login attempts and lock account if necessary."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Lock account for 30 minutes
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def reset_failed_login_attempts(self):
        """Reset failed login attempts on successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def update_last_login_ip(self, ip_address):
        """Update the last login IP address."""
        self.last_login_ip = ip_address
        self.save(update_fields=['last_login_ip'])


class TOTPDevice(models.Model):
    """
    Model to store TOTP device information for users.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='totp_devices'
    )
    name = models.CharField(
        max_length=64,
        help_text=_("Human-readable name for the device")
    )
    key = models.CharField(
        max_length=80,
        help_text=_("Encrypted TOTP secret key")
    )
    verified = models.BooleanField(
        default=False,
        help_text=_("Whether this device has been verified")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("Last time this device was used for authentication")
    )
    
    class Meta:
        db_table = 'totp_devices'
        verbose_name = _('TOTP Device')
        verbose_name_plural = _('TOTP Devices')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def save(self, *args, **kwargs):
        """Encrypt the key before saving."""
        if self.key and not self.key.startswith('encrypted:'):
            self.key = self.encrypt_key(self.key)
        super().save(*args, **kwargs)

    def encrypt_key(self, key):
        """Encrypt the TOTP key."""
        # Generate a key from Django's SECRET_KEY
        from django.conf import settings
        fernet_key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32)[:32])
        f = Fernet(fernet_key)
        encrypted = f.encrypt(key.encode())
        return f"encrypted:{encrypted.decode()}"

    def decrypt_key(self):
        """Decrypt the TOTP key."""
        if not self.key.startswith('encrypted:'):
            return self.key
        
        from django.conf import settings
        fernet_key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32)[:32])
        f = Fernet(fernet_key)
        encrypted_key = self.key.replace('encrypted:', '')
        return f.decrypt(encrypted_key.encode()).decode()

    def mark_as_used(self):
        """Mark the device as used."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class BackupCode(models.Model):
    """
    Model to store backup codes for MFA.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='backup_codes'
    )
    code = models.CharField(
        max_length=16,
        unique=True,
        help_text=_("Backup code (hashed)")
    )
    used = models.BooleanField(
        default=False,
        help_text=_("Whether this code has been used")
    )
    used_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("When this code was used")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'backup_codes'
        verbose_name = _('Backup Code')
        verbose_name_plural = _('Backup Codes')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {'Used' if self.used else 'Available'}"

    def mark_as_used(self):
        """Mark the backup code as used."""
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])


class LoginHistory(models.Model):
    """
    Model to track user login history for security auditing.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(
        blank=True,
        help_text=_("Browser/client user agent string")
    )
    login_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(
        default=True,
        help_text=_("Whether the login was successful")
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Reason for login failure if applicable")
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Approximate location based on IP (if available)")
    )

    class Meta:
        db_table = 'login_history'
        verbose_name = _('Login History')
        verbose_name_plural = _('Login Histories')
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.user.username} - {status} - {self.login_time}"