# Encryption Services

This directory contains encryption services for the application.

## Overview

The application provides two separate encryption services:

1. **EncryptionService**: General-purpose encryption for various application data
2. **DBEncryptionService**: Dedicated encryption for database fields

Using separate encryption services with different keys provides better security by isolating different types of encrypted data.

## EncryptionService

The `EncryptionService` is used for general-purpose encryption throughout the application. It uses the `ENCRYPTION_KEY` and `ENCRYPTION_SECRET_KEY` environment variables.

### Features

- Version-based encryption for key rotation
- Support for decrypting data encrypted with previous key versions
- Methods for encrypting/decrypting text, data with embedded dates, etc.

### Usage

```python
from app.modules.core.services.encryption.encryption_service import EncryptionService

# Initialize the service
encryption_service = EncryptionService()

# Encrypt text
encrypted = EncryptionService.encrypt_text("sensitive data")

# Decrypt text
decrypted = EncryptionService.decrypt_text(encrypted)
```

## DBEncryptionService

The `DBEncryptionService` is specifically designed for encrypting database fields. It uses the `ENCRYPTION_DB_SECRET_KEY` environment variable, which is separate from the general encryption keys.

### Features

- Dedicated encryption for database fields
- Consistent versioning with "db_enc:" prefix
- Clear error handling for controllers
- Methods to check if data is encrypted

### Usage

```python
from app.modules.core.services.encryption.db_encryption_service import DBEncryptionService

# Initialize the service
db_encryption = DBEncryptionService()

# Encrypt data
encrypted = db_encryption.encrypt("sensitive data")

# Decrypt data
decrypted = db_encryption.decrypt(encrypted)

# Check if data is encrypted
is_encrypted = db_encryption.is_encrypted(data)
```

## Key Management

Both encryption services use Fernet symmetric encryption, which requires a 32-byte key encoded in base64. The application manages these keys in several ways:

1. **Environment Variables**: Keys can be set in the `.env` files
2. **Secure Keys Directory**: Keys are stored in the `app/keys` directory
3. **Key Generation**: Scripts are provided to generate new keys

### Generating New Keys

To generate a new database encryption key:

```bash
python scripts/generate_db_encryption_key.py [environment]
```

This will:
1. Generate a new Fernet key
2. Update the `.env.[environment]` file
3. Create a migration script to re-encrypt existing data

## Best Practices

1. **Use the Right Service**: Use `DBEncryptionService` for database fields and `EncryptionService` for other purposes
2. **Handle Errors**: Always handle encryption/decryption errors gracefully
3. **Search Considerations**: Encrypted fields cannot be searched directly in MongoDB
4. **Key Rotation**: Regularly rotate encryption keys using the provided scripts
5. **Secure Storage**: Ensure encryption keys are stored securely and not exposed in logs or code

## Example

See `app/examples/db_encryption_example.py` for a complete example of using the `DBEncryptionService`.
