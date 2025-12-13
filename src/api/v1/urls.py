from django.urls import path, include

urlpatterns = [
    # Include all app-specific URLs
    path('users/', include('apps.users.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('accountants/', include('apps.accountants.urls')),
    path('connections/', include('apps.connections.urls')),
    path('integrations/', include('apps.integrations.urls')),
    path('financials/', include('apps.financials.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('invoices/', include('apps.invoices.urls')),
    path('bank-statements/', include('apps.bank_statements.urls')),
    path('accounting/', include('apps.accounting.urls')),
]
