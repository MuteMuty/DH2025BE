from catalog_processor import CatalogProcessor
from pymongo import MongoClient
from datetime import datetime
import sys

def test_mongodb_integration(store="Spar"):
    """
    Test MongoDB integration with a specific store.
    
    Args:
        store (str): Name of the store to process (default: "Lidl")
    """
    # Initialize processor with test dates
    processor = CatalogProcessor(
        offer_start_date="2025-04-10",
        offer_end_date="2025-04-20"
    )
    
    try:
        
        print(f"\nProcessing test catalog for {store}...")
        processor.process_catalog(store, f"catalogs/{store.lower()}_catalog.pdf")
        
        
        print(f"\nDisplaying products from MongoDB for {store}:")
        processor.display_products(store_name=store, limit=5)
        
        print("\nVerifying MongoDB data directly:")
        mongo_uri = "mongodb+srv://nekadruga44:blwHFub8RTrALutY@cluster0.kxfh4cw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        client = MongoClient(mongo_uri)
        db = client.discount_hunter
        discounts = db.discounts
        # Count total documents
        total_count = discounts.count_documents({})
        print(f"\nTotal documents in discounts collection: {total_count}")
        
        
        store_count = discounts.count_documents({"store": store})
        print(f"Total {store} products: {store_count}")
        
        
        print(f"\nSample documents for {store}:")
        for doc in discounts.find({"store": store}).limit(3):
            print(f"\nProduct: {doc.get('item_description')}")
            print(f"Price: {doc.get('discount_price')}")
            print(f"Discount: {doc.get('discount_percentage')}%")
            print(f"Offer dates: {doc.get('offer_start_date')} to {doc.get('offer_end_date')}")
            print(f"Bounding box: {doc.get('bounding_box')}")
            
    finally:
        processor.cleanup()

if __name__ == "__main__":
    store = sys.argv[1] if len(sys.argv) > 1 else "Lidl"
    test_mongodb_integration(store) 