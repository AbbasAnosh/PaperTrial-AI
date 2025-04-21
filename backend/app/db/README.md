# Database Migrations

This directory contains the database migrations for the Paper Trail Automator AI application.

## Migration Files

The migrations are organized in the following order:

1. `20240318_create_common_functions.sql` - Creates common functions used by all tables
2. `20240319_create_users_table.sql` - Creates the users table
3. `20240319_create_workspaces_table.sql` - Creates the workspaces and workspace_members tables
4. `20240320_create_ml_tables.sql` - Creates the ML models, training data, and evaluations tables
5. `20240320_create_ml_monitoring_tables.sql` - Creates the ML monitoring tables

## Running Migrations

To run the migrations, you need to have PostgreSQL installed and running. Then, follow these steps:

1. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Set the following environment variables (or they will use the defaults):

   ```
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=postgres
   export DB_USER=postgres
   export DB_PASSWORD=postgres
   ```

3. Run the migrations:
   ```
   python run_migrations.py
   ```

## Troubleshooting

If you encounter any errors, check the following:

1. Make sure PostgreSQL is running and accessible
2. Verify that the database user has the necessary permissions
3. Check that the migrations are being run in the correct order
4. Look for any SQL syntax errors in the migration files

## Adding New Migrations

When adding new migrations, follow these guidelines:

1. Use a timestamp prefix for the filename (e.g., `20240321_create_new_table.sql`)
2. Add the new migration file to the `MIGRATION_FILES` list in `run_migrations.py`
3. Test the migration in a development environment before running it in production
