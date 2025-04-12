from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import asyncio
from bson import ObjectId

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

async def init_database():
    """Initialize database with dummy data"""
    # Clear existing data
    await clear_database()
    
    # Sample stores
    stores = ["Lidl", "Hofer", "Spar", "Mercator", "Eurospin"]
    
    # Create dummy discounts
    discounts = []
    for i in range(50):  # Create 50 dummy discounts
        store = stores[i % len(stores)]
        normal_price = round(10 + (i * 2.5), 2)
        discount_percentage = 10 + (i % 30)  # Random discount between 10% and 40%
        discount_price = round(normal_price * (1 - discount_percentage/100), 2)
        
        start_date = datetime.utcnow() - timedelta(days=i % 7)
        end_date = start_date + timedelta(days=14)
        
        # Create bounding box for the item in the PDF
        bounding_box = {
            "x": i * 10,
            "y": i * 10,
            "width": 100,
            "height": 100
        }
        
        discount = {
            "item_description": f"Product {i+1}",
            "discount_price": discount_price,
            "discount_percentage": discount_percentage,
            "store": store,
            "offer_start_date": start_date,
            "offer_end_date": end_date,
            "trending_score": 0,
            "quantity": i % 10 + 1,  # Random quantity between 1 and 10
            "bounding_box": bounding_box
        }
        discounts.append(discount)
    
    # Insert discounts
    if discounts:
        await db.discounts.insert_many(discounts)
        print(f"Inserted {len(discounts)} dummy discounts")
    
    # Create some dummy shopping cart items
    shopping_cart_items = []
    for i in range(20):  # Create 20 dummy shopping cart items
        user_id = f"user_{i % 5}"  # 5 different users
        # Get a random discount ID from the inserted discounts
        discount = discounts[i % len(discounts)]
        discount_id = str(discount["_id"]) if "_id" in discount else str(ObjectId())
        
        item = {
            "user_id": user_id,
            "discount_id": discount_id,
            "added_date": datetime.utcnow() - timedelta(days=i % 3)
        }
        shopping_cart_items.append(item)
    
    # Insert shopping cart items
    if shopping_cart_items:
        await db.shopping_cart.insert_many(shopping_cart_items)
        print(f"Inserted {len(shopping_cart_items)} dummy shopping cart items")
    
    # Create some dummy notifications
    notifications = []
    for i in range(10):  # Create 10 dummy notifications
        user_id = f"user_{i % 5}"  # 5 different users
        
        notification = {
            "user_id": user_id,
            "device_id": f"device_{i}"
        }
        notifications.append(notification)
    
    # Insert notifications
    if notifications:
        await db.notifications.insert_many(notifications)
        print(f"Inserted {len(notifications)} dummy notifications")
    
    print("Database initialized with dummy data successfully")

if __name__ == "__main__":
    # Run the initialization
    asyncio.run(init_database()) 