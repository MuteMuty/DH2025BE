from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from bson import ObjectId
import asyncio
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = "mongodb+srv://nekadruga44:blwHFub8RTrALutY@cluster0.kxfh4cw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tls=true"
client = AsyncIOMotorClient(MONGODB_URL)
db = client.discount_hunter

# Pydantic models
class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

class Discount(BaseModel):
    item_description: str
    discount_price: float
    discount_percentage: Optional[float] = None
    store: str
    offer_start_date: datetime
    offer_end_date: datetime
    trending_score: int = 0
    quantity: Optional[int] = None
    bounding_box: Optional[BoundingBox] = None

class ShoppingCartItem(BaseModel):
    user_id: str
    discount_id: str
    added_date: datetime = Field(default_factory=datetime.utcnow)

class Notification(BaseModel):
    user_id: str
    device_id: str

# Helper functions
async def update_trending_scores():
    """Update trending scores based on shopping cart activity"""
    # Get all active discounts
    active_discounts = await db.discounts.find({
        "offer_end_date": {"$gt": datetime.utcnow()}
    }).to_list(length=None)
    
    for discount in active_discounts:
        # Count how many users have this item in their cart
        cart_count = await db.shopping_cart.count_documents({
            "discount_id": str(discount["_id"])
        })
        
        # Update trending score
        await db.discounts.update_one(
            {"_id": discount["_id"]},
            {"$set": {"trending_score": cart_count}}
        )

# Background task for updating trending scores
async def update_scores_periodically():
    while True:
        await update_trending_scores()
        await asyncio.sleep(3600)  # Update every hour

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    trending_task = asyncio.create_task(update_scores_periodically())
    yield
    # Shutdown
    trending_task.cancel()
    try:
        await trending_task
    except asyncio.CancelledError:
        pass

# Initialize FastAPI app with lifespan
app = FastAPI(title="Discount Hunter API", lifespan=lifespan)

# API endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to Discount Hunter API"}

@app.get("/api/search")
async def search_items(
    query: Optional[str] = None,
    store: Optional[str] = None,
    sort_by: Optional[str] = None,
    min_discount: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10,
    offset: int = 0
):
    try:
        # Build search query
        search_query = {}
        if query:
            search_query["item_description"] = {"$regex": query, "$options": "i"}
        if store:
            search_query["store"] = store
        if min_discount:
            search_query["discount_percentage"] = {"$gte": min_discount}
        if max_price:
            search_query["discount_price"] = {"$lte": max_price}

        # Get total count for pagination
        total_count = await db.discounts.count_documents(search_query)

        # Execute search with optional sorting
        if sort_by:
            sort_query = {}
            if sort_by == "price":
                sort_query["discount_price"] = 1
            elif sort_by == "store":
                sort_query["store"] = 1
            elif sort_by == "date":
                sort_query["offer_end_date"] = 1
            elif sort_by == "trending":
                sort_query["trending_score"] = -1
            items = await db.discounts.find(search_query).sort(sort_query).skip(offset).limit(limit).to_list(length=limit)
        else:
            items = await db.discounts.find(search_query).skip(offset).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item["_id"] = str(item["_id"])
            if "bounding_box" in item and item["bounding_box"]:
                item["bounding_box"] = dict(item["bounding_box"])
        
        return {
            "items": items,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
    except Exception as e:
        print(f"Error in search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trending")
async def get_trending_items(limit: int = 10):
    try:
        items = await db.discounts.find({
            "offer_end_date": {"$gt": datetime.utcnow()}
        }).sort("trending_score", -1).limit(limit).to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item["_id"] = str(item["_id"])
            if "bounding_box" in item and item["bounding_box"]:
                item["bounding_box"] = dict(item["bounding_box"])
        
        return items
    except Exception as e:
        print(f"Error in trending: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/shopping-cart")
async def add_to_cart(item: ShoppingCartItem):
    try:
        # Check if discount exists
        discount = await db.discounts.find_one({"_id": ObjectId(item.discount_id)})
        if not discount:
            raise HTTPException(status_code=404, detail="Discount not found")
        
        # Check if item is already in cart
        existing_item = await db.shopping_cart.find_one({
            "user_id": item.user_id,
            "discount_id": item.discount_id
        })
        
        if existing_item:
            raise HTTPException(status_code=400, detail="Item already in cart")
        
        # Add to shopping cart
        result = await db.shopping_cart.insert_one(item.dict())
        
        # Update trending scores
        await update_trending_scores()
        
        return {"message": "Item added to cart", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error in add_to_cart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/shopping-cart/{user_id}")
async def get_shopping_cart(user_id: str):
    try:
        items = await db.shopping_cart.find({"user_id": user_id}).to_list(length=100)
        
        # Convert ObjectId to string for JSON serialization
        for item in items:
            item["_id"] = str(item["_id"])
        
        return items
    except Exception as e:
        print(f"Error in get_shopping_cart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/shopping-cart/{user_id}/{item_id}")
async def remove_from_cart(user_id: str, item_id: str):
    try:
        result = await db.shopping_cart.delete_one({
            "user_id": user_id,
            "discount_id": item_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found in cart")
        
        # Update trending scores
        await update_trending_scores()
        
        return {"message": "Item removed from cart"}
    except Exception as e:
        print(f"Error in remove_from_cart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications")
async def add_notification(notification: Notification):
    try:
        # Check if notification preferences already exist
        existing = await db.notifications.find_one({
            "user_id": notification.user_id
        })
        
        if existing:
            # Update existing preferences
            result = await db.notifications.update_one(
                {"user_id": notification.user_id},
                {"$set": notification.dict()}
            )
            return {"message": "Notification preferences updated"}
        else:
            # Create new preferences
            result = await db.notifications.insert_one(notification.dict())
            return {"message": "Notification preferences saved", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error in add_notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications/{user_id}")
async def get_notifications(user_id: str):
    try:
        notification = await db.notifications.find_one({"user_id": user_id})
        if not notification:
            raise HTTPException(status_code=404, detail="No notification preferences found")
        
        # Convert ObjectId to string for JSON serialization
        notification["_id"] = str(notification["_id"])
        
        return notification
    except Exception as e:
        print(f"Error in get_notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 