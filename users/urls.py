"""
URL configuration for the users app.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    UserRegistrationView,
    EmailVerificationView,
    ResendVerificationEmailView,
    CustomTokenObtainPairView,
    MFASetupView,
    MFAVerifyView,
    MFALoginView,
    UserProfileView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LoginHistoryView,
    LogoutView,
    DisableMFAView,
    RegenerateBackupCodesView,
)

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Email verification endpoints
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path('verify-email/<str:uidb64>/<str:token>/', EmailVerificationView.as_view(), name='verify_email_confirm'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification'),
    
    # MFA endpoints
    path('mfa/setup/', MFASetupView.as_view(), name='mfa_setup'),
    path('mfa/verify/', MFAVerifyView.as_view(), name='mfa_verify'),
    path('mfa/login/', MFALoginView.as_view(), name='mfa_login'),
    path('mfa/disable/', DisableMFAView.as_view(), name='mfa_disable'),
    path('mfa/backup-codes/', RegenerateBackupCodesView.as_view(), name='regenerate_backup_codes'),
    
    # User profile endpoints
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Password reset endpoints
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Security endpoints
    path('login-history/', LoginHistoryView.as_view(), name='login_history'),
]