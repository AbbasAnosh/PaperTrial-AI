import asyncio
from app.core.db_migrations import add_extracted_fields_column

async def main():
    print("Running database migrations...")
    
    # Add extracted_fields column
    success = await add_extracted_fields_column()
    if success:
        print("All migrations completed successfully!")
    else:
        print("Some migrations failed. Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main()) 