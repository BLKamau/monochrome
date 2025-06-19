"""
Forms for the users app.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import UserType

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating new users."""
    
    email = forms.EmailField(
        required=True,
        help_text=_("Required. Enter a valid email address.")
    )
    user_type = forms.ChoiceField(
        choices=UserType.choices,
        initial=UserType.USER,
        help_text=_("Select the user role.")
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'user_type', 'password1', 'password2')
    
    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("This email is already registered."))
        return email.lower()
    
    def save(self, commit=True):
        """Save user with email and set as inactive."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False  # Require email verification
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom form for updating users."""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type')
    
    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get('email')
        if email:
            # Check if email is already taken by another user
            existing = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(_("This email is already registered."))
        return email.lower()


class EmailVerificationForm(forms.Form):
    """Form for email verification."""
    
    token = forms.CharField(
        max_length=200,
        required=True,
        help_text=_("Enter the verification token from your email.")
    )


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset."""
    
    email = forms.EmailField(
        required=True,
        help_text=_("Enter your registered email address.")
    )
    
    def clean_email(self):
        """Normalize email."""
        return self.cleaned_data['email'].lower()


class PasswordResetForm(forms.Form):
    """Form for resetting password."""
    
    token = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.HiddenInput()
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(),
        help_text=_("Enter your new password.")
    )
    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(),
        help_text=_("Enter the same password again.")
    )
    
    def clean(self):
        """Validate passwords match."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError({
                'new_password2': _("The two password fields didn't match.")
            })
        
        return cleaned_data


class MFASetupForm(forms.Form):
    """Form for MFA setup."""
    
    device_name = forms.CharField(
        max_length=64,
        required=False,
        initial="Default Device",
        help_text=_("Name for this authentication device.")
    )


class MFAVerificationForm(forms.Form):
    """Form for MFA verification."""
    
    token = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        help_text=_("Enter the 6-digit code from your authenticator app.")
    )
    
    def clean_token(self):
        """Validate token is numeric."""
        token = self.cleaned_data['token']
        if not token.isdigit():
            raise ValidationError(_("Token must contain only numbers."))
        return token


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile."""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields optional
        for field in self.fields:
            self.fields[field].required = False


class ChangePasswordForm(forms.Form):
    """Form for changing password."""
    
    old_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput(),
        required=True
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(),
        required=True,
        help_text=_("Password must be at least 8 characters long.")
    )
    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(),
        required=True
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        """Validate current password."""
        old_password = self.cleaned_data['old_password']
        if not self.user.check_password(old_password):
            raise ValidationError(_("Your current password was entered incorrectly."))
        return old_password
    
    def clean(self):
        """Validate new passwords match and are different from old."""
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise ValidationError({
                    'new_password2': _("The two password fields didn't match.")
                })
            
            if old_password and new_password1 == old_password:
                raise ValidationError({
                    'new_password1': _("Your new password must be different from your current password.")
                })
        
        return cleaned_data


class DisableMFAForm(forms.Form):
    """Form for disabling MFA."""
    
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(),
        required=True,
        help_text=_("Enter your password to confirm disabling MFA.")
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_password(self):
        """Validate password."""
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise ValidationError(_("Incorrect password."))
        return password