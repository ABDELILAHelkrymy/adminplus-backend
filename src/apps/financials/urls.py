from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TransactionCategoryViewSet,
    FinancialAccountViewSet,
    TransactionViewSet,
    RecurringTransactionViewSet
)

app_name = 'financials'

router = DefaultRouter()
router.register(r'categories', TransactionCategoryViewSet, basename='transaction-categories')
router.register(r'accounts', FinancialAccountViewSet, basename='financial-accounts')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'recurring', RecurringTransactionViewSet, basename='recurring-transactions')

urlpatterns = [
    path('', include(router.urls)),
] 