# BaseDocument Guide

## Overview

`BaseDocument` is a clean, abstract base class that replaces the complex `BaseModelMixin`. It provides:

- **Lifecycle Hooks**: `pre_save()` and `post_save()` for custom logic
- **Automatic Translation**: Google Translate integration for multi-language support
- **Automatic Encryption**: DBEncryptionService integration for sensitive fields
- **Flexible Formatting**: `format()` method with multiple output types
- **Tree Support**: Built-in support for hierarchical data with depth, limit, and pagination
- **Easy to Override**: All methods can be customized in subclasses

## Key Features

### 1. Lifecycle Hooks

#### `pre_save(**kwargs)`
Called **before** saving the document. Use for:
- Validation
- Field transformation
- Encryption
- Auto-generation of fields

```python
async def pre_save(self, **kwargs) -> None:
    await super().pre_save(**kwargs)  # Updates timestamps
    
    # Your custom logic
    if not self.flag:
        self.flag = self._generate_flag()
```

#### `post_save(**kwargs)`
Called **after** saving the document. Use for:
- Logging
- Notifications
- Cache updates
- Triggering other operations

```python
async def post_save(self, **kwargs) -> None:
    await super().post_save(**kwargs)
    
    # Your custom logic
    await self._send_notification()
    await self._update_cache()
```

### 2. Formatting Method

#### `format()` - Main Formatting Method

```python
async def format(
    self,
    output_data_type: OutputDataType = OutputDataType.DEFAULT,
    formatting_flag: EGlobalFormatingFlag = EGlobalFormatingFlag.DEFAULT,
    accept_language: str = DEFAULT_LANGUAGE,
    depth: Optional[int] = None,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    **kwargs
) -> Any:
```

**Parameters:**
- `output_data_type`: Type of output (DEFAULT, TREE, DATA_TABLE, INPUT_SELECT, CASCADE)
- `formatting_flag`: Style of formatting (DEFAULT, FULL_FORMATING_DATA, RESUME_FORMATING_DATA)
- `accept_language`: Language code for translations
- `depth`: Tree depth (used when output_data_type is TREE)
- `limit`: Items per page (for pagination)
- `page`: Page number (for pagination)

**Default Behavior:**
Returns `self` (the document instance itself)

**Override Example:**
```python
async def format(self, output_data_type=OutputDataType.DEFAULT, **kwargs):
    if output_data_type == OutputDataType.INPUT_SELECT:
        return {"id": str(self.id), "display_value": self.name}
    
    elif output_data_type == OutputDataType.DATA_TABLE:
        return await self.format_for_data_table(**kwargs)
    
    # Default: return self
    return self
```

### 3. Specialized Formatting Methods

#### `format_for_tree(depth, limit, page, accept_language)`
For hierarchical/tree data structures.

```python
async def format_for_tree(self, depth=1, **kwargs):
    return {
        "id": str(self.id),
        "data": {"name": self.name},
        "children": await self._get_children(depth - 1) if depth > 0 else []
    }
```

#### `format_for_data_table(accept_language)`
For table display.

```python
async def format_for_data_table(self, **kwargs):
    return {
        "id": str(self.id),
        "name": self.name,
        "created_at": self.created_at.isoformat()
    }
```

#### `format_for_input_select(accept_language)`
For dropdown/select inputs.

```python
async def format_for_input_select(self, **kwargs):
    return {
        "id": str(self.id),
        "display_value": self.name
    }
```

#### `format_for_cascade(accept_language)`
For cascading selects.

```python
async def format_for_cascade(self, **kwargs):
    return {
        "id": str(self.id),
        "display_value": self.name,
        "parent_id": str(self.parent_id) if self.parent_id else None
    }
```

## Usage Examples

### Basic Usage

```python
from app.modules.core.utils.model.base_document import BaseDocument

class MyModel(BaseDocument):
    name: str
    description: str
    
    class Settings:
        name = "my_collection"
```

### With Lifecycle Hooks

```python
class MyModel(BaseDocument):
    name: str
    slug: str = None
    
    async def pre_save(self, **kwargs):
        await super().pre_save(**kwargs)
        
        # Auto-generate slug from name
        if not self.slug:
            self.slug = self.name.lower().replace(" ", "-")
    
    async def post_save(self, **kwargs):
        await super().post_save(**kwargs)
        
        # Log the operation
        print(f"Saved: {self.name}")
```

### With Custom Formatting

```python
class MyModel(BaseDocument):
    name: str
    details: Dict
    
    async def format(self, output_data_type=OutputDataType.DEFAULT, 
                    formatting_flag=EGlobalFormatingFlag.DEFAULT, **kwargs):
        
        if formatting_flag == EGlobalFormatingFlag.FULL_FORMATING_DATA:
            return {
                "id": str(self.id),
                "name": self.name,
                "details": self.details,
                "created_at": self.created_at.isoformat()
            }
        
        elif formatting_flag == EGlobalFormatingFlag.RESUME_FORMATING_DATA:
            return {
                "id": str(self.id),
                "name": self.name
            }
        
        # Default: return self
        return self
```

### Saving Documents

Always use `save_with_hooks()` instead of `save()` to ensure lifecycle hooks are called:

```python
# Create a new document
doc = MyModel(name="Test")

# Save with hooks
await doc.save_with_hooks()

# Or with context data
await doc.save_with_hooks(user_id="123", action="create")
```

### Formatting Lists

Use the class method `format_list()` to format multiple documents:

```python
# Fetch documents
documents = await MyModel.find_all().to_list()

# Format all documents
formatted = await MyModel.format_list(
    documents=documents,
    output_data_type=OutputDataType.DATA_TABLE,
    accept_language="en"
)
```

## Migration from BaseModelMixin

### Before (BaseModelMixin)

```python
from app.modules.core.utils.model.base_model_mixin import BaseModelMixin

class MyModel(BaseModelMixin):
    name: str

    # Complex logic mixed with BaseModelMixin
    async def formatted_properties(self, accept_language="en"):
        # Lots of complex code...
        pass
```

### After (BaseDocument)

```python
from app.modules.core.utils.model.base_document import BaseDocument

class MyModel(BaseDocument):
    name: str

    # Clean, simple formatting
    async def format(self, output_data_type=OutputDataType.DEFAULT, **kwargs):
        if output_data_type == OutputDataType.INPUT_SELECT:
            return {"id": str(self.id), "display_value": self.name}
        return self

    # Lifecycle hooks for custom logic
    async def pre_save(self, **kwargs):
        await super().pre_save(**kwargs)
        # Your logic here
```

## Benefits

1. **Simplicity**: Clean, focused methods instead of complex mixins
2. **Flexibility**: Easy to override and customize
3. **Maintainability**: Clear separation of concerns
4. **Testability**: Easier to test individual methods
5. **Performance**: No unnecessary processing by default
6. **Type Safety**: Better IDE support and type hints

## Best Practices

1. **Always call `super()` in lifecycle hooks** to maintain base functionality
2. **Use `save_with_hooks()`** instead of `save()` to ensure hooks are called
3. **Keep formatting logic simple** - delegate complex logic to helper methods
4. **Return `self` by default** in the `format()` method
5. **Use type hints** for better IDE support
6. **Document custom formatting** in docstrings
7. **Test lifecycle hooks** separately from formatting logic

## See Also

- `sys_person_type_model_new.py` - Complete example implementation
- `base_document.py` - Source code with full documentation
- `OutputDataType` enum - Available output types
- `EGlobalFormatingFlag` enum - Available formatting flags
