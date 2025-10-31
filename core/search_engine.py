"""
Search engine for Google Maps
"""
import re
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
            
            # Extract rating - try multiple methods
            rating = None
            rating_text = None
            
            # Method 1: Get from parent container (gets full "4.5" text)
            try:
                rating_container = self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice')
                full_text = rating_container.text
                # Extract rating from text like "4.5" or "4.5 (123 reviews)"
                match = re.search(r'(\d+[.,]\d+)', full_text)
                if match:
                    rating_text = match.group(1).replace(',', '.')
            except:
                pass
            
            # Method 2: Standard selectors (fallback)
            if not rating_text:
                rating_text = self._extract_text('div.F7nice span[aria-hidden="true"], span.ceNzKf[aria-hidden="true"]')
            
            # Method 3: Try aria-label on button
            if not rating_text:
                try:
                    rating_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="stars"], button[aria-label*="rating"]')
                    aria = rating_button.get_attribute('aria-label')
                    if aria:
                        match = re.search(r'(\d+[.,]\d+)', aria)
                        if match:
                            rating_text = match.group(1).replace(',', '.')
                except:
                    pass
            
            # Method 4: Look for any element with rating pattern
            if not rating_text:
                try:
                    # Search all text on page for rating pattern near reviews
                    all_text = self.driver.find_element(By.CSS_SELECTOR, 'div.m6QErb').text
                    # Pattern: number followed by reviews/stars
                    match = re.search(r'(\d+[.,]\d+)\s*(?:\(|stars|reviews)', all_text, re.IGNORECASE)
                    if match:
                        rating_text = match.group(1).replace(',', '.')
                except:
                    pass
            
            rating = parse_rating(rating_text)
            print(f"    📍 Rating text: '{rating_text}' → Parsed: {rating}")
            
            # Extract reviews - must get from individual place details, not search results
            reviews_count = None
            reviews_text = None
            
            # Method 1: Get from rating container (most specific)
            try:
                rating_section = self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice')
                reviews_elem = rating_section.find_element(By.CSS_SELECTOR, 'span[aria-label*="reviews"], button[aria-label*="reviews"]')
                reviews_text = reviews_elem.get_attribute('aria-label')
                if not reviews_text:
                    reviews_text = reviews_elem.text
                print(f"    🔍 Method 1 (rating section): '{reviews_text}'")
            except Exception as e:
                print(f"    ⚠️  Method 1 failed: {e}")
            
            # Method 2: Try to find review count in rating section text
            if not reviews_text:
                try:
                    rating_section = self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice')
                    full_text = rating_section.text
                    print(f"    🔍 Method 2 (section text): '{full_text}'")
                    # Pattern: "(123)" or "(1,234)" or "(1.234)" after rating
                    match = re.search(r'\(([0-9.,\s]+)\)', full_text)
                    if match:
                        reviews_text = match.group(1)
                        print(f"    ✓ Extracted from pattern: '{reviews_text}'")
                except Exception as e:
                    print(f"    ⚠️  Method 2 failed: {e}")
            
            # Method 3: Look for any button with review count
            if not reviews_text:
                try:
                    review_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[jsaction*="reviews"], button.HHrUdb, button[aria-label*="review"]')
                    print(f"    🔍 Method 3: Found {len(review_buttons)} review buttons")
                    for idx, btn in enumerate(review_buttons):
                        text = btn.text
                        aria = btn.get_attribute('aria-label')
                        print(f"      Button {idx}: text='{text}', aria='{aria}'")
                        
                        # Check aria-label first
                        if aria and 'review' in aria.lower():
                            match = re.search(r'([0-9.,\s]+)', aria)
                            if match:
                                reviews_text = match.group(1)
                                print(f"    ✓ Got from button aria: '{reviews_text}'")
                                break
                        
                        # Check button text
                        if text and 'review' in text.lower():
                            match = re.search(r'([0-9.,\s]+)', text)
                            if match:
                                reviews_text = match.group(1)
                                print(f"    ✓ Got from button text: '{reviews_text}'")
                                break
                except Exception as e:
                    print(f"    ⚠️  Method 3 failed: {e}")
            
            # Method 4: Search in details panel (first few lines only)
            if not reviews_text:
                try:
                    details_panel = self.driver.find_element(By.CSS_SELECTOR, 'div.m6QErb[aria-label]')
                    lines = details_panel.text.split('\n')[0:10]
                    print(f"    🔍 Method 4: Searching in {len(lines)} lines")
                    for idx, line in enumerate(lines):
                        # Look for line with just rating and reviews: "4.5 (123)"
                        match = re.search(r'(\d+[.,]\d+).*?\(([0-9.,\s]+)\)', line)
                        if match:
                            reviews_text = match.group(2)
                            print(f"    ✓ Found in line {idx}: '{line}' → '{reviews_text}'")
                            break
                except Exception as e:
                    print(f"    ⚠️  Method 4 failed: {e}")
            
            # Method 5: Look for review text/link directly
            if not reviews_text:
                try:
                    # Sometimes reviews are in a link or span with specific text
                    review_elements = self.driver.find_elements(By.XPATH, 
                        "//*[contains(text(), 'review') or contains(text(), 'Review')]")
                    print(f"    🔍 Method 5: Found {len(review_elements)} elements with 'review'")
                    for idx, elem in enumerate(review_elements[:5]):  # Check first 5
                        text = elem.text
                        print(f"      Element {idx}: '{text}'")
                        match = re.search(r'([0-9.,\s]+)\s*review', text, re.IGNORECASE)
                        if match:
                            reviews_text = match.group(1)
                            print(f"    ✓ Got from element: '{reviews_text}'")
                            break
                except Exception as e:
                    print(f"    ⚠️  Method 5 failed: {e}")
            
            # Method 6: Get from page source as last resort
            if not reviews_text:
                try:
                    page_source = self.driver.page_source
                    # Look for common review patterns in HTML
                    patterns = [
                        r'aria-label="([0-9.,\s]+)\s*reviews?"',
                        r'"reviews?["\s:]+([0-9.,\s]+)',
                        r'reviewCount["\s:]+([0-9.,\s]+)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, page_source, re.IGNORECASE)
                        if match:
                            reviews_text = match.group(1)
                            print(f"    ✓ Found in source with pattern '{pattern}': '{reviews_text}'")
                            break
                except Exception as e:
                    print(f"    ⚠️  Method 6 failed: {e}")
            
            reviews_count = parse_reviews_count(reviews_text)
            print(f"    📍 Reviews FINAL: '{reviews_text}' → Parsed: {reviews_count}")
            
            if not reviews_count:
                print(f"    ❌ WARNING: Could not extract review count!")
            
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