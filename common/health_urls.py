"""
Health check URLs for the common app.
"""

from django.urls import path
from .views import HealthCheckView

urlpatterns = [
    path('', HealthCheckView.as_view(), name='health_check'),
    path('status/', HealthCheckView.as_view(), name='health_status'),
]