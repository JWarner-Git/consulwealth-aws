# SQL Migration Scripts for Plaid Integration

This directory contains SQL scripts to update your Supabase database schema to fully support the Plaid integration. These scripts handle creating and updating tables for storing Plaid-connected accounts, institutions, and related data.

## Overview of Scripts

### Diagnostic Scripts

- **`check_schema.sql`**: Use this first to diagnose your current database schema and identify potential issues before running other scripts.

### Core Migrations

Run these scripts in the following order:

1. **`fix_institution_id_constraint.sql`**: Fixes foreign key constraints issues between accounts and institutions tables.
2. **`fix_institution_id_type.sql`**: Converts any UUID institution_id columns to TEXT to match Plaid's format.
3. **`fixed_institutions_table_update.sql`**: Updates the institutions table to use TEXT IDs instead of UUIDs.
4. **`run_this_fixed_accounts_schema.sql`**: Updates the accounts table to support various financial account types.

## Common Errors and Solutions

### Error: unterminated dollar-quoted string at or near "$$"

```
ERROR: 42601: unterminated dollar-quoted string at or near "$$
```

**Cause**: This happens when a DO block isn't properly closed, often due to additional text inserted in the middle of the script.

**Solution**: Use the `run_this_fixed_accounts_schema.sql` script instead, which has been cleaned up to avoid this issue.

### Error: column "institution_id" of relation "institutions_new" does not exist

```
ERROR: 42703: column "institution_id" of relation "institutions_new" does not exist
```

**Cause**: This happens when the script tries to insert data into a column that doesn't exist in the new institutions table.

**Solution**: Use the `fixed_institutions_table_update.sql` script instead, which dynamically determines the columns in your institutions table and properly migrates them.

### Error: key columns "institution_id" and "id" are of incompatible types

```
ERROR: foreign key constraint "accounts_institution_id_fkey" cannot be implemented
DETAIL: Key columns "institution_id" and "id" are of incompatible types: text and uuid.
```

**Cause**: The foreign key constraint expects both columns to be the same type, but they're not.

**Solution**: Run the scripts in the correct order:
1. First run `fix_institution_id_constraint.sql` to drop the problematic constraint
2. Then run `fixed_institutions_table_update.sql` to convert the institutions table
3. Finally run `run_this_fixed_accounts_schema.sql` to update the accounts table

## Step-by-Step Migration Guide

For a clean migration, follow these steps:

1. **Backup your database** before running any scripts (use the Supabase Dashboard)

2. **Run the diagnostic script** to understand your current schema:
   ```sql
   -- First run this to see your current schema
   [contents of check_schema.sql]
   ```

3. **Drop any problematic foreign key constraints**:
   ```sql
   -- Run this first to drop any problematic constraints
   [contents of fix_institution_id_constraint.sql]
   ```

4. **Update the institutions table** (if it exists):
   ```sql
   -- Convert institution IDs from UUID to TEXT
   [contents of fixed_institutions_table_update.sql]
   ```

5. **Update the accounts table schema**:
   ```sql
   -- Add columns for various account types
   [contents of run_this_fixed_accounts_schema.sql]
   ```

If you encounter any issues, please reach out to our support team for assistance. 