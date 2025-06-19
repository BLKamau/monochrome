"""
Serializers for the users app.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction
import pyotp
import qrcode
import io
import base64

from .models import User, UserType, TOTPDevice, BackupCode, LoginHistory


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    user_type = serializers.ChoiceField(
        choices=UserType.choices,
        default=UserType.USER
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'user_type', 'first_name', 'last_name'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        """Validate the registration data."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _("Password fields didn't match.")
            })
        
        # Remove password_confirm as it's not needed for user creation
        attrs.pop('password_confirm')
        return attrs

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                _("A user with this email already exists.")
            )
        return value.lower()

    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                _("A user with this username already exists.")
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create a new user with the validated data."""
        # Extract password
        password = validated_data.pop('password')
        
        # Create user
        user = User.objects.create_user(
            password=password,
            is_active=False,  # Inactive until email is verified
            **validated_data
        )
        
        # Send verification email through service
        from .services import UserService
        UserService.send_verification_email(user)
        
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""
    
    is_email_verified = serializers.SerializerMethodField()
    requires_mfa_setup = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'is_active', 'is_email_verified',
            'is_mfa_enabled', 'is_mfa_verified', 'requires_mfa_setup',
            'created_at', 'updated_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'is_active', 'is_email_verified', 'is_mfa_enabled',
            'is_mfa_verified', 'created_at', 'updated_at', 'last_login'
        ]

    def get_is_email_verified(self, obj):
        """Check if user's email is verified."""
        return obj.is_active and obj.email

    def get_requires_mfa_setup(self, obj):
        """Check if user needs to set up MFA."""
        return obj.is_active and not obj.is_mfa_enabled


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional claims."""
    
    def validate(self, attrs):
        """Validate credentials and add custom claims."""
        # Get username and password
        username = attrs.get('username')
        password = attrs.get('password')
        
        # Authenticate user
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError({
                'detail': _('Invalid credentials.')
            })
        
        # Check if account is locked
        if user.is_account_locked:
            raise serializers.ValidationError({
                'detail': _('Account is locked due to multiple failed attempts. Please try again later.')
            })
        
        # Check if email is verified
        if not user.is_active:
            raise serializers.ValidationError({
                'detail': _('Please verify your email before logging in.')
            })
        
        # Check if MFA is required but not set up
        if not user.is_mfa_enabled:
            raise serializers.ValidationError({
                'detail': _('MFA setup required. Please complete MFA setup first.'),
                'requires_mfa_setup': True,
                'user_id': user.id
            })
        
        # Reset failed login attempts
        user.reset_failed_login_attempts()
        
        # Get tokens
        refresh = self.get_token(user)
        
        # Add custom claims
        refresh['user_type'] = user.user_type
        refresh['is_mfa_verified'] = user.is_mfa_verified
        refresh['email'] = user.email
        
        # Update last login IP
        request = self.context.get('request')
        if request:
            user.update_last_login_ip(self.get_client_ip(request))
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MFASetupSerializer(serializers.Serializer):
    """Serializer for MFA setup."""
    
    device_name = serializers.CharField(
        max_length=64,
        default='Default Device'
    )
    
    def create(self, validated_data):
        """Create MFA setup for user."""
        user = self.context['request'].user
        device_name = validated_data.get('device_name', 'Default Device')
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Create TOTP device
        device = TOTPDevice.objects.create(
            user=user,
            name=device_name,
            key=secret,
            verified=False
        )
        
        # Generate QR code
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name='Monochrome'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_image = base64.b64encode(buffer.getvalue()).decode()
        
        # Generate backup codes
        from .services import MFAService
        backup_codes = MFAService.generate_backup_codes(user)
        
        return {
            'device_id': device.id,
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_code_image}',
            'backup_codes': backup_codes
        }


class MFAVerifySerializer(serializers.Serializer):
    """Serializer for MFA verification."""
    
    device_id = serializers.IntegerField()
    token = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        """Validate MFA token."""
        user = self.context['request'].user
        device_id = attrs['device_id']
        token = attrs['token']
        
        try:
            device = TOTPDevice.objects.get(id=device_id, user=user)
        except TOTPDevice.DoesNotExist:
            raise serializers.ValidationError({
                'device_id': _('Invalid device ID.')
            })
        
        # Verify token
        totp = pyotp.TOTP(device.decrypt_key())
        if not totp.verify(token, valid_window=1):
            raise serializers.ValidationError({
                'token': _('Invalid token.')
            })
        
        attrs['device'] = device
        return attrs
    
    def create(self, validated_data):
        """Mark device as verified and enable MFA."""
        device = validated_data['device']
        user = device.user
        
        # Mark device as verified
        device.verified = True
        device.save()
        
        # Enable MFA for user
        user.is_mfa_enabled = True
        user.is_mfa_verified = True
        user.save()
        
        return {'success': True, 'message': 'MFA successfully enabled.'}


class MFALoginSerializer(serializers.Serializer):
    """Serializer for MFA login verification."""
    
    user_id = serializers.IntegerField()
    token = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        """Validate MFA token for login."""
        user_id = attrs['user_id']
        token = attrs['token']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': _('Invalid user ID.')
            })
        
        # Check if it's a backup code
        from .services import MFAService
        if len(token) > 6:
            if not MFAService.verify_backup_code(user, token):
                raise serializers.ValidationError({
                    'token': _('Invalid backup code.')
                })
        else:
            # Verify TOTP token
            if not MFAService.verify_totp_token(user, token):
                raise serializers.ValidationError({
                    'token': _('Invalid token.')
                })
        
        attrs['user'] = user
        return attrs
    
    def create(self, validated_data):
        """Complete MFA login."""
        user = validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        refresh['user_type'] = user.user_type
        refresh['is_mfa_verified'] = True
        refresh['email'] = user.email
        
        # Log successful login
        request = self.context.get('request')
        if request:
            LoginHistory.objects.create(
                user=user,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""
    
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate password change data."""
        user = self.context['request'].user
        
        # Check old password
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({
                'old_password': _('Invalid password.')
            })
        
        # Check new passwords match
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _("Password fields didn't match.")
            })
        
        # Check new password is different from old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': _('New password must be different from the old password.')
            })
        
        return attrs
    
    def create(self, validated_data):
        """Change user password."""
        user = self.context['request'].user
        user.set_password(validated_data['new_password'])
        user.save()
        
        return {'success': True, 'message': 'Password changed successfully.'}


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate email exists."""
        try:
            User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            pass
        return value.lower()
    
    def create(self, validated_data):
        """Send password reset email."""
        email = validated_data['email']
        
        try:
            user = User.objects.get(email__iexact=email)
            from .services import UserService
            UserService.send_password_reset_email(user)
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            pass
        
        return {
            'success': True,
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }


class LoginHistorySerializer(serializers.ModelSerializer):
    """Serializer for login history."""
    
    class Meta:
        model = LoginHistory
        fields = [
            'id', 'ip_address', 'user_agent', 'login_time',
            'success', 'failure_reason', 'location'
        ]
        read_only_fields = fields