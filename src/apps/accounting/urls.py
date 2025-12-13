"""
URL patterns for Accounting Export API
"""

from django.urls import path
from .views import AccountingExportView, AccountMappingView, DashboardStatsView

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

    # Dashboard endpoint
    path(
        'dashboard/stats/',
        DashboardStatsView.as_view(),
        name='dashboard-stats'
    ),
]

