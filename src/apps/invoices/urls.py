from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    SupplierViewSet,
    CustomerViewSet,
    CategoryViewSet,
    PaymentMethodViewSet,
    ProjectViewSet,
    InvoiceViewSet,
    InvoiceLineItemViewSet,
    InvoiceAttachmentViewSet,
    ArticleViewSet,
    TimeEntryViewSet
)

# Create a router for the primary resources
router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'time-entries', TimeEntryViewSet, basename='time-entry')

# Create nested routers for the related resources
invoices_router = routers.NestedSimpleRouter(router, r'invoices', lookup='invoice')
invoices_router.register(r'line-items', InvoiceLineItemViewSet, basename='invoice-line-item')
invoices_router.register(r'attachments', InvoiceAttachmentViewSet, basename='invoice-attachment')

# Combine the URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('', include(invoices_router.urls)),
]