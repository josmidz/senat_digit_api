# EXPENSE CHAIN API - Multilingual Data Management System

## Overview

Dominog API is a FastAPI-based backend system that provides robust multilingual data management capabilities. The system is designed to handle data in multiple languages while maintaining French as the primary language in the database.

## Key Features

- **Multilingual Support**: Store and retrieve data in multiple languages
- **Automatic Translation**: Seamlessly translate content between languages using Google Translate
- **Language Preference**: Support for user language preferences via `accept_language` parameter
- **Consistent Data Structure**: Maintain a consistent data structure with French as the primary language
- **Flexible Translation Strategies**: Control how translations are updated with multiple strategies
- **Field Encryption**: Secure sensitive data with field-level encryption

## Core Concepts

### Translation Model

The system uses a structured approach to handle translations:

1. **Main Field Storage**:

   - All main fields in documents always store the French version of the content
   - This ensures consistency across the database

2. **Translations Dictionary**:

   - Each document contains a `translations` dictionary
   - The dictionary stores translations for each translatable field
   - Format: `{ "field_name": { "language_code": "translated_value" } }`

3. **Field Translation Metadata**:
   - Fields that can be translated are marked with `may_have_translation: true` in their schema
   - This allows the system to automatically identify which fields need translation

### Translation Update Strategies

The system supports three translation update strategies:

1. **Default**:

   - Updates the main field (French) and the translation for the current language
   - Preserves translations in other languages
   - This is the standard behavior

2. **Preserve**:

   - Only updates the translation for the specified language
   - Leaves the main field unchanged if the language is not French
   - Preserves all other language translations
   - Useful for correcting translations without affecting other languages

3. **Cascade**:
   - Updates the main field (French) and regenerates translations for all languages
   - Overwrites all existing translations with newly generated ones
   - Useful when the meaning of content has significantly changed

### Data Operations

#### Adding Data

When adding data to a collection:

1. If the input language is French:

   - Store the data directly in the main fields
   - Also store it in the translations dictionary under the "fr" key

2. If the input language is not French:
   - Translate the input to French
   - Store the French translation in the main fields
   - Store both the original input and the French translation in the translations dictionary

#### Updating Data

When updating data, the behavior depends on the selected translation strategy:

1. **Default Strategy**:

   - If the update language is French:
     - Update the main fields directly
     - Update the French translation in the translations dictionary
     - Preserve translations in other languages
   - If the update language is not French:
     - Translate the input to French
     - Update the main fields with the French translation
     - Update the translations dictionary for both French and the input language
     - Preserve translations in other languages

2. **Preserve Strategy**:

   - Only update the translation for the specified language
   - Leave the main field unchanged if the language is not French
   - Preserve all other language translations

3. **Cascade Strategy**:
   - Update the main field with the French translation (if input is not French, translate it first)
   - Regenerate translations for all existing language entries in the translations dictionary
   - This ensures all translations are consistent with the updated content

#### Upsert Operations

The upsert operation combines insert and update logic:

1. First checks if the document exists
2. If it exists, applies the update logic with the specified translation strategy
3. If it doesn't exist, applies the insert logic
4. In both cases, handles translations appropriately based on the input language

### Data Encryption

The system supports field-level encryption for sensitive data:

1. **Field Marking**:
   - Fields that contain sensitive data are marked with `can_be_encrypted=True` in their schema
   - This allows the system to automatically identify which fields need encryption

2. **Encryption Process**:
   - When a document is saved or updated, fields marked with `can_be_encrypted=True` are automatically encrypted
   - Encrypted values are prefixed with "ENC:" to indicate they are encrypted
   - The encryption uses Fernet symmetric encryption with a key derived from the application's secret key

3. **Decryption Process**:
   - When retrieving data, fields that start with "ENC:" are automatically decrypted
   - The decryption happens transparently, so applications receive the decrypted values

4. **Migration**:
   - A migration script is provided to convert existing encrypted data to the new format
   - Run `python scripts/migrate_encrypted_fields.py [env]` to migrate data for a specific environment

### Data Retrieval

When retrieving data:

1. The system checks the `accept_language` parameter
2. If the requested language is French, it returns the main field values
3. If the requested language is not French, it looks for translations in the requested language
4. If a translation exists, it returns that; otherwise, it falls back to the French value
5. Any encrypted fields are automatically decrypted before being returned

## API Usage

### Basic Parameters

- `collection_key`: Identifies which collection to operate on
- `accept_language`: Specifies the language for input/output (default: "fr")
- `data`: The data to be added or updated
- `translation_strategy`: Controls how translations are updated (options: "default", "preserve", "cascade")

### Example Operations

#### Adding Data

```python
result = await add_data_to_collection(
    collection_key="products",
    data={"name": "Computer", "description": "A powerful machine"},
    accept_language="en"
)
```

#### Working with Encrypted Fields

To mark a field for encryption, add `can_be_encrypted=True` to the field's metadata:

```python
from app.models.common.field_decorator import translation_meta
from pydantic import Field

class UserModel(BaseModelMixin):
    name: str = Field(
        ...,
        description="User's name",
        json_schema_extra=translation_meta(
            may_have_translation=True,
            to_be_translated_in_front=False,
            data_type={"is_string": True}
        )
    )

    credit_card_number: str = Field(
        ...,
        description="User's credit card number (sensitive)",
        json_schema_extra=translation_meta(
            may_have_translation=False,
            to_be_translated_in_front=False,
            data_type={"is_string": True},
            can_be_encrypted=True  # Mark this field for encryption
        )
    )
```

The system will automatically encrypt and decrypt fields marked with `can_be_encrypted=True`:

```python
# Adding data with sensitive fields
result = await add_data_to_collection(
    collection_key="users",
    data={"name": "John Doe", "credit_card_number": "1234-5678-9012-3456"},
    accept_language="en"
)

# Retrieving data with sensitive fields
user = await fetch_one_from_collection(
    collection_key="users",
    query={"filter__name": "John Doe"},
    accept_language="en"
)
# user.credit_card_number will be automatically decrypted
```

### Encryption Utilities

The system provides scripts for testing and migrating encrypted data:

#### Testing Encryption

```bash
# Test encryption without database operations
python scripts/test_encryption.py

# Test encryption with database operations for a specific environment
python scripts/test_encryption.py development
```

#### Migrating Encrypted Data

```bash
# Show usage instructions
python scripts/migrate_encrypted_fields.py

# Migrate encrypted data for a specific environment
python scripts/migrate_encrypted_fields.py development
```

#### Managing Field Encryption Status

```bash
# Show usage instructions
python scripts/manage_field_encryption.py

# Encrypt a previously unencrypted field
python scripts/manage_field_encryption.py development encrypt users credit_card_number

# Decrypt a previously encrypted field
python scripts/manage_field_encryption.py development decrypt users credit_card_number
```

#### Rotating Encryption Keys

The system supports encryption key rotation for enhanced security:

```bash
# Show what would be updated without making changes
python scripts/rotate_encryption_key.py development v1 --dry-run

# Actually perform the key rotation
python scripts/rotate_encryption_key.py development v1
```

#### Searching Encrypted Fields

The system provides a dedicated search endpoint that handles both encrypted and non-encrypted fields:

```json
// POST /api/v1/search/search
{
  "collection_key": "users",
  "search_criteria": {
    "name": {"$regex": "John"},
    "credit_card_number": "1234"  // This will search in decrypted values
  },
  "skip": 0,
  "limit": 10,
  "sort": {"created_at": -1}
}
```

For more detailed information about the encryption system, including key rotation procedures and searching encrypted fields, see the [Field Encryption Guide](docs/ENCRYPTION.md).

## Database Migrations

The system includes a database migration system to manage schema changes. Migrations are stored in the `scripts/migrations` directory and are tracked in a `migrations` collection in the database.

### Running Migrations

To run all pending migrations:

```bash
# Run migrations for the default environment (dev)
./run_migrations.sh

# Run migrations for a specific environment
./run_migrations.sh prod
./run_migrations.sh local
./run_migrations.sh stage
./run_migrations.sh test
```

### Important Migrations

#### Remove Duplicate ID Fields

MongoDB uses `_id` as the primary key field, but some models had both `_id` and `id` fields, causing conflicts. The migration `001_remove_duplicate_id_field.py` removes the duplicate `id` field from all collections, keeping only the `_id` field.

To run this migration:

```bash
./run_migrations.sh local
```

This migration is important because:
1. It resolves conflicts between `_id` and `id` fields
2. It ensures that only the `_id` field is used as the primary key
3. It prevents issues with the BaseModelMixin class that uses `id` with `alias="_id"`

For more information about the database migration system, see the [Migrations README](MIGRATIONS.README.md).
