from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = "mongodb+srv://nekadruga44:blwHFub8RTrALutY@cluster0.kxfh4cw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tls=true"
client = AsyncIOMotorClient(MONGODB_URL)
db = client.discount_hunter

async def restore_collection(collection_name, filename):
    """Restore a collection from a JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        collection = db[collection_name]
        
        # Clear existing collection
        await collection.delete_many({})
        
        # Convert string IDs back to ObjectId
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = ObjectId(doc['_id'])
            if 'offer_start_date' in doc:
                doc['offer_start_date'] = datetime.fromisoformat(doc['offer_start_date'])
            if 'offer_end_date' in doc:
                doc['offer_end_date'] = datetime.fromisoformat(doc['offer_end_date'])
            if 'added_date' in doc:
                doc['added_date'] = datetime.fromisoformat(doc['added_date'])
        
        # Insert documents
        if documents:
            await collection.insert_many(documents)
        
        print(f"Restored {len(documents)} documents to {collection_name}")
        return True
    except Exception as e:
        print(f"Error restoring {collection_name}: {str(e)}")
        return False

async def restore_from_backup(backup_dir='backups'):
    """Restore all collections from backup files"""
    try:
        # Read backup metadata
        with open(f'{backup_dir}/backup_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        success = True
        for collection, filename in metadata['collections'].items():
            if not await restore_collection(collection, filename):
                success = False
        
        if success:
            print("\nDatabase restoration completed successfully!")
        else:
            print("\nDatabase restoration completed with some errors.")
        
        return success
    except Exception as e:
        print(f"Error during restoration: {str(e)}")
        return False

async def restore_latest_backup():
    """Restore from the most recent backup"""
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        print("No backup directory found!")
        return False
    
    # Find the most recent backup metadata file
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith('backup_metadata')]
    if not backup_files:
        print("No backup files found!")
        return False
    
    # Sort by timestamp (newest first)
    backup_files.sort(reverse=True)
    latest_backup = backup_files[0]
    
    print(f"Restoring from backup: {latest_backup}")
    return await restore_from_backup(backup_dir)

if __name__ == "__main__":
    import asyncio
    asyncio.run(restore_latest_backup()) 