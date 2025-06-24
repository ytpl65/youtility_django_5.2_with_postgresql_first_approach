"""
Health Check URLs for Production Monitoring
"""

from django.urls import path
from .health_checks import (
    health_check,
    readiness_check, 
    liveness_check,
    detailed_health_check
)

urlpatterns = [
    # Basic health check - for load balancers
    path('health/', health_check, name='health_check'),
    
    # Kubernetes/Container orchestration endpoints
    path('ready/', readiness_check, name='readiness_check'),
    path('alive/', liveness_check, name='liveness_check'),
    
    # Detailed health check - for monitoring systems
    path('health/detailed/', detailed_health_check, name='detailed_health_check'),
]