from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# MongoDB connection
MONGODB_URL = "connection_url_string"
client = AsyncIOMotorClient(MONGODB_URL)
db = client.discount_hunter

async def clear_database():
    """Clear all collections in the database"""
    collections = await db.list_collection_names()
    for collection in collections:
        await db[collection].delete_many({})
    print("Database cleared successfully")

if __name__ == "__main__":
    # Run the clear operation
    asyncio.run(clear_database()) 