import os
import glob
from pathlib import Path
from app.db.supabase import SupabaseClient

def run_migrations():
    """Run all SQL migration files in order."""
    # Get the migrations directory
    migrations_dir = Path(__file__).parent / "migrations"
    
    # Get all SQL files and sort them
    migration_files = sorted(glob.glob(str(migrations_dir / "*.sql")))
    
    # Get Supabase client
    supabase = SupabaseClient.get_client()
    
    print("Starting database migrations...")
    
    for migration_file in migration_files:
        print(f"Running migration: {os.path.basename(migration_file)}")
        
        # Read the migration file
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        try:
            # Execute the SQL using Supabase
            result = supabase.rpc('execute_sql', {'sql': sql}).execute()
            print(f"Successfully executed {os.path.basename(migration_file)}")
        except Exception as e:
            print(f"Error executing {os.path.basename(migration_file)}: {str(e)}")
            raise
    
    print("All migrations completed successfully!")

if __name__ == "__main__":
    run_migrations() 