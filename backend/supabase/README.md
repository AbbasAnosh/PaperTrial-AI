# Supabase Migrations

This directory contains the Supabase configuration and migration files for the Paper Trail Automator project.

## Migration Files

All migration files are stored in the `migrations` directory with the following naming convention:

```
YYYYMMDDHHMMSS_description.sql
```

For example:

```
20240317_create_execute_sql_function.sql
20240321_create_user_profiles.sql
```

## Running Migrations

There are two ways to run migrations:

### 1. Using the Supabase CLI

```bash
# Make sure you have the Supabase CLI installed
npm install supabase --save-dev

# Set your access token
$env:SUPABASE_ACCESS_TOKEN="your-access-token"

# Link your project
npx supabase link --project-ref jrizrpjpjpqolculmckf

# Push migrations to the remote database
npx supabase db push
```

### 2. Using the Python Migration Script

```bash
# Run the migration script
python app/db/migrate.py
```

## Migration Process

1. Create a new migration file in the `migrations` directory with the current timestamp
2. Write your SQL statements in the migration file
3. Run the migration using one of the methods above

## Troubleshooting

If you encounter issues with migrations:

1. Check that your Supabase credentials are correct in the `.env` file
2. Make sure you have the correct access token set
3. Verify that your project is linked correctly
4. Check the Supabase dashboard for any errors

## Resources

- [Supabase CLI Documentation](https://supabase.com/docs/reference/cli)
- [Supabase Migrations Guide](https://supabase.com/docs/guides/cli/migrations)
- [Supabase Database Schema](https://supabase.com/docs/guides/database/schema)
