"""
Views for the common app.
"""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from rest_framework import views, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .utils import StandardResponseMixin, get_client_info


class HealthCheckView(StandardResponseMixin, views.APIView):
    """
    Health check endpoint for monitoring.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return health status."""
        health_data = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': getattr(settings, 'APP_VERSION', '1.0.0'),
            'services': {
                'database': self.check_database(),
                'cache': self.check_cache(),
                'email': self.check_email(),
            }
        }
        
        # Determine overall health
        all_healthy = all(service['healthy'] for service in health_data['services'].values())
        
        if all_healthy:
            return self.success_response(
                data=health_data,
                message="All systems operational"
            )
        else:
            return self.error_response(
                message="Some services are unhealthy",
                errors=health_data,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    
    def check_database(self):
        """Check database connectivity."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {'healthy': True, 'message': 'Database is accessible'}
        except Exception as e:
            return {'healthy': False, 'message': str(e)}
    
    def check_cache(self):
        """Check cache connectivity."""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 1)
            value = cache.get('health_check')
            cache.delete('health_check')
            
            if value == 'ok':
                return {'healthy': True, 'message': 'Cache is working'}
            else:
                return {'healthy': False, 'message': 'Cache read/write failed'}
        except Exception as e:
            return {'healthy': False, 'message': str(e)}
    
    def check_email(self):
        """Check email configuration."""
        try:
            # Just check if email backend is configured
            if hasattr(settings, 'EMAIL_BACKEND'):
                return {'healthy': True, 'message': 'Email backend configured'}
            else:
                return {'healthy': False, 'message': 'Email backend not configured'}
        except Exception as e:
            return {'healthy': False, 'message': str(e)}


@api_view(['GET'])
@permission_classes([AllowAny])
def api_info(request):
    """Return API information."""
    return Response({
        'name': 'Monochrome Authentication API',
        'version': getattr(settings, 'APP_VERSION', '1.0.0'),
        'description': 'Secure authentication and authorization API',
        'documentation': request.build_absolute_uri('/api/docs/'),
        'endpoints': {
            'auth': request.build_absolute_uri('/api/auth/'),
            'health': request.build_absolute_uri('/api/health/'),
            'docs': request.build_absolute_uri('/api/docs/'),
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_client_ip_view(request):
    """Return client IP address - useful for debugging."""
    client_info = get_client_info(request)
    return Response({
        'ip_address': client_info['ip_address'],
        'user_agent': client_info['user_agent'],
        'debug_mode': settings.DEBUG
    })


# Error handlers
def custom_404(request, exception=None):
    """Custom 404 error handler."""
    return JsonResponse({
        'success': False,
        'message': 'The requested resource was not found',
        'code': 'not_found',
        'status_code': 404
    }, status=404)


def custom_500(request):
    """Custom 500 error handler."""
    return JsonResponse({
        'success': False,
        'message': 'An internal server error occurred',
        'code': 'internal_error',
        'status_code': 500
    }, status=500)


@csrf_exempt
@require_http_methods(['GET'])
def robots_txt(request):
    """Return robots.txt content."""
    lines = [
        "User-agent: *",
        "Disallow: /api/",
        "Disallow: /admin/",
        "Disallow: /static/",
        "Disallow: /media/",
    ]
    return JsonResponse("\n".join(lines), safe=False, content_type="text/plain")


class RateLimitTestView(StandardResponseMixin, views.APIView):
    """
    Test endpoint for rate limiting.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Test rate limiting."""
        return self.success_response(
            message="Rate limit test successful",
            data={
                'timestamp': timezone.now().isoformat(),
                'client_ip': get_client_info(request)['ip_address']
            }
        )