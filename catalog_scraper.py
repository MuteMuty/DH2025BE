import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

def get_latest_catalog_data():
    try:
        # Step 1: Get the main catalog page
        base_url = "https://vsikatalogi.si/hofer-katalog"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        
        # Step 2: Parse the page to find the latest catalog link
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first catalog link
        catalog_link = None
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and 'hofer-katalog-od' in href:
                catalog_link = href
                break
        
        if not catalog_link:
            raise Exception("Catalog link not found")
        
        # Step 3: Follow the catalog link
        catalog_response = requests.get(catalog_link, headers=headers)
        catalog_response.raise_for_status()
        
        # Step 4: Find the JSON data URL in the response
        json_url = None
        json_pattern = r'https://reader3\.isu\.pub/vsikatalogi/hofer_[a-f0-9]+/reader3_4\.json'
        matches = re.findall(json_pattern, catalog_response.text)
        if matches:
            json_url = matches[0]
        
        if not json_url:
            raise Exception("JSON data URL not found")
        
        # Step 5: Fetch the JSON data
        json_response = requests.get(json_url, headers=headers)
        json_response.raise_for_status()
        
        # Parse and return the JSON data
        catalog_data = json_response.json()
        
        return {
            'catalog_link': catalog_link,
            'json_url': json_url,
            'data': catalog_data
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    result = get_latest_catalog_data()
    if result:
        print(f"Catalog page: {result['catalog_link']}")
        print(f"JSON data URL: {result['json_url']}")
        print("\nFirst few items of catalog data:")
        print(json.dumps(result['data'], indent=2)[:500] + "...")
    else:
        print("Failed to fetch catalog data") 