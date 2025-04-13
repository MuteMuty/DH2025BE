from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import requests
import json
import time
import re
from datetime import datetime

def get_latest_catalog_data():
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Enable performance logging
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Step 1: Get the main catalog page
            base_url = "https://vsikatalogi.si/hofer-katalog"
            driver.get(base_url)
            
            # Wait for the page to load and any overlays to disappear
            wait = WebDriverWait(driver, 10)
            
            # Wait for the page to be fully loaded
            wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            
            # Handle the overlay
            try:
                # Wait for the overlay to appear
                overlay = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-dialog-overlay')))
                print("Found overlay, waiting for it to disappear...")
                
                # Try to click the overlay to dismiss it
                try:
                    ActionChains(driver).move_to_element(overlay).click().perform()
                    print("Clicked overlay to dismiss it")
                except:
                    print("Could not click overlay directly")
                
                # Wait for the overlay to disappear
                wait.until(EC.invisibility_of_element(overlay))
                print("Overlay disappeared")
                
                # Additional wait to ensure everything is settled
                time.sleep(1)
            except Exception as e:
                print(f"Overlay handling error: {str(e)}")
                # Continue even if overlay handling fails
            
            # Step 2: Find and click the first catalog link
            catalog_link = None
            # Wait for links to be present
            links = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a')))
            
            for link in links:
                href = link.get_attribute('href')
                if href and 'hofer-katalog-od' in href:
                    catalog_link = href
                    print(f"\nFound catalog link: {href}")
                    
                    # Scroll the link into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", link)
                    time.sleep(0.5)  # Wait for scroll to complete
                    
                    # Wait for the link to be clickable
                    wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[@href='{href}']")))
                    
                    # Try to click using JavaScript
                    try:
                        driver.execute_script("arguments[0].click();", link)
                        print("Clicked link using JavaScript")
                    except:
                        # If JavaScript click fails, try regular click
                        try:
                            link.click()
                            print("Clicked link using regular click")
                        except Exception as e:
                            print(f"Failed to click link: {str(e)}")
                            raise
                    
                    break
            
            if not catalog_link:
                raise Exception("Catalog link not found")
            
            # Wait for the new page to load
            wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            
            # Step 3: Get all network requests and find the Issuu embed URL
            print("\nNetwork requests after clicking the link:")
            print("-" * 80)
            
            logs = driver.get_log('performance')
            issuu_hash = None
            
            # Look for the Issuu embed URL in the network logs
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if 'Network.requestWillBeSent' in log['method']:
                        url = log['params']['request']['url']
                        # print(f"Request URL: {url}")
                        
                        # Look for the Issuu embed URL pattern
                        if 'e.issuu.com/embed.html' in url and 'd=hofer_' in url:
                            # Extract the hash using regex
                            match = re.search(r'hofer_([a-f0-9]+)', url)
                            if match:
                                issuu_hash = match.group(1)
                                print(f"\nFound Issuu hash: {issuu_hash}")
                                break
                except:
                    continue
            
            if not issuu_hash:
                raise Exception("Issuu hash not found")
            
            # Construct the JSON URL using the hash
            json_url = f"https://reader3.isu.pub/vsikatalogi/hofer_{issuu_hash}/reader3_4.json"
            print(f"\nConstructed JSON URL: {json_url}")
            
            # Step 4: Fetch the JSON data
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            json_response = requests.get(json_url, headers=headers)
            json_response.raise_for_status()
            
            # Parse the JSON data
            catalog_data = json_response.json()
            
            # Extract image URLs from the pages
            image_urls = []
            if 'document' in catalog_data and 'pages' in catalog_data['document']:
                for page in catalog_data['document']['pages']:
                    if 'imageUri' in page:
                        # Construct full image URL
                        image_url = f"https://{page['imageUri']}"
                        image_urls.append({
                            'page_number': len(image_urls) + 1,
                            'url': image_url,
                            'width': page.get('width'),
                            'height': page.get('height')
                        })
            
            return {
                'catalog_link': catalog_link,
                'issuu_hash': issuu_hash,
                'json_url': json_url,
                'image_urls': image_urls,
                'total_pages': len(image_urls)
            }
            
        finally:
            # Always close the browser
            driver.quit()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    result = get_latest_catalog_data()
    if result:
        print(f"\nCatalog page: {result['catalog_link']}")
        print(f"Issuu hash: {result['issuu_hash']}")
        print(f"JSON data URL: {result['json_url']}")
        print(f"\nTotal pages: {result['total_pages']}")
        print("\nImage URLs:")
        for page in result['image_urls']:
            print(f"Page {page['page_number']}: {page['url']}")
    else:
        print("Failed to fetch catalog data") 