from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .auth import SwaggerAuthView

schema_view = get_schema_view(
   openapi.Info(
      title="Pre-Accounting API",
      default_version='v1',
      description="API for pre-accounting software with user management, invoice processing, and financial reporting",
      terms_of_service="https://www.yourapp.com/terms/",
      contact=openapi.Contact(email="contact@yourapp.com"),
      license=openapi.License(name="Your License"),
      url='https://adminplus-backend-production.up.railway.app', # This is the URL of your deployed
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
   patterns=[path('api/', include('api.urls'))],  # Include only API URLs in the schema
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),

    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # Swagger Auth endpoint
    path('swagger-auth/', SwaggerAuthView.as_view(), name='swagger-auth'),
]
