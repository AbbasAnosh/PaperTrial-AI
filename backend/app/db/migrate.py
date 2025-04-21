import os
import glob
from pathlib import Path
import requests
from dotenv import load_dotenv
import time
import sys
import json
import re

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip('/')  # Remove trailing slash if present
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin operations

def is_sql_empty(sql):
    """Check if SQL is empty or contains only comments"""
    # Remove SQL comments and empty lines
    lines = []
    for line in sql.split('\n'):
        # Remove inline comments
        line = re.sub(r'--.*$', '', line)
        # Remove whitespace
        line = line.strip()
        if line:
            lines.append(line)
    
    # Join remaining lines
    sql = ' '.join(lines)
    
    # Remove block comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Check if anything remains after removing comments and whitespace
    return not sql.strip()

def execute_sql_direct(sql):
    """Execute SQL using the Supabase REST API with admin privileges"""
    # Skip empty SQL
    if is_sql_empty(sql):
        print("Skipping empty or comment-only SQL")
        return None
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # Use the REST API endpoint for SQL execution
    url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
    
    print(f"\nExecuting SQL with URL: {url}")
    print(f"Headers: {headers}")
    print(f"SQL: {sql}")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={"sql": sql}
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response text: {response.text}")
        
        if response.status_code != 200 and response.status_code != 204:
            print(f"Error executing SQL: {response.text}")
            try:
                error_details = response.json() if response.text else "No error details available"
                print("Error details:", error_details)
            except json.JSONDecodeError:
                print("Error details could not be parsed as JSON")
            print("Request URL:", url)
            print("Request headers:", headers)
            print("Request body:", {"sql": sql})
            raise Exception(f"SQL execution failed with status code {response.status_code}")
            
        print("SQL executed successfully")
        try:
            return response.json() if response.text else None
        except json.JSONDecodeError:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        raise
    except Exception as e:
        print(f"Error executing SQL: {str(e)}")
        raise

def execute_raw_sql(sql):
    """Execute raw SQL using the Supabase REST API with admin privileges"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # Use the REST API endpoint for raw SQL execution
    url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={"sql": sql}
        )
        
        if response.status_code != 200:
            print(f"Error executing raw SQL: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"Error executing raw SQL: {str(e)}")
        return None

def check_function_exists():
    """Check if the execute_sql function exists in the database"""
    check_sql = """
    SELECT EXISTS (
        SELECT 1 
        FROM pg_proc 
        WHERE proname = 'execute_sql'
    );
    """
    
    result = execute_raw_sql(check_sql)
    return result and len(result) > 0 and result[0].get('exists', False)

def bootstrap_execute_sql_function():
    """Create the execute_sql function if it doesn't exist"""
    print("Checking if execute_sql function exists...")
    
    if check_function_exists():
        print("execute_sql function already exists.")
        return True
    
    print("execute_sql function does not exist. Creating it...")
    
    # SQL to create the execute_sql function
    create_function_sql = """
    create or replace function execute_sql(sql text)
    returns void
    language plpgsql
    as $$
    begin
      execute sql;
    end;
    $$;

    -- Grant execute permission to authenticated users
    grant execute on function execute_sql(text) to authenticated;
    """
    
    try:
        # Use direct SQL execution to create the function
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # Use the Supabase REST API to execute SQL directly
        url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
        response = requests.post(
            url,
            headers=headers,
            json={"sql": create_function_sql}
        )
        
        if response.status_code != 200:
            print(f"Error creating execute_sql function: {response.text}")
            return False
        
        print("Successfully created execute_sql function.")
        return True
    except Exception as e:
        print(f"Error creating execute_sql function: {str(e)}")
        return False

def run_migrations():
    """Run all SQL migrations in order"""
    print("Starting migrations...")
    
    # Get all SQL files from migrations directory
    migration_files = glob.glob("supabase/migrations/*.sql")
    migration_files.sort()  # Ensure ordered execution
    
    # Skip the bootstrap check and run migrations directly
    print("Running migrations directly...")
    print(f"Found {len(migration_files)} migration files:")
    for f in migration_files:
        print(f"  - {f}")
    
    # Run all migrations
    for migration_file in migration_files:
        print(f"\nExecuting migration: {migration_file}")
        
        # Read and execute SQL file
        with open(migration_file, "r", encoding='utf-8') as f:
            sql = f.read().strip()
            
        try:
            execute_sql_direct(sql)
            print(f"Successfully executed {migration_file}")
        except Exception as e:
            print(f"Failed to execute {migration_file}: {str(e)}")
            raise

if __name__ == "__main__":
    # Print environment information
    print("Environment information:")
    print(f"SUPABASE_URL: {SUPABASE_URL}")
    print(f"SUPABASE_KEY: {'*' * len(SUPABASE_KEY) if SUPABASE_KEY else 'Not set'}")
    run_migrations() 