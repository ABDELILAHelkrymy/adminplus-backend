"""
URL patterns for Accounting Export API
"""

from django.urls import path
from .views import AccountingExportView, AccountMappingView

urlpatterns = [
    # Accounting Export endpoints
    path(
        'export/',
        AccountingExportView.as_view(),
        name='accounting-export'
    ),
    
    # Account mappings endpoint
    path(
        'mappings/',
        AccountMappingView.as_view(),
        name='account-mappings'
    ),
]
