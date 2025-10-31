"""
Search engine for Google Maps
"""
import time
import random
from typing import List, Set, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from models.place import SearchTask, Place
from config.settings import ScraperConfig
from core.driver_manager import DriverManager
from utils.extractors import (
    extract_coordinates_from_link, 
    parse_address, 
    clean_text,
    parse_rating,
    parse_reviews_count
)


class MapsSearchEngine:
    """Handles searching and extracting data from Google Maps"""
    
    def __init__(self, driver_manager: DriverManager, config: ScraperConfig):
        self.driver_manager = driver_manager
        self.config = config
        self.driver = driver_manager.driver
        self.seen_links: Set[str] = set()
        self.seen_names: Set[str] = set()
    
    def search(self, task: SearchTask) -> List[Place]:
        """
        Execute a search task and return found places
        
        Args:
            task: SearchTask to execute
            
        Returns:
            List of Place objects
        """
        print(f"Searching: {task}")
        
        places = []
        query = task.get_query()
        
        # Perform search with retry
        if not self._perform_search(query):
            print(f"Failed to perform search for: {query}")
            return places
        
        # Wait for results to load
        time.sleep(self.config.scroll_pause_time)
        
        # Scroll to load more results
        place_elements = self._scroll_and_collect_elements(task.max_results)
        
        print(f"Found {len(place_elements)} place elements")
        
        # Extract details from each place
        for idx, element in enumerate(place_elements):
            try:
                place = self._extract_place_details(element, task)
                
                if place and self._is_valid_place(place):
                    places.append(place)
                    print(f"  [{idx+1}/{len(place_elements)}] ✓ {place.name}")
                
                # Random delay
                time.sleep(random.uniform(self.config.min_delay, self.config.max_delay))
                
            except Exception as e:
                print(f"  [{idx+1}/{len(place_elements)}] Error: {e}")
                continue
        
        print(f"Collected {len(places)} places for: {task}")
        return places
    
    def _perform_search(self, query: str, max_retries: int = 3) -> bool:
        """Perform search with retry"""
        for attempt in range(max_retries):
            try:
                print(f"  Search attempt {attempt + 1}/{max_retries}")
                
                if not self.driver_manager.reset_to_maps_home():
                    continue
                
                search_box = WebDriverWait(self.driver, self.config.element_wait_timeout).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        'input[aria-label="Search Google Maps"], input[id="searchboxinput"]'
                    ))
                )
                
                search_box.clear()
                time.sleep(0.5)
                search_box.send_keys(query)
                time.sleep(1)
                search_box.send_keys(Keys.RETURN)
                time.sleep(3)
                
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                    )
                    return True
                except TimeoutException:
                    print(f"  Results timeout")
                    
            except Exception as e:
                print(f"  Search failed: {e}")
                time.sleep(2)
        
        return False
    
    def _scroll_and_collect_elements(self, max_results: int) -> List:
        """Scroll and collect place elements"""
        place_elements = []
        
        try:
            results_panel = None
            for selector in ['div[role="feed"]', 'div.m6QErb']:
                try:
                    results_panel = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"  Found panel: {selector}")
                    break
                except:
                    continue
            
            if not results_panel:
                return []
            
            scroll_attempts = 0
            no_change_count = 0
            
            while len(place_elements) < max_results and scroll_attempts < self.config.max_scroll_attempts:
                current_elements = []
                for selector in ['a.hfpxzc', 'div.Nv2PK']:
                    try:
                        current_elements = results_panel.find_elements(By.CSS_SELECTOR, selector)
                        if len(current_elements) > 0:
                            break
                    except:
                        continue
                
                if len(current_elements) > len(place_elements):
                    place_elements = current_elements
                    no_change_count = 0
                else:
                    no_change_count += 1
                
                if no_change_count >= 3:
                    break
                
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    results_panel
                )
                
                time.sleep(self.config.scroll_pause_time)
                scroll_attempts += 1
                print(f"  Scroll {scroll_attempts}: {len(place_elements)} elements")
            
        except Exception as e:
            print(f"Scroll error: {e}")
        
        return place_elements[:max_results]
    
    def _extract_place_details(self, element, task: SearchTask) -> Optional[Place]:
        """Extract place details"""
        try:
            # Get preview name
            preview_name = None
            try:
                preview_name = element.text.split('\n')[0] if element.text else None
            except:
                pass
            
            # Click element
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except:
                try:
                    element.click()
                except:
                    return None
            
            # Wait for details panel
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.m6QErb[aria-label]'))
                )
            except:
                pass
            
            # Wait for content to render
            time.sleep(4)
            
            # Extract name
            name = self._extract_text('h1.DUwDvf, h1.fontHeadlineLarge, h1')
            if not name or name in ['Hasil', 'Results', '']:
                name = preview_name
            
            if not name:
                return None
            
            # Extract category
            category = self._extract_text('button.DkEaL, div.LBgpqf button, button[jsaction*="category"]')
            
            # Extract address
            address = self._extract_text('button[data-item-id="address"], div.rogA2c, button[aria-label*="Address"]')
            
            # Try aria-label if address not found
            if not address:
                try:
                    addr_elems = self.driver.find_elements(By.CSS_SELECTOR, 'button[data-item-id*="address"]')
                    for elem in addr_elems:
                        aria = elem.get_attribute('aria-label')
                        if aria and ':' in aria:
                            address = aria.split(':', 1)[1].strip()
                            break
                except:
                    pass
            
            # DEBUG: Print raw address
            if address:
                print(f"    🔍 RAW ADDRESS: {address}")
            
            subdistrict, district, city, province, zip_code = parse_address(address) if address else (None, None, None, None, None)
            
            # DEBUG: Print parsed components
            print(f"    📍 Subdistrict: {subdistrict or 'N/A'}")
            print(f"    📍 District: {district or 'N/A'}")
            print(f"    📍 City: {city or 'N/A'}")
            print(f"    📍 Province: {province or 'N/A'}")
            print(f"    📍 ZIP: {zip_code or 'N/A'}")
            
            # Get coordinates from URL
            link = self.driver.current_url
            latitude, longitude = extract_coordinates_from_link(link)
            
            # Extract rating
            rating_text = self._extract_text('div.F7nice span[aria-hidden="true"], span.ceNzKf')
            rating = parse_rating(rating_text)
            
            # Extract reviews
            reviews_text = self._extract_text('div.F7nice span[aria-label*="reviews"], span.UY7F9, button[aria-label*="reviews"]')
            reviews_count = parse_reviews_count(reviews_text)
            
            # Extract phone
            phone = self._extract_text('button[data-item-id*="phone"]')
            if not phone:
                try:
                    phone_elem = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
                    aria = phone_elem.get_attribute('aria-label')
                    if aria and ':' in aria:
                        phone = aria.split(':', 1)[1].strip()
                except:
                    pass
            
            # Extract website
            website = self._extract_attribute('a[data-item-id="authority"]', 'href')
            
            # Extract opening hours
            opening_hours = self._extract_opening_hours()
            
            # Extract stars
            stars = self._extract_star_distribution()
            
            # Debug
            print(f"    📍 Category: {category or 'N/A'}")
            print(f"    📍 Address: {address or 'N/A'}")
            print(f"    📍 Coords: ({latitude}, {longitude})")
            print(f"    📍 Phone: {phone or 'N/A'}")
            
            # Create Place
            place = Place(
                name=clean_text(name),
                category=clean_text(category),
                address=clean_text(address),
                subdistrict=clean_text(subdistrict),
                district=clean_text(district),
                city=clean_text(city),
                province=clean_text(province),
                zip_code=clean_text(zip_code),
                latitude=latitude,
                longitude=longitude,
                rating=rating,
                reviews_count=reviews_count,
                phone=clean_text(phone),
                website=clean_text(website),
                google_maps_link=link,
                opening_hours=clean_text(opening_hours),
                star_1=stars.get(1),
                star_2=stars.get(2),
                star_3=stars.get(3),
                star_4=stars.get(4),
                star_5=stars.get(5),
                search_keyword=task.keyword,
                search_location=task.location
            )
            
            return place
            
        except Exception as e:
            print(f"❌ Extract error: {e}")
            return None
    
    def _extract_text(self, selector: str) -> Optional[str]:
        """Extract text trying multiple selectors"""
        selectors = [s.strip() for s in selector.split(',')]
        
        for sel in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, sel)
                text = element.text
                if text and text.strip():
                    return text.strip()
            except:
                continue
        
        return None
    
    def _extract_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Extract attribute from element"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute)
        except:
            return None
    
    def _extract_opening_hours(self) -> Optional[str]:
        """Extract opening hours"""
        try:
            hours = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="oh"]')
            return hours.text
        except:
            return None
    
    def _extract_star_distribution(self) -> dict:
        """Extract star distribution"""
        stars = {1: None, 2: None, 3: None, 4: None, 5: None}
        
        try:
            bars = self.driver.find_elements(By.CSS_SELECTOR, 'tr.BHOKXe')
            
            for idx, bar in enumerate(bars[:5]):
                try:
                    import re
                    match = re.search(r'(\d+)', bar.text)
                    if match:
                        stars[5 - idx] = int(match.group(1))
                except:
                    continue
                    
        except:
            pass
        
        return stars
    
    def _is_valid_place(self, place: Place) -> bool:
        """Check if place is valid"""
        return (
            place.name is not None and 
            place.google_maps_link is not None and
            len(place.name) > 0
        )