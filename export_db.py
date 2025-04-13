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

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def export_collection(collection_name):
    """Export a collection to a JSON file"""
    collection = db[collection_name]
    documents = await collection.find().to_list(length=None)
    
    # Convert ObjectId to string for JSON serialization
    for doc in documents:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        if 'bounding_box' in doc and doc['bounding_box']:
            doc['bounding_box'] = dict(doc['bounding_box'])
    
    # Create backup directory if it doesn't exist
    os.makedirs('backups', exist_ok=True)
    
    # Save to file with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backups/{collection_name}_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2, cls=JSONEncoder)
    
    print(f"Exported {len(documents)} documents from {collection_name} to {filename}")
    return filename

async def export_all_collections():
    """Export all collections in the database"""
    collections = await db.list_collection_names()
    backup_files = {}
    
    for collection in collections:
        if collection not in ['system.indexes', 'system.profile']:
            filename = await export_collection(collection)
            backup_files[collection] = filename
    
    # Save backup metadata
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'collections': backup_files
    }
    
    with open('backups/backup_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print("\nBackup completed successfully!")
    return metadata

if __name__ == "__main__":
    import asyncio
    asyncio.run(export_all_collections()) 