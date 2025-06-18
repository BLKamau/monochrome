"""
Management command to create test users.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users for development'

    def handle(self, *args, **options):
        # Example implementation
        self.stdout.write(self.style.SUCCESS('Test users creation command'))
