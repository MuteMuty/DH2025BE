import os
import json
import re
from datetime import datetime
from PIL import Image
import fitz
from google import genai
from pymongo import MongoClient
from bson import ObjectId
import matplotlib.pyplot as plt
import time

class CatalogProcessor:
    def __init__(self, offer_start_date=None, offer_end_date=None, max_pages=10):
        mongo_uri = "connection_url_string"
        self.client = MongoClient(mongo_uri)
        self.db = self.client.discount_hunter  
        
        api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyBB5h2P-kr3eVSsSdVuNt67hlq5M0BjJPs')
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-1.5-pro'
        
        self.offer_start_date = offer_start_date
        self.offer_end_date = offer_end_date
        self.max_pages = max_pages
        
        self.output_folder = "processed_catalogs"
        self.temp_folder = "temp_pages"
        self.PADDING = 100
        
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.temp_folder, exist_ok=True)

    def save_product_image(self, image, bbox, product_name, price, output_path):
        x1, y1, x2, y2 = bbox
        width, height = image.size
        
        bottom_padding = self.PADDING * 1.5
        
        x1_padded = max(0, x1 - self.PADDING)
        y1_padded = max(0, y1 - self.PADDING)
        x2_padded = min(width, x2 + self.PADDING)
        y2_padded = min(height, y2 + int(bottom_padding))
        
        if x1_padded >= x2_padded or y1_padded >= y2_padded:
            print(f"ERROR: Invalid coordinates after padding!")
            return
        
        if x1_padded < 0 or y1_padded < 0 or x2_padded > width or y2_padded > height:
            print(f"ERROR: Coordinates out of bounds after padding!")
            return
        
        try:
            cropped = image.crop((x1_padded, y1_padded, x2_padded, y2_padded))
            cropped.save(output_path)
            print(f"Successfully saved: {output_path}")
        except Exception as e:
            print(f"Error saving image: {e}")

    def create_summary_image(self, image, products, output_path):
        plt.figure(figsize=(12, 8))
        plt.imshow(image)
        
        for i, product in enumerate(products):
            bbox = product["bbox"]
            x1, y1, x2, y2 = bbox
            
            plt.plot([x1, x2, x2, x1, x1], [y1, y1, y2, y2, y1], 'r-', linewidth=2)
            
            label = f"{product['name']} - {product.get('price', 'no_price')}"
            if product.get('quantity'):
                label += f" - {product['quantity']}"
            if product.get('discount'):
                label += f" ({product['discount']})"
            if product.get('description'):
                label += f"\n{product['description']}"
                
            plt.text(x1, y1-10, label, 
                     color='red', fontsize=8, bbox=dict(facecolor='white', alpha=0.7))
        
        plt.axis('off')
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=300)
        plt.close()
        print(f"\nSaved summary image: {output_path}")

    def process_catalog(self, store_name, pdf_path):
        print(f"\nProcessing catalog for {store_name}")
        
        image_paths = self._convert_pdf_to_images(pdf_path)
        
        for i, image_path in enumerate(image_paths):
            page_num = i + 1
            print(f"\nProcessing page {page_num}")
            
            page_dir = os.path.join(self.output_folder, f"page{page_num}")
            os.makedirs(page_dir, exist_ok=True)
            
            image = Image.open(image_path)
            products = self._process_image(image_path)
            
            for j, product in enumerate(products):
                try:
                    product_name = product.get("name", "Unknown_Product")
                    if product_name is None:
                        product_name = f"Unknown_Product_{j+1}"
                    else:
                        product_name = str(product_name).replace('\n', ' ').replace('\r', ' ')
                        product_name = re.sub(r'[\\/*?:"<>|]', "_", product_name)
                        if len(product_name) > 50:
                            product_name = product_name[:50]
                    
                    price = product.get("price", "no_price")
                    if price is None or price.strip() == "":
                        price = "no_price"
                    else:
                        try:
                            price = f"{float(price.replace(',', '.')):.2f}"
                        except (ValueError, AttributeError):
                            price = "no_price"
                    
                    bbox = product.get("bbox")
                    if not bbox or len(bbox) != 4:
                        print(f"Warning: Invalid bbox for product {j+1}, skipping...")
                        continue
                    
                    output_path = os.path.join(page_dir, f"{product_name}_{price}.png")
                    self.save_product_image(image, bbox, product_name, price, output_path)
                    
                except Exception as e:
                    print(f"Error processing product {j+1}: {str(e)}")
                    continue
            
            try:
                summary_path = os.path.join(page_dir, "all_products.png")
                self.create_summary_image(image, products, summary_path)
            except Exception as e:
                print(f"Error creating summary image: {str(e)}")
            
            for product in products:
                self._store_product(store_name, product)
            
            print(f"Page {page_num} processing complete. Found {len(products)} products.")
        
        print(f"\nCatalog processing complete for {store_name}")

    def _convert_pdf_to_images(self, pdf_path, max_pages=None):
        if max_pages is None:
            max_pages = self.max_pages
            
        print(f"Converting PDF to images: {pdf_path}")
        doc = fitz.open(pdf_path)
        image_paths = []
        
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            image_path = os.path.join(self.temp_folder, f"page_{page_num+1}.png")
            pix.save(image_path)
            image_paths.append(image_path)
            print(f"Saved page {page_num+1} as {image_path}")
        
        doc.close()
        return image_paths

    def _process_image(self, image_path):
        print(f"\nProcessing image: {image_path}")
        image = Image.open(image_path)
        width, height = image.size
        print(f"Image dimensions: {width}x{height}")
        
        prompt = (
            "You are given an image of a grocery catalog page. Your task is to detect and extract all individual buyable products.\n"
            "\n"
            "For each product, return the following information:\n"
            "1. Bounding box in [ymin, xmin, ymax, xmax] format:\n"
            "   - The box MUST include the visual image of the actual product (e.g., if the product is 'banana', the image of bananas must be fully inside the box).\n"
            "   - Also include the red price box, and all nearby relevant text such as name, quantity, description, and discount.\n"
            "   - Err on the side of including slightly too much (more margin is okay), but do not miss any part of the product image.\n"
            "2. 'label': The product name (e.g., 'Banana')\n"
            "3. 'price': The main visible price (usually in a red box). If there are multiple prices, choose the boldest or largest one.\n"
            "   - If the price is written with a large number and a small number next to it (e.g., '1 99'), interpret it as '1.99'\n"
            "   - If the price is written with a comma (e.g., '1,99'), convert it to '1.99'\n"
            "   - Always use decimal point (.) format for prices\n"
            "4. 'quantity': Visible unit/weight (e.g., '1 kg', '400 g')\n"
            "5. 'description': Any additional descriptive text near the product (excluding name and quantity)\n"
            "6. 'discount': If visible, include any discount indicators like '-30%' or '25% off'. Otherwise, leave empty.\n"
            "7. 'validity_date': The start date of the offer, if present. Convert formats like '10.4.' into '2025-04-10'.\n"
            "8. 'offer_end': The end date of the offer, if present. Use same formatting.\n"
            "\n"
            "Important:\n"
            "- Every bounding box must contain the visual object that is being sold — not just the name and price.\n"
            "- If the product is shown with an image (e.g., shoes, cheese, ham), that image must be inside the bounding box.\n"
            "- These bounding boxes will be used to generate product cutouts — so they must be visually complete.\n"
            "- Only include real, buyable products. Ignore general text banners or decorations.\n"
            "\n"
            "Return your results as a JSON array of objects with keys: 'ymin', 'xmin', 'ymax', 'xmax', 'label', 'price', 'quantity', 'description', 'discount', 'validity_date', 'offer_end'."
        )

        import io
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        from google.genai import types
        content = types.Content(
            parts=[
                types.Part(text=prompt),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=img_byte_arr
                    )
                )
            ]
        )
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=content
        )
        
        try:
            json_str = response.text
            if "```json" in json_str:
                match = re.search(r'```json\s*(.*?)\s*```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            elif "```" in json_str:
                match = re.search(r'```\s*(.*?)\s*```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            
            detections = json.loads(json_str)
            print(f"Number of detections: {len(detections)}")
            
            products = []
            for detection in detections:
                required_keys = ['ymin', 'xmin', 'ymax', 'xmax']
                missing_keys = [key for key in required_keys if key not in detection]
                
                if missing_keys:
                    print(f"Warning: Missing keys in detection: {missing_keys}")
                    continue
                
                ymin = int(detection['ymin'] / 1000 * height)
                xmin = int(detection['xmin'] / 1000 * width)
                ymax = int(detection['ymax'] / 1000 * height)
                xmax = int(detection['xmax'] / 1000 * width)
                
                validity_date = detection.get('validity_date', '')
                offer_start_date = self.offer_start_date
                offer_end_date = self.offer_end_date
                
                if validity_date:
                    date_pattern = r'(\d{1,2})\.(\d{1,2})?.?-(\d{1,2})\.(\d{1,2})?(?:\.(\d{4}))?'
                    match = re.search(date_pattern, validity_date)
                    
                    if match:
                        start_day, start_month, end_day, end_month, year = match.groups()
                        year = year or "2025"
                        end_month = end_month or start_month
                        
                        offer_start_date = f"{year}-{int(start_month):02d}-{int(start_day):02d}"
                        offer_end_date = f"{year}-{int(end_month):02d}-{int(end_day):02d}"
                    else:
                        single_date_pattern = r'(\d{1,2})\.(\d{1,2})?(?:\.(\d{4}))?'
                        match = re.search(single_date_pattern, validity_date)
                        
                        if match:
                            day, month, year = match.groups()
                            year = year or "2025"
                            month = month or "4"
                            
                            date = f"{year}-{int(month):02d}-{int(day):02d}"
                            offer_start_date = date
                            offer_end_date = date
                
                product = {
                    "bbox": [xmin, ymin, xmax, ymax],
                    "name": detection.get('label', 'Unknown Product'),
                    "price": detection.get('price', 'Unknown Price'),
                    "quantity": detection.get('quantity', ''),
                    "description": detection.get('description', ''),
                    "discount": detection.get('discount', ''),
                    "offer_start_date": offer_start_date,
                    "offer_end_date": offer_end_date
                }
                products.append(product)
                
                print(f"Product: {product['name']}, Price: {product['price']}, Quantity: {product['quantity']}, "
                      f"Description: {product['description']}, Discount: {product['discount']}, "
                      f"Offer Dates: {offer_start_date} to {offer_end_date}")
            
            return products
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"\nError parsing Gemini AI response: {e}")
            print(f"Raw response: {response.text}")
            return []

    def _store_product(self, store_name, product):
        try:
            price = float(product["price"].replace(',', '.'))
        except (ValueError, AttributeError):
            price = 0.0

        discount_percentage = None
        if product.get("discount"):
            try:
                discount_percentage = float(re.search(r'(\d+)%', product["discount"]).group(1))
            except (AttributeError, ValueError):
                pass

        product_name = product["name"].replace('\n', ' ').strip()

        product_doc = {
            "item_description": product_name,
            "discount_price": price,
            "discount_percentage": discount_percentage,
            "store": store_name,
            "offer_start_date": datetime.strptime(product["offer_start_date"], "%Y-%m-%d"),
            "offer_end_date": datetime.strptime(product["offer_end_date"], "%Y-%m-%d"),
            "trending_score": 0,
            "quantity": product.get("quantity", ""),
            "bounding_box": {
                "x": product["bbox"][0],
                "y": product["bbox"][1],
                "width": product["bbox"][2] - product["bbox"][0],
                "height": product["bbox"][3] - product["bbox"][1]
            }
        }
        
        self.db.discounts.insert_one(product_doc)
        
        print(f"Stored product: {product_name} in MongoDB")

    def get_store_products(self, store_name):
        return list(self.db.discounts.find({"store": store_name}))

    def get_product(self, store_name, product_name):
        return self.db.discounts.find_one({"store": store_name, "item_description": product_name})

    def cleanup(self):
        for file in os.listdir(self.temp_folder):
            try:
                file_path = os.path.join(self.temp_folder, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except PermissionError:
                print(f"Warning: Could not remove {file_path} - file is in use")
            except Exception as e:
                print(f"Warning: Error removing {file_path}: {e}")
        
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            self.client.close()

    def display_products(self, store_name=None, limit=10):
        query = {}
        if store_name:
            query["store"] = store_name
            
        products = list(self.db.discounts.find(query).limit(limit))
        
        print(f"\nFound {len(products)} products:")
        for i, product in enumerate(products):
            print(f"\nProduct {i+1}:")
            print(f"  ID: {product.get('_id', 'N/A')}")
            print(f"  Store: {product.get('store', 'N/A')}")
            print(f"  Name: {product.get('item_description', 'N/A')}")
            print(f"  Price: {product.get('discount_price', 'N/A')}")
            print(f"  Quantity: {product.get('quantity', 'N/A')}")
            print(f"  Offer Start: {product.get('offer_start_date', 'N/A')}")
            print(f"  Offer End: {product.get('offer_end_date', 'N/A')}")
            print(f"  Description: {product.get('description', 'N/A')}")
            print(f"  Discount: {product.get('discount_percentage', 'N/A')}%")
            print(f"  Last Updated: {product.get('last_updated', 'N/A')}")
            
        return products

if __name__ == "__main__":
    processor = CatalogProcessor(
        offer_start_date="2025-04-10",
        offer_end_date="2025-04-20"
    )
    
    try:
        store = "Eurospin"
        processor.process_catalog(store, "catalogs/eurospin_catalog.pdf")
        processor.display_products(store_name=store, limit=5)
        mercator_products = processor.get_store_products(store)
        print(f"\nFound {len(mercator_products)} products in Mercator catalog")
        banana = processor.get_product("Mercator", "banane")
        if banana:
            print(f"\nBanana product: {banana}")
    finally:
        processor.cleanup() 