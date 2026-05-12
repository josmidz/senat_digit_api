# Database Migrations System

This document explains how to use the database migration system to manage changes to the MongoDB database schema.

## Overview

The migration system allows you to:

1. Create new migration files
2. Run pending migrations
3. List all migrations and their status
4. Rollback migrations if needed

Migrations are tracked in a `migrations` collection in your MongoDB database, ensuring that each migration is applied only once.

## Migration Files

Migration files are stored in the `scripts/migrations` directory and follow the naming convention:

```
NNN_migration_name.py
```

Where:
- `NNN` is a sequential number (e.g., 001, 002, 003)
- `migration_name` is a descriptive name using snake_case

Each migration file must define two async functions:
- `migrate_up()`: Implements the migration
- `migrate_down()`: Implements the rollback logic

## Creating a New Migration

### Manual Migration Creation

To create a new migration file manually, use the `create_migration.sh` script:

```bash
# For all environments
./create_migration.sh add_new_field

# For local development only
./create_migration.local.sh add_new_field
```

This will create a new migration file with the next sequential number in the `scripts/migrations` directory.

### Automatic Migration Generation

You can also automatically detect schema changes and generate migrations using the `create_migration_auto.sh` script:

```bash
# Auto-detect changes in the default environment (dev)
./create_migration_auto.sh

# Auto-detect changes in a specific environment
./create_migration_auto.sh local
./create_migration_auto.sh prod

# Auto-detect with a custom migration name
./create_migration_auto.sh local --name add_custom_fields

# Specify a custom field and collection
./create_migration_auto.sh local --field status --collection users

# Specify a custom field, collection, and name
./create_migration_auto.sh local --field is_active --collection users --name add_active_status

# Only detect changes without creating a migration (dry run)
./create_migration_auto.sh local --dry-run
```

The automatic migration generator:

1. Extracts schema information from your model files
2. Creates a migration file with the specified options
3. Generates a unique name with a timestamp to avoid conflicts
4. Makes the migration file executable
5. Intelligently handles the `id` field with `alias="_id"` in Python models
6. Only creates migrations for fields that are actually missing in documents

The script handles all the necessary steps automatically:

1. Creates the required directories if they don't exist
2. Extracts model schemas
3. Detects missing fields in the database collections
4. Checks if there are documents that would be affected by the migration
5. Skips creating migrations if all fields already exist in all documents
6. Generates the migration file with proper MongoDB queries
7. Makes the file executable

## Running Migrations

### Standard Schema Migrations

To run all pending migrations, use the `run_migrations.sh` script:

```bash
# Run migrations for the default environment (dev)
./run_migrations.sh

# Run migrations for a specific environment
./run_migrations.sh prod
./run_migrations.sh local
./run_migrations.sh stage
./run_migrations.sh test

# List all migrations and their status
./run_migrations.sh local --list

# Rollback a specific migration
./run_migrations.sh local --rollback 001_update_bank_model_20250619161913
```

### Encryption Migrations

For encryption-related migrations, use the `run_encryption_migrations.sh` script:

```bash
# Migrate encrypted fields in local environment
./run_encryption_migrations.sh local fields

# Migrate to database encryption in production (with safety checks)
./run_encryption_migrations.sh prod db

# Migrate to new encryption key in staging
./run_encryption_migrations.sh stage key
```

**⚠️ Important Notes for Encryption Migrations:**
- Always backup your database before running encryption migrations
- Set `NEW_ENCRYPTION_KEY` environment variable for key migration
- Production environments require additional confirmation
- Scripts gracefully handle missing encryption services

## Listing Migrations

There are two ways to list all migrations and their status:

### Using the run_migrations.sh script with --list option

```bash
# List migrations for the default environment (dev)
./run_migrations.sh --list

# List migrations for a specific environment
./run_migrations.sh prod --list
./run_migrations.sh local --list
```

### Using the dedicated list_migrations.sh script

```bash
# List migrations for the default environment (dev)
./list_migrations.sh

# List migrations for a specific environment
./list_migrations.sh prod
./list_migrations.sh local
```

Both methods will show you:
- The name of each migration
- Whether it's been applied or is pending
- When it was applied (if applicable)

## Rolling Back Migrations

To rollback a specific migration, use the `--rollback` option:

```bash
# Rollback a migration for the default environment (dev)
./run_migrations.sh --rollback 001_fix_verified_at_field

# Rollback a migration for a specific environment
./run_migrations.sh prod --rollback 001_fix_verified_at_field
./run_migrations.sh local --rollback 001_fix_verified_at_field
```

## Migration Best Practices

1. **Make migrations idempotent**: Migrations should be safe to run multiple times without causing errors or duplicate data.

2. **Test migrations thoroughly**: Always test migrations in a development or staging environment before applying them to production.

3. **Keep migrations small and focused**: Each migration should do one thing and do it well.

4. **Always implement rollback logic**: The `migrate_down()` function should properly undo the changes made by `migrate_up()`.

5. **Document your migrations**: Add clear comments explaining what the migration does and why.

6. **Handle errors gracefully**: Migrations should check for errors and handle them appropriately.

7. **Use `id` with `alias="_id"` in Python models**: The migration system is designed to handle this pattern correctly and will skip the `id` field when detecting schema changes.

8. **Avoid creating unnecessary migrations**: The system checks if there are documents that would be affected by the migration and only creates migrations if needed.

## Example Migrations

### Example 1: Adding a field with a default value

Here's an example of a migration that adds a new field to a collection:

```python
from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    """
    Migration: Add status field to users

    Description:
    Adds a 'status' field to all documents in the users collection
    that don't already have it, with a default value of 'active'.

    Created: 2025-05-08 12:46:06
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Update users collection
    if "users" in db.list_collection_names():
        result = db["users"].update_many(
            {"status": {"$exists": False}},
            {"$set": {"status": "active"}}
        )
        print(f"Migration complete: {result.modified_count} documents updated")
    else:
        print(f"Collection users not found")

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Rollback users collection
    if "users" in db.list_collection_names():
        result = db["users"].update_many(
            {"status": {"$exists": True}},
            {"$unset": {"status": ""}}
        )
        print(f"Rollback complete: {result.modified_count} documents updated")
    else:
        print(f"Collection users not found")
```

### Example 2: Adding a field with a null default value

```python
from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    """
    Migration: Add paid_at field to ops_expense_operation

    Description:
    Adds a 'paid_at' field to all documents in the ops_expense_operation collection
    that don't already have it, with a default value of None.

    Created: 2025-05-08 11:30:15
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Update ops_expense_operation collection
    if "ops_expense_operation" in db.list_collection_names():
        result = db["ops_expense_operation"].update_many(
            {"paid_at": {"$exists": False}},
            {"$set": {"paid_at": None}}
        )
        print(f"Migration complete: {result.modified_count} documents updated")
    else:
        print(f"Collection ops_expense_operation not found")

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Rollback ops_expense_operation collection
    if "ops_expense_operation" in db.list_collection_names():
        result = db["ops_expense_operation"].update_many(
            {"paid_at": {"$exists": True}},
            {"$unset": {"paid_at": ""}}
        )
        print(f"Rollback complete: {result.modified_count} documents updated")
    else:
        print(f"Collection ops_expense_operation not found")
```

### Example 3: Adding multiple fields to multiple collections

```python
from pymongo import MongoClient
from app.core.config import settings

async def migrate_up():
    """
    Migration: Add fields to collections

    Description:
    Adds fields to collections that don't already have them, with a default value of None.

    Created: 2025-05-08 13:23:37
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Update users collection - Add status field
    if "users" in db.list_collection_names():
        result = db["users"].update_many(
            {"status": {"$exists": False}},
            {"$set": {"status": None}}
        )
        print(f"Migration complete for users.status: {result.modified_count} documents updated")
    else:
        print(f"Collection users not found")

    # Update profiles collection - Add is_active field
    if "profiles" in db.list_collection_names():
        result = db["profiles"].update_many(
            {"is_active": {"$exists": False}},
            {"$set": {"is_active": None}}
        )
        print(f"Migration complete for profiles.is_active: {result.modified_count} documents updated")
    else:
        print(f"Collection profiles not found")

async def migrate_down():
    """
    Rollback the migration
    """
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Rollback users collection - Remove status field
    if "users" in db.list_collection_names():
        result = db["users"].update_many(
            {"status": {"$exists": True}},
            {"$unset": {"status": ""}}
        )
        print(f"Rollback complete for users.status: {result.modified_count} documents updated")
    else:
        print(f"Collection users not found")

    # Rollback profiles collection - Remove is_active field
    if "profiles" in db.list_collection_names():
        result = db["profiles"].update_many(
            {"is_active": {"$exists": True}},
            {"$unset": {"is_active": ""}}
        )
        print(f"Rollback complete for profiles.is_active: {result.modified_count} documents updated")
    else:
        print(f"Collection profiles not found")
```

## Recent Fixes and Improvements (2025-06-19)

### ✅ Migration System Fixes
- **Fixed import paths**: All migration scripts now use correct `app.modules.core.configs.config` imports
- **Fixed collection name detection**: Now properly detects collection names from `Settings.name` in models
- **Fixed sys.path setup**: Proper project root path configuration for all scripts
- **Enhanced error handling**: Graceful fallback when services are unavailable

### ✅ Encryption Migration Fixes
- **Security improvements**: Removed hardcoded encryption keys, now uses environment variables
- **Fixed import paths**: Corrected all import paths in encryption migration files
- **Added safety checks**: Production environment warnings with confirmation prompts
- **Enhanced error handling**: Graceful handling of missing encryption services

### ✅ New Features
- **Unified wrapper scripts**: `run_migrations.sh` and `run_encryption_migrations.sh`
- **Environment variable loading**: Properly loads `.env` files for each environment
- **Virtual environment activation**: Automatically activates Python virtual environment
- **Dynamic model discovery**: Scans all model directories across the entire codebase

## Troubleshooting

If you encounter issues with migrations, check the following:

1. Make sure the MongoDB connection settings are correct in your environment file
2. Ensure the migration file has the correct format with `migrate_up` and `migrate_down` functions
3. Check the logs in `bash/migration/logs/` for detailed error messages
4. Verify that MongoDB queries use the correct syntax:
   - Use `{"$exists": false}` to check if a field doesn't exist
   - Use `{"$set": {"field": value}}` to set a field value
   - Use `{"$unset": {"field": ""}}` to remove a field
5. **Environment setup**: Make sure your `.env.local` (or appropriate env file) exists and contains correct MongoDB settings

### Common Issues

1. **Migrations showing as PENDING after running**:
   - Check the MongoDB queries in the migration file
   - Make sure the database name in `.env.local` matches the one in `run_migrations.sh`
   - Look for error messages in the logs directory: `bash/migration/logs/`

2. **Error: No module named 'pymongo'**:
   - Install the pymongo module: `pip install pymongo`
   - Make sure your virtual environment is activated

3. **Import errors in migration files**:
   - **Fixed in 2025-06-19**: All import paths have been corrected
   - Use `from app.modules.core.configs.config import settings` (not `from app.configs.config`)
   - Scripts now automatically handle sys.path setup

4. **Database connection issues**:
   - Check your `.env.local` file exists and contains correct MongoDB settings
   - Verify `MONGO_URI` and `MONGO_DB_NAME` environment variables
   - Test connection: `python -c "from app.modules.core.configs.config import settings; print(settings.MONGO_URI)"`

5. **No migration created when running create_migration_auto.sh**:
   - This is expected behavior if all fields already exist in all documents
   - The system checks if there are documents that would be affected by the migration
   - If no documents would be affected, no migration is created
   - You can use the `--dry-run` option to see what fields would be included in the migration

6. **ID field not included in migrations**:
   - This is expected behavior as the system is designed to handle the `id` field with `alias="_id"` pattern
   - The `id` field is skipped when detecting schema changes to avoid unnecessary migrations

7. **Encryption migration issues**:
   - **Fixed in 2025-06-19**: All encryption migration scripts have been fixed
   - Set `NEW_ENCRYPTION_KEY` environment variable for key migrations
   - Scripts now gracefully handle missing encryption services
   - Always backup database before running encryption migrations

8. **Collection name detection issues**:
   - **Fixed in 2025-06-19**: Now properly detects collection names from `Settings.name` in models
   - System scans all model directories: `core/models`, `auth/models`, `edocs/models`, etc.

## Migration File Locations

- **Migration files**: `bash/migration/migrations/`
- **Schema snapshots**: `bash/migration/schema_snapshots/`
- **Logs**: `bash/migration/logs/`
- **Scripts**: `bash/migration/` (main directory)

## Environment Files

Make sure you have the appropriate environment file:
- `.env.local` for local development
- `.env.development` for development
- `.env.production` for production
- `.env.staging` for staging
- `.env.testing` for testing
