import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.db_migrations import run_migrations

def main():
    print("Running database migrations...")
    
    try:
        run_migrations()
        print("All migrations completed successfully!")
    except Exception as e:
        print(f"Some migrations failed: {str(e)}")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main() 