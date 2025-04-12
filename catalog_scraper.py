from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import requests
import json
import time
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
            
            # Step 3: Get all network requests
            print("\nNetwork requests after clicking the link:")
            print("-" * 80)
            
            logs = driver.get_log('performance')
            json_url = None
            
            # Look for the JSON URL in the network logs
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if 'Network.requestWillBeSent' in log['method']:
                        url = log['params']['request']['url']
                        print(f"Request URL: {url}")
                        
                        if 'reader3.isu.pub/vsikatalogi/hofer_' in url and '/reader3_4.json' in url:
                            json_url = url
                            print(f"\nFound JSON data URL: {url}")
                except:
                    continue
            
            if not json_url:
                raise Exception("JSON data URL not found")
            
            # Step 4: Fetch the JSON data
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            json_response = requests.get(json_url, headers=headers)
            json_response.raise_for_status()
            
            # Parse and return the JSON data
            catalog_data = json_response.json()
            
            return {
                'catalog_link': catalog_link,
                'json_url': json_url,
                'data': catalog_data
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
        print(f"JSON data URL: {result['json_url']}")
        print("\nFirst few items of catalog data:")
        print(json.dumps(result['data'], indent=2)[:500] + "...")
    else:
        print("Failed to fetch catalog data") 