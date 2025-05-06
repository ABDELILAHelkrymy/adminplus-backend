"""
Utility functions and classes for the core app.
This file contains custom JSON encoders for serialization.
"""
from json import JSONEncoder
from rest_framework.serializers import SerializerMetaclass

# Original JSONEncoder
original_json_default = JSONEncoder.default

# Custom function to handle serialization of SerializerMetaclass objects
def json_encoder_default(self, obj):
    """
    Custom JSON encoder function that handles SerializerMetaclass objects.
    This is needed for Swagger/OpenAPI schema generation.
    """
    # Handle SerializerMetaclass object by returning its name
    if isinstance(obj, SerializerMetaclass):
        return obj.__name__
    
    # Use the default implementation for all other objects
    return original_json_default(self, obj)

# Override the default method
JSONEncoder.default = json_encoder_default 