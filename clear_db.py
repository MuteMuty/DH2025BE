from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# MongoDB connection
MONGODB_URL = "mongodb+srv://nekadruga44:blwHFub8RTrALutY@cluster0.kxfh4cw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
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