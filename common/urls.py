"""
URL configuration for the common app.
"""

from django.urls import path
from .views import api_info, get_client_ip_view, RateLimitTestView

app_name = 'common'

urlpatterns = [
    path('info/', api_info, name='api_info'),
    path('client-ip/', get_client_ip_view, name='client_ip'),
    path('rate-limit-test/', RateLimitTestView.as_view(), name='rate_limit_test'),
]
