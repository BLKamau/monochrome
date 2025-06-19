"""
App configuration for the users app.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration for the users app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'User Management'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import users.signals
        except ImportError:
            pass