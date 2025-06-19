"""
Views for the users app.
"""

from rest_framework import status, generics, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .serializers import (
    UserRegistrationSerializer, UserSerializer,
    CustomTokenObtainPairSerializer, MFASetupSerializer,
    MFAVerifySerializer, MFALoginSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    LoginHistorySerializer
)
from .models import LoginHistory
from .permissions import IsOwner, IsMFAVerified
from common.utils import StandardResponseMixin

User = get_user_model()


class UserRegistrationView(StandardResponseMixin, generics.CreateAPIView):
    """
    User registration endpoint.
    
    Registers a new user with username, email, password, and user_type.
    Sends email verification after successful registration.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return self.success_response(
            data=UserSerializer(user).data,
            message=_("Registration successful. Please check your email to verify your account."),
            status_code=status.HTTP_201_CREATED
        )


class EmailVerificationView(StandardResponseMixin, views.APIView):
    """
    Email verification endpoint.
    
    Verifies user email using the token sent via email.
    Supports both POST (for API) and GET (for email links) methods.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, uidb64=None, token=None):
        """Handle GET request from email link."""
        if not uidb64 or not token:
            return self.error_response(
                message=_("Invalid verification link."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Combine uidb64 and token
        full_token = f"{uidb64}/{token}"
        
        # Verify token
        from .services import UserService
        result = UserService.verify_email_token(full_token)
        
        if result['success']:
            # For GET request, you might want to redirect to a success page
            # or return an HTML response
            return Response(
                f"""
                <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #4CAF50;">Email Verified Successfully!</h1>
                    <p>Your email has been verified. You can now log in to your account.</p>
                    <p>User ID: {result.get('user_id')}</p>
                    <a href="{settings.FRONTEND_URL}/login" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">Go to Login</a>
                </body>
                </html>
                """,
                content_type='text/html'
            )
        else:
            return Response(
                f"""
                <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #f44336;">Verification Failed</h1>
                    <p>{result['message']}</p>
                </body>
                </html>
                """,
                content_type='text/html',
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def post(self, request):
        """Handle POST request from API."""
        token = request.data.get('token')
        
        if not token:
            return self.error_response(
                message=_("Verification token is required."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify token and activate user
        from .services import UserService
        result = UserService.verify_email_token(token)
        
        if result['success']:
            return self.success_response(
                message=result['message'],
                data={'user_id': result.get('user_id')}
            )
        else:
            return self.error_response(
                message=result['message'],
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ResendVerificationEmailView(StandardResponseMixin, views.APIView):
    """
    Resend email verification endpoint.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return self.error_response(
                message=_("Email is required."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email__iexact=email)
            if user.is_active:
                return self.error_response(
                    message=_("Email is already verified."),
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            from .services import UserService
            UserService.send_verification_email(user)
            
            return self.success_response(
                message=_("Verification email sent successfully.")
            )
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            return self.success_response(
                message=_("If an account exists with this email, a verification email has been sent.")
            )


class CustomTokenObtainPairView(StandardResponseMixin, TokenObtainPairView):
    """
    Custom login endpoint with MFA support.
    
    Returns JWT tokens if credentials are valid and MFA is set up.
    """
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            return self.success_response(
                data=serializer.validated_data,
                message=_("Login successful.")
            )
        except Exception as e:
            # Check if MFA setup is required
            if hasattr(e, 'detail') and isinstance(e.detail, dict):
                if e.detail.get('requires_mfa_setup'):
                    return self.error_response(
                        message=str(e.detail.get('detail')),
                        errors={'requires_mfa_setup': True, 'user_id': e.detail.get('user_id')},
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            
            # Log failed login attempt
            username = request.data.get('username')
            if username:
                try:
                    user = User.objects.get(username=username)
                    user.increment_failed_login_attempts()
                    
                    # Log failed attempt
                    LoginHistory.objects.create(
                        user=user,
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=False,
                        failure_reason=str(e)
                    )
                except User.DoesNotExist:
                    pass
            
            return self.error_response(
                message=_("Invalid credentials."),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MFASetupView(StandardResponseMixin, generics.CreateAPIView):
    """
    MFA setup endpoint.
    
    Generates TOTP secret and QR code for MFA setup.
    """
    serializer_class = MFASetupSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        if request.user.is_mfa_enabled:
            return self.error_response(
                message=_("MFA is already enabled for this account."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return self.success_response(
            data=result,
            message=_("MFA setup initiated. Please scan the QR code with your authenticator app.")
        )


class MFAVerifyView(StandardResponseMixin, generics.CreateAPIView):
    """
    MFA verification endpoint.
    
    Verifies TOTP token and enables MFA for the user.
    """
    serializer_class = MFAVerifySerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        # Generate new tokens with MFA verified
        refresh = RefreshToken.for_user(request.user)
        refresh['user_type'] = request.user.user_type
        refresh['is_mfa_verified'] = True
        refresh['email'] = request.user.email
        
        return self.success_response(
            data={
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(request.user).data
            },
            message=result['message']
        )


class MFALoginView(StandardResponseMixin, generics.CreateAPIView):
    """
    MFA login verification endpoint.
    
    Verifies MFA token for users who have MFA enabled.
    """
    serializer_class = MFALoginSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return self.success_response(
            data=result,
            message=_("MFA verification successful.")
        )


class UserProfileView(StandardResponseMixin, generics.RetrieveUpdateAPIView):
    """
    User profile endpoint.
    
    Retrieves and updates user profile information.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return self.success_response(
            data=serializer.data,
            message=_("Profile updated successfully.")
        )


class ChangePasswordView(StandardResponseMixin, generics.CreateAPIView):
    """
    Change password endpoint.
    
    Allows authenticated users to change their password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated, IsMFAVerified]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        # Invalidate all refresh tokens for the user
        # User needs to login again with new password
        RefreshToken.for_user(request.user).blacklist()
        
        return self.success_response(
            message=result['message']
        )


class PasswordResetRequestView(StandardResponseMixin, generics.CreateAPIView):
    """
    Password reset request endpoint.
    
    Sends password reset email to the user.
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return self.success_response(
            message=result['message']
        )


class PasswordResetConfirmView(StandardResponseMixin, views.APIView):
    """
    Password reset confirmation endpoint.
    
    Resets user password using the token from email.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')
        
        if not all([token, new_password, new_password_confirm]):
            return self.error_response(
                message=_("Token and passwords are required."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != new_password_confirm:
            return self.error_response(
                message=_("Passwords do not match."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        from .services import UserService
        result = UserService.reset_password_with_token(token, new_password)
        
        if result['success']:
            return self.success_response(
                message=result['message']
            )
        else:
            return self.error_response(
                message=result['message'],
                status_code=status.HTTP_400_BAD_REQUEST
            )


class LoginHistoryView(StandardResponseMixin, generics.ListAPIView):
    """
    Login history endpoint.
    
    Returns the login history for the authenticated user.
    """
    serializer_class = LoginHistorySerializer
    permission_classes = [IsAuthenticated, IsMFAVerified]
    
    def get_queryset(self):
        return LoginHistory.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            message=_("Login history retrieved successfully.")
        )


class LogoutView(StandardResponseMixin, views.APIView):
    """
    Logout endpoint.
    
    Blacklists the refresh token to logout the user.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return self.success_response(
                message=_("Logout successful.")
            )
        except Exception as e:
            return self.error_response(
                message=_("Invalid token."),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class DisableMFAView(StandardResponseMixin, views.APIView):
    """
    Disable MFA endpoint.
    
    Allows users to disable MFA (requires current password).
    """
    permission_classes = [IsAuthenticated, IsMFAVerified]
    
    def post(self, request):
        password = request.data.get('password')
        
        if not password:
            return self.error_response(
                message=_("Password is required to disable MFA."),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not request.user.check_password(password):
            return self.error_response(
                message=_("Invalid password."),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        # Disable MFA
        request.user.is_mfa_enabled = False
        request.user.is_mfa_verified = False
        request.user.save()
        
        # Delete all TOTP devices
        request.user.totp_devices.all().delete()
        
        # Delete all backup codes
        request.user.backup_codes.all().delete()
        
        return self.success_response(
            message=_("MFA has been disabled successfully.")
        )


class RegenerateBackupCodesView(StandardResponseMixin, views.APIView):
    """
    Regenerate backup codes endpoint.
    
    Generates new backup codes for MFA recovery.
    """
    permission_classes = [IsAuthenticated, IsMFAVerified]
    
    def post(self, request):
        from .services import MFAService
        
        # Delete old backup codes
        request.user.backup_codes.all().delete()
        
        # Generate new codes
        backup_codes = MFAService.generate_backup_codes(request.user)
        
        return self.success_response(
            data={'backup_codes': backup_codes},
            message=_("New backup codes generated successfully. Please save them securely.")
        )