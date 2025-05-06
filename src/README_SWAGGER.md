# Fixing Swagger Serialization Issues

## Issue: SerializerMetaclass Not JSON Serializable

If you encounter the error:

```
TypeError: Object of type SerializerMetaclass is not JSON serializable
```

This occurs when using a serializer class directly in Swagger schema definitions. To fix this, we've implemented two solutions:

## Solution 1: Custom JSON Encoder (Already Applied)

We've added a custom JSON encoder in `core/utils.py` that can handle `SerializerMetaclass` objects.

This encoder automatically converts `SerializerMetaclass` objects to their string representation, resolving the serialization issue. This solution is loaded via the import in `core/__init__.py`.

## Solution 2: Proper Way to Use Serializers in Swagger

The better approach is to use the proper schema definition for serializers in Swagger. We've provided utility functions in `core/swagger_utils.py` to help with this:

```python
from core.swagger_utils import get_serializer_schema
from drf_yasg.utils import swagger_auto_schema

@swagger_auto_schema(
    responses={
        200: get_serializer_schema(MySerializer)  # <-- Use this instead of MySerializer directly
    }
)
def my_view(request):
    # Your view code
    pass
```

## Common Patterns to Fix

### Views with Direct Serializer References

**Incorrect:**

```python
@swagger_auto_schema(
    responses={
        200: UserSerializer
    }
)
```

**Correct:**

```python
from core.swagger_utils import get_serializer_schema

@swagger_auto_schema(
    responses={
        200: get_serializer_schema(UserSerializer)
    }
)
```

### Schema Generation with Serializer References

**Incorrect:**

```python
schema_view = get_schema_view(
   # ... other settings
   responses={
       200: MySerializer
   }
)
```

**Correct:**

```python
from core.swagger_utils import get_serializer_schema

schema_view = get_schema_view(
   # ... other settings
   responses={
       200: get_serializer_schema(MySerializer)
   }
)
```

## Best Practices

1. Always use `get_serializer_schema()` instead of passing serializer classes directly
2. For nested serializers, the function will automatically handle the nesting
3. For complex response structures, use explicit `openapi.Schema` definitions
4. Test Swagger docs after making API changes
