from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, AccountantClientRelationshipViewSet,
    RoleViewSet, LoginView, CustomTokenRefreshView ,UserViewSet, ClientProfileUpdateView, AccountantClientRelationshipViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'relationships', AccountantClientRelationshipViewSet, basename='relationship')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'relationclientsaccountants', AccountantClientRelationshipViewSet, basename='relationclientsaccountants')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),

    path('profile/update', ClientProfileUpdateView.as_view(), name='profile'),
]
