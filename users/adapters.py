"""
Custom adapters for django-allauth integration.
"""

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.urls import reverse


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter to integrate with our authentication system.
    """
    
    def is_open_for_signup(self, request):
        """
        Check whether site is open for signup.
        """
        return getattr(settings, 'ACCOUNT_ALLOW_REGISTRATION', True)
    
    def get_login_redirect_url(self, request):
        """
        Returns the default URL to redirect to after logging in.
        """
        path = "/dashboard/"  # Default redirect
        
        # Check if user needs MFA setup
        if request.user.is_authenticated:
            if not request.user.is_mfa_enabled:
                path = reverse('users:mfa_setup')
        
        return path
    
    def get_logout_redirect_url(self, request):
        """
        Returns the URL to redirect to after logging out.
        """
        return "/"
    
    def get_email_confirmation_redirect_url(self, request):
        """
        Return the URL to redirect to after email confirmation.
        """
        return reverse('users:login')
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Send confirmation email with our custom template.
        """
        # Use our custom email service instead
        from users.services import UserService
        UserService.send_verification_email(emailconfirmation.email_address.user)
    
    def respond_user_inactive(self, request, user):
        """
        Respond when user account is inactive.
        """
        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'message': 'Your account is inactive. Please verify your email first.',
            'code': 'inactive_account'
        }, status=403)
    
    def respond_email_verification_sent(self, request, user):
        """
        Respond after sending verification email.
        """
        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'message': 'Verification email sent. Please check your inbox.',
            'data': {'email': user.email}
        }, status=200)