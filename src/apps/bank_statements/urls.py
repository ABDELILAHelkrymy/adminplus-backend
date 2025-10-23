from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BankStatementViewSet, BankTransactionViewSet, TransactionCategoryViewSet

router = DefaultRouter()
router.register(r'statements', BankStatementViewSet, basename='bank-statement')
router.register(r'transactions', BankTransactionViewSet, basename='bank-transaction')
router.register(r'categories', TransactionCategoryViewSet, basename='transaction-category')

urlpatterns = [
    path('', include(router.urls)),
]
