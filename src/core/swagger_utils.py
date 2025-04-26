"""
Utility functions for Swagger/OpenAPI schema generation.
Provides helper functions for proper serializer handling in responses.
"""
from drf_yasg import openapi
from rest_framework import serializers


def get_serializer_schema(serializer_class):
    """
    Convert a serializer class to an OpenAPI Schema object.
    Use this instead of directly using the serializer class in swagger_auto_schema.
    
    Example:
        @swagger_auto_schema(
            responses={
                200: get_serializer_schema(MySerializer)
            }
        )
    
    Args:
        serializer_class: A DRF serializer class
        
    Returns:
        openapi.Schema: A proper schema object for the serializer
    """
    # Create an instance of the serializer
    serializer_instance = serializer_class()
    
    # Get the field information
    properties = {}
    required = []
    
    for field_name, field in serializer_instance.fields.items():
        # Convert the field to OpenAPI type
        field_schema = field_to_schema(field)
        properties[field_name] = field_schema
        
        if field.required:
            required.append(field_name)
    
    # Create and return the schema
    schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties=properties,
        required=required if required else None
    )
    
    return schema


def field_to_schema(field):
    """
    Convert a DRF field to an OpenAPI Schema object.
    
    Args:
        field: A DRF field instance
        
    Returns:
        openapi.Schema: A schema representation of the field
    """
    # Map DRF field types to OpenAPI types
    if isinstance(field, serializers.CharField) or isinstance(field, serializers.EmailField):
        return openapi.Schema(type=openapi.TYPE_STRING)
    elif isinstance(field, serializers.IntegerField):
        return openapi.Schema(type=openapi.TYPE_INTEGER)
    elif isinstance(field, serializers.FloatField) or isinstance(field, serializers.DecimalField):
        return openapi.Schema(type=openapi.TYPE_NUMBER)
    elif isinstance(field, serializers.BooleanField):
        return openapi.Schema(type=openapi.TYPE_BOOLEAN)
    elif isinstance(field, serializers.ListField) or isinstance(field, serializers.ListSerializer):
        child_schema = field_to_schema(field.child) if hasattr(field, 'child') else openapi.Schema(type=openapi.TYPE_STRING)
        return openapi.Schema(type=openapi.TYPE_ARRAY, items=child_schema)
    elif isinstance(field, serializers.DictField):
        return openapi.Schema(type=openapi.TYPE_OBJECT)
    elif isinstance(field, serializers.DateTimeField) or isinstance(field, serializers.DateField):
        return openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
    elif isinstance(field, serializers.JSONField):
        return openapi.Schema(type=openapi.TYPE_OBJECT)
    elif isinstance(field, serializers.SerializerMethodField):
        # For method fields, we make a guess based on the method name
        method_name = f'get_{field.field_name}'
        if hasattr(field.parent, method_name):
            # Return string as default for SerializerMethodField
            return openapi.Schema(type=openapi.TYPE_STRING)
    elif isinstance(field, serializers.ModelSerializer) or isinstance(field, serializers.Serializer):
        # Handle nested serializers
        nested_properties = {}
        for nested_name, nested_field in field.fields.items():
            nested_properties[nested_name] = field_to_schema(nested_field)
        return openapi.Schema(type=openapi.TYPE_OBJECT, properties=nested_properties)
    
    # Default to string for unknown types
    return openapi.Schema(type=openapi.TYPE_STRING) 