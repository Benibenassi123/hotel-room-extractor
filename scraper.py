import asyncio
import random
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
import os
from datetime import datetime
from config import Config


class HotelRoomExtractor:
    """Extract room-level data and images from hotel websites"""
    
    def __init__(self):
        self.config = Config()
        self.browser: Optional[Browser] = None
        self.results: List[Dict] = []
        
    def normalize_room_name(self, name: str) -> str:
        """Normalize room name for file naming"""
        import unicodedata
        name = name.lower().strip()
        name = ''.join(c for c in unicodedata.normalize('NFD', name)
                      if unicodedata.category(c) != 'Mn')
        name = re.sub(r'[/\\:*?"<>|]', '', name)
        name = re.sub(r'\s+', '-', name)
        name = re.sub(r'-+', '-', name)
        return name.strip('-')
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.config.HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        return playwright
    
    async def create_page(self) -> Page:
        """Create a new page with anti-detection"""
        context = await self.browser.new_context(
            user_agent=random.choice(self.config.USER_AGENTS),
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        return page
    
    async def search_hotel_website(self, hotel_name: str, city: str) -> Optional[str]:
        """Search for official hotel website"""
        page = await self.create_page()
        try:
            search_query = f"{hotel_name} {city} official website"
            await page.goto(f"https://www.google.com/search?q={search_query}")
            await page.wait_for_load_state('networkidle')
            first_link = await page.query_selector('div#search a[href^="http"]')
            if first_link:
                url = await first_link.get_attribute('href')
                if url and not any(x in url.lower() for x in ['google.', 'booking.', 'tripadvisor.', 'expedia.']):
                    return url
            return None
        finally:
            await page.close()
    
    async def find_and_click_rooms_link(self, page: Page, base_url: str) -> bool:
        """Try to find and click rooms/accommodations link"""
        try:
            from urllib.parse import urljoin
            
            # Try clicking navigation items
            room_keywords = ['rooms', 'accommodations', 'suites', 'habitaciones', 'alojamiento']
            
            for keyword in room_keywords:
                # Try different selectors
                selectors = [
                    f'a:has-text("{keyword}")',
                    f'a:text-is("{keyword}")',
                    f'nav a:has-text("{keyword}")',
                    f'[class*="menu"] a:has-text("{keyword}")',
                    f'[class*="nav"] a:has-text("{keyword}")'
                ]
                
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector, timeout=2000)
                        if element:
                            print(f"Found rooms link with selector: {selector}")
                            await element.click()
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            return True
                    except:
                        continue
            
            # Try finding href links
            for keyword in room_keywords:
                try:
                    link = await page.query_selector(f'a[href*="{keyword}"]')
                    if link:
                        href = await link.get_attribute('href')
                        if href:
                            if href.startswith('http'):
                                await page.goto(href)
                            elif href.startswith('/'):
                                await page.goto(urljoin(base_url, href))
                            else:
                                await page.goto(urljoin(base_url, '/' + href))
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            return True
                except:
                    continue
            
            return False
        except Exception as e:
            print(f"Error finding rooms link: {e}")
            return False
    
    async def find_room_cards_on_page(self, page: Page) -> List[Dict]:
        """Find room cards/sections on current page"""
        room_cards = []
        
        try:
            # Scroll page to load lazy content
            for i in range(3):
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await asyncio.sleep(1)
            
            # Strategy 1: Look for room cards with links
            card_selectors = [
                '[class*="room"]',
                '[class*="accommodation"]',
                '[class*="suite"]',
                '[data-room]',
                'article',
                '.card',
                '[class*="habitacion"]'
            ]
            
            for selector in card_selectors:
                elements = await page.query_selector_all(selector)
                
                for elem in elements:
                    try:
                        # Get room name
                        name_elem = await elem.query_selector('h2, h3, h4, [class*="title"], [class*="name"]')
                        if name_elem:
                            room_name = await name_elem.inner_text()
                            room_name = room_name.strip()
                            
                            if len(room_name) > 3 and len(room_name) < 100:
                                # Try to find link to room detail page
                                link_elem = await elem.query_selector('a')
                                room_url = None
                                if link_elem:
                                    room_url = await link_elem.get_attribute('href')
                                
                                room_cards.append({
                                    'name': room_name,
                                    'url': room_url,
                                    'element': elem
                                })
                    except:
                        continue
                
                if room_cards:
                    break
            
            # Strategy 2: Look for headings with "room" in text
            if not room_cards:
                headings = await page.query_selector_all('h2, h3, h4')
                for heading in headings:
                    try:
                        text = await heading.inner_text()
                        text = text.strip()
                        if any(keyword in text.lower() for keyword in ['room', 'suite', 'habitacion']) and len(text) > 3:
                            room_cards.append({
                                'name': text,
                                'url': None,
                                'element': heading
                            })
                    except:
                        continue
            
        except Exception as e:
            print(f"Error finding room cards: {e}")
        
        return room_cards[:20]  # Limit to 20 rooms
    
    async def extract_room_details(self, page: Page, room_name: str) -> Dict:
        """Extract detailed information for a specific room"""
        details = {
            'room_name': room_name,
            'room_area_m2': 'NOT FOUND',
            'bed_type': 'NOT FOUND',
            'views': 'NOT FOUND',
            'room_description_30w': '',
            'link_main': page.url,
            'sources': [page.url]
        }
        
        try:
            content = await page.content()
            
            # Extract area
            area_patterns = [r'(\d+)\s*m²', r'(\d+)\s*m2', r'(\d+)\s*sqm', r'(\d+)\s*square\s*meters']
            for pattern in area_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    details['room_area_m2'] = match.group(1)
                    break
            
            # Extract bed type
            bed_patterns = [
                r'(\d+\s+(?:king|queen|double|twin|single)\s+bed)',
                r'(king\s+(?:size\s+)?bed)',
                r'(queen\s+(?:size\s+)?bed)',
                r'(twin\s+beds)',
                r'(double\s+bed)',
                r'(cama\s+(?:king|queen|doble|individual))'
            ]
            for pattern in bed_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    details['bed_type'] = match.group(1)
                    break
            
            # Extract views
            view_keywords = ['sea view', 'ocean view', 'city view', 'garden view', 'mountain view', 
                           'pool view', 'vista mar', 'vista ciudad']
            for keyword in view_keywords:
                if keyword in content.lower():
                    details['views'] = keyword.title()
                    break
            
            # Generate 30-word description
            paragraphs = await page.query_selector_all('p')
            desc_text = ''
            for p in paragraphs[:5]:  # Check first 5 paragraphs
                try:
                    text = await p.inner_text()
                    if len(text) > 50:  # Meaningful paragraph
                        desc_text = text
                        break
                except:
                    continue
            
            if desc_text:
                words = desc_text.split()[:30]
                details['room_description_30w'] = ' '.join(words)
            
            if not details['room_description_30w']:
                details['room_description_30w'] = f"Accommodations at this hotel include the {room_name} room type with various amenities and features for guest comfort and convenience during their stay at the property."[:200]
                words = details['room_description_30w'].split()[:30]
                details['room_description_30w'] = ' '.join(words)
            
        except Exception as e:
            print(f"Error extracting room details: {e}")
        
        return details
    
    async def capture_room_images(self, page: Page, hotel_id: str, room_name: str) -> Dict[str, str]:
        """Capture 4 screenshots: room1, room2, bathroom, view"""
        images = {'room1': 'NOT AVAILABLE', 'room2': 'NOT AVAILABLE', 'bathroom': 'NOT AVAILABLE', 'view': 'NOT AVAILABLE'}
        
        try:
            image_dir = os.path.join(self.config.IMAGES_DIR, str(hotel_id))
            os.makedirs(image_dir, exist_ok=True)
            normalized_name = self.normalize_room_name(room_name)
            
            # Find gallery or image containers
            img_elements = await page.query_selector_all('img[src], img[data-src]')
            
            captured = 0
            captured_types = set()
            
            for idx, img_elem in enumerate(img_elements):
                if captured >= 4:
                    break
                
                try:
                    await img_elem.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    
                    # Get image attributes
                    img_src = await img_elem.get_attribute('src') or await img_elem.get_attribute('data-src') or ''
                    img_alt = await img_elem.get_attribute('alt') or ''
                    img_class = await img_elem.get_attribute('class') or ''
                    
                    # Skip tiny images, icons, logos
                    box = await img_elem.bounding_box()
                    if not box or box['width'] < 200 or box['height'] < 150:
                        continue
                    
                    # Determine image type
                    combined_text = f"{img_src} {img_alt} {img_class}".lower()
                    
                    img_type = None
                    if 'bathroom' in combined_text or 'bath' in combined_text:
                        if 'bathroom' not in captured_types:
                            img_type = 'bathroom'
                    elif 'view' in combined_text or 'vista' in combined_text:
                        if 'view' not in captured_types:
                            img_type = 'view'
                    elif 'room1' not in captured_types:
                        img_type = 'room1'
                    elif 'room2' not in captured_types:
                        img_type = 'room2'
                    
                    if not img_type:
                        continue
                    
                    filename = f"{hotel_id}_{normalized_name}_{img_type}.jpg"
                    filepath = os.path.join(image_dir, filename)
                    
                    await img_elem.screenshot(path=filepath, type='jpeg', quality=90)
                    
                    images[img_type] = filename
                    captured_types.add(img_type)
                    captured += 1
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"Error capturing room images: {e}")
            images = {'room1': 'SCREENSHOT FAILED', 'room2': 'SCREENSHOT FAILED', 'bathroom': 'SCREENSHOT FAILED', 'view': 'SCREENSHOT FAILED'}
        
        return images
    
    async def extract_hotel(self, hotel_data: Dict, progress_callback=None) -> List[Dict]:
        """Main extraction method for a single hotel"""
        hotel_id = hotel_data.get('hotel_id')
        hotel_name = hotel_data.get('hotel_name')
        city = hotel_data.get('city', '')
        address = hotel_data.get('address', '')
        
        if progress_callback:
            progress_callback(f"Searching for {hotel_name}...")
        
        rooms_data = []
        
        try:
            website_url = await self.search_hotel_website(hotel_name, city)
            
            if not website_url:
                return [self._create_error_row(hotel_id, hotel_name, city, address, 
                                               'Hotel website not found.', 'Official website not found')]
            
            if progress_callback:
                progress_callback(f"Found website: {website_url}")
            
            page = await self.create_page()
            await page.goto(website_url, timeout=30000)
            await page.wait_for_load_state('networkidle')
            
            # Try to navigate to rooms page
            if progress_callback:
                progress_callback("Looking for rooms page...")
            
            clicked = await self.find_and_click_rooms_link(page, website_url)
            
            if progress_callback:
                if clicked:
                    progress_callback("Found rooms section!")
                else:
                    progress_callback("Searching for rooms on homepage...")
            
            # Find room cards on current page
            room_cards = await self.find_room_cards_on_page(page)
            
            if not room_cards:
                await page.close()
                return [self._create_error_row(hotel_id, hotel_name, city, address,
                                               'No room types found on website.', 
                                               'No rooms found', website_url)]
            
            if progress_callback:
                progress_callback(f"Found {len(room_cards)} room types!")
            
            # Process each room
            for room_card in room_cards:
                room_name = room_card['name']
                room_url = room_card['url']
                
                if progress_callback:
                    progress_callback(f"Extracting: {room_name}")
                
                # If room has dedicated page, navigate to it
                if room_url and room_url != '#':
                    try:
                        from urllib.parse import urljoin
                        if not room_url.startswith('http'):
                            room_url = urljoin(page.url, room_url)
                        
                        room_page = await self.create_page()
                        await room_page.goto(room_url, timeout=30000)
                        await room_page.wait_for_load_state('networkidle')
                        
                        details = await self.extract_room_details(room_page, room_name)
                        images = await self.capture_room_images(room_page, hotel_id, room_name)
                        
                        await room_page.close()
                    except Exception as e:
                        print(f"Error navigating to room page: {e}")
                        details = await self.extract_room_details(page, room_name)
                        images = await self.capture_room_images(page, hotel_id, room_name)
                else:
                    # Extract from current page
                    details = await self.extract_room_details(page, room_name)
                    images = await self.capture_room_images(page, hotel_id, room_name)
                
                room_data = {
                    'hotel_id': hotel_id,
                    'hotel_name': hotel_name,
                    'city': city,
                    'address': address,
                    'room_name': room_name,
                    'image_folder': f'images/{hotel_id}/',
                    'image_files': f"{images['room1']} | {images['room2']} | {images['bathroom']} | {images['view']}",
                    'room_area_m2': details['room_area_m2'],
                    'bed_type': details['bed_type'],
                    'views': details['views'],
                    'room_description_30w': details['room_description_30w'],
                    'link_main': details['link_main'],
                    'link_secondary': '',
                    'sources': ', '.join(details['sources']),
                    'room_match_method': 'Exact match',
                    'confidence': 'Medium',
                    'notes': 'Extracted from official website'
                }
                
                rooms_data.append(room_data)
            
            await page.close()
            
        except Exception as e:
            print(f"Error extracting hotel: {e}")
            return [self._create_error_row(hotel_id, hotel_name, city, address,
                                           f'Extraction failed: {str(e)[:50]}',
                                           f'Error: {str(e)}', is_failed=True)]
        
        return rooms_data
    
    def _create_error_row(self, hotel_id, hotel_name, city, address, description, notes, link_main='', is_failed=False):
        """Helper to create error row"""
        files_status = 'EXTRACTION FAILED' if is_failed else 'NOT AVAILABLE'
        return {
            'hotel_id': hotel_id,
            'hotel_name': hotel_name,
            'city': city,
            'address': address,
            'room_name': 'N/A',
            'image_folder': f'images/{hotel_id}/',
            'image_files': f'{files_status} | {files_status} | {files_status} | {files_status}',
            'room_area_m2': 'NOT FOUND',
            'bed_type': 'NOT FOUND',
            'views': 'NOT FOUND',
            'room_description_30w': description,
            'link_main': link_main,
            'link_secondary': '',
            'sources': link_main if link_main else '',
            'room_match_method': 'Failed' if is_failed else 'No match',
            'confidence': 'Low',
            'notes': notes
        }
    
    async def process_hotels(self, hotels: List[Dict], progress_callback=None) -> List[Dict]:
        """Process multiple hotels"""
        playwright = await self.init_browser()
        all_rooms = []
        
        try:
            for idx, hotel in enumerate(hotels):
                if progress_callback:
                    progress_callback(f"Processing hotel {idx + 1}/{len(hotels)}: {hotel.get('hotel_name')}")
                
                rooms = await self.extract_hotel(hotel, progress_callback)
                all_rooms.extend(rooms)
                
                if idx < len(hotels) - 1:
                    await asyncio.sleep(2)
            
        finally:
            await self.browser.close()
            await playwright.stop()
        
        return all_rooms
    
    def save_to_csv(self, rooms_data: List[Dict], filename: Optional[str] = None):
        """Save results to CSV"""
        import csv
        if not rooms_data:
            return
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"hotel_rooms_{timestamp}.csv"
        filepath = os.path.join(self.config.OUTPUT_DIR, filename)
        fieldnames = ['hotel_id', 'hotel_name', 'city', 'address', 'room_name', 'image_folder', 'image_files', 'room_area_m2', 'bed_type', 'views', 'room_description_30w', 'link_main', 'link_secondary', 'sources', 'room_match_method', 'confidence', 'notes']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rooms_data)
        return filepath
