"""
Admin configuration for the users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, TOTPDevice, BackupCode, LoginHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced admin interface for User model."""
    
    list_display = [
        'username', 'email', 'user_type', 'is_active', 
        'is_mfa_enabled', 'created_at', 'last_login'
    ]
    list_filter = [
        'user_type', 'is_active', 'is_mfa_enabled', 
        'is_mfa_verified', 'is_staff', 'is_superuser',
        'created_at'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Additional Info'), {
            'fields': (
                'user_type', 'is_mfa_enabled', 'is_mfa_verified',
                'phone_number', 'last_login_ip', 'failed_login_attempts',
                'locked_until'
            )
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Additional Info'), {
            'fields': ('email', 'user_type', 'phone_number')
        }),
    )
    
    readonly_fields = [
        'created_at', 'updated_at', 'last_login_ip', 
        'failed_login_attempts', 'locked_until'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('totp_devices', 'backup_codes')
    
    actions = ['unlock_accounts', 'reset_mfa', 'send_verification_email']
    
    def unlock_accounts(self, request, queryset):
        """Unlock selected user accounts."""
        count = queryset.update(
            failed_login_attempts=0,
            locked_until=None
        )
        self.message_user(
            request,
            f'{count} account(s) unlocked successfully.'
        )
    unlock_accounts.short_description = "Unlock selected accounts"
    
    def reset_mfa(self, request, queryset):
        """Reset MFA for selected users."""
        count = 0
        for user in queryset:
            user.is_mfa_enabled = False
            user.is_mfa_verified = False
            user.save()
            user.totp_devices.all().delete()
            user.backup_codes.all().delete()
            count += 1
        
        self.message_user(
            request,
            f'MFA reset for {count} user(s).'
        )
    reset_mfa.short_description = "Reset MFA for selected users"
    
    def send_verification_email(self, request, queryset):
        """Send verification email to selected users."""
        from .services import UserService
        count = 0
        for user in queryset.filter(is_active=False):
            UserService.send_verification_email(user)
            count += 1
        
        self.message_user(
            request,
            f'Verification email sent to {count} user(s).'
        )
    send_verification_email.short_description = "Send verification email"


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    """Admin interface for TOTP devices."""
    
    list_display = ['user', 'name', 'verified', 'created_at', 'last_used_at']
    list_filter = ['verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'name']
    readonly_fields = ['key', 'created_at', 'last_used_at']
    
    def get_queryset(self, request):
        """Include user data in queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """Disable adding TOTP devices through admin."""
        return False


@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    """Admin interface for backup codes."""
    
    list_display = ['user', 'code_preview', 'used', 'used_at', 'created_at']
    list_filter = ['used', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['code', 'used', 'used_at', 'created_at']
    
    def code_preview(self, obj):
        """Show partial code for security."""
        return f"{obj.code[:8]}..."
    code_preview.short_description = "Code (partial)"
    
    def get_queryset(self, request):
        """Include user data in queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """Disable adding backup codes through admin."""
        return False


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """Admin interface for login history."""
    
    list_display = [
        'user', 'login_time', 'success', 'ip_address', 
        'location', 'user_agent_preview'
    ]
    list_filter = ['success', 'login_time']
    search_fields = ['user__username', 'user__email', 'ip_address']
    readonly_fields = [
        'user', 'ip_address', 'user_agent', 'login_time',
        'success', 'failure_reason', 'location'
    ]
    date_hierarchy = 'login_time'
    
    def user_agent_preview(self, obj):
        """Show truncated user agent."""
        if obj.user_agent:
            return obj.user_agent[:50] + '...' if len(obj.user_agent) > 50 else obj.user_agent
        return '-'
    user_agent_preview.short_description = "User Agent"
    
    def get_queryset(self, request):
        """Include user data in queryset."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """Disable adding login history through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing login history."""
        return False
    
    actions = ['export_to_csv']
    
    def export_to_csv(self, request, queryset):
        """Export selected login history to CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="login_history.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User', 'Email', 'Login Time', 'Success', 'IP Address',
            'User Agent', 'Location', 'Failure Reason'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.user.username,
                obj.user.email,
                obj.login_time,
                'Yes' if obj.success else 'No',
                obj.ip_address,
                obj.user_agent,
                obj.location or '-',
                obj.failure_reason or '-'
            ])
        
        return response
    export_to_csv.short_description = "Export selected to CSV"


# Customize admin site
admin.site.site_header = "Monochrome Admin"
admin.site.site_title = "Monochrome Admin Portal"
admin.site.index_title = "Welcome to Monochrome Administration"