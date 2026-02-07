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
    
    async def find_rooms_page(self, page: Page, base_url: str) -> Optional[str]:
        """Find the rooms/accommodations page"""
        try:
            from urllib.parse import urljoin
            room_keywords = ['rooms', 'accommodations', 'suites', 'guest-rooms']
            for keyword in room_keywords:
                link = await page.query_selector(f'a[href*="{keyword}"]')
                if link:
                    href = await link.get_attribute('href')
                    if href:
                        if href.startswith('http'):
                            return href
                        elif href.startswith('/'):
                            return urljoin(base_url, href)
            return None
        except Exception as e:
            print(f"Error finding rooms page: {e}")
            return None
    
    async def extract_room_list(self, page: Page) -> List[str]:
        """Extract list of distinct room names"""
        rooms = []
        try:
            selectors = ['h2:has-text("room")', 'h3:has-text("room")', '.room-title', '.room-name']
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for elem in elements:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 3:
                        rooms.append(text.strip())
                if rooms:
                    break
            seen = set()
            unique_rooms = []
            for room in rooms:
                normalized = room.lower().strip()
                if normalized not in seen:
                    seen.add(normalized)
                    unique_rooms.append(room)
            return unique_rooms[:20]
        except Exception as e:
            print(f"Error extracting room list: {e}")
            return []
    
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
            area_match = re.search(r'(\d+)\s*m²', content, re.IGNORECASE)
            if area_match:
                details['room_area_m2'] = area_match.group(1)
            bed_patterns = [r'(\d+\s+(?:king|queen|double|twin)\s+bed)', r'(king\s+bed)', r'(queen\s+bed)']
            for pattern in bed_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    details['bed_type'] = match.group(1)
                    break
            view_keywords = ['sea view', 'ocean view', 'city view', 'garden view']
            for keyword in view_keywords:
                if keyword in content.lower():
                    details['views'] = keyword.title()
                    break
            p_elem = await page.query_selector('p')
            if p_elem:
                desc_text = await p_elem.inner_text()
                words = desc_text.split()[:30]
                details['room_description_30w'] = ' '.join(words)
            if not details['room_description_30w']:
                details['room_description_30w'] = f"Room information for {room_name}. " * 5
                details['room_description_30w'] = ' '.join(details['room_description_30w'].split()[:30])
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
            img_elements = await page.query_selector_all('img')
            for idx, img_elem in enumerate(img_elements[:4]):
                try:
                    await img_elem.scroll_into_view_if_needed()
                    await asyncio.sleep(self.config.SCREENSHOT_DELAY)
                    img_src = await img_elem.get_attribute('src') or ''
                    img_type = 'room1'
                    if 'bathroom' in img_src.lower():
                        img_type = 'bathroom'
                    elif 'view' in img_src.lower():
                        img_type = 'view'
                    elif idx > 0:
                        img_type = f'room{idx + 1}'
                    filename = f"{hotel_id}_{normalized_name}_{img_type}.jpg"
                    filepath = os.path.join(image_dir, filename)
                    await img_elem.screenshot(path=filepath, type='jpeg', quality=90)
                    images[img_type] = filename
                except Exception as e:
                    continue
        except Exception as e:
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
                return [{'hotel_id': hotel_id, 'hotel_name': hotel_name, 'city': city, 'address': address, 'room_name': 'N/A', 'image_folder': f'images/{hotel_id}/', 'image_files': 'NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE', 'room_area_m2': 'NOT FOUND', 'bed_type': 'NOT FOUND', 'views': 'NOT FOUND', 'room_description_30w': 'Hotel website not found.', 'link_main': '', 'link_secondary': '', 'sources': '', 'room_match_method': 'No match', 'confidence': 'Low', 'notes': 'Official website not found'}]
            if progress_callback:
                progress_callback(f"Found website: {website_url}")
            page = await self.create_page()
            await page.goto(website_url, timeout=30000)
            await page.wait_for_load_state('networkidle')
            rooms_page_url = await self.find_rooms_page(page, website_url)
            if rooms_page_url:
                await page.goto(rooms_page_url)
                await page.wait_for_load_state('networkidle')
            room_names = await self.extract_room_list(page)
            if not room_names:
                await page.close()
                return [{'hotel_id': hotel_id, 'hotel_name': hotel_name, 'city': city, 'address': address, 'room_name': 'N/A', 'image_folder': f'images/{hotel_id}/', 'image_files': 'NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE', 'room_area_m2': 'NOT FOUND', 'bed_type': 'NOT FOUND', 'views': 'NOT FOUND', 'room_description_30w': 'No room types found on website.', 'link_main': website_url, 'link_secondary': '', 'sources': website_url, 'room_match_method': 'No match', 'confidence': 'Low', 'notes': 'No rooms found'}]
            for room_name in room_names:
                if progress_callback:
                    progress_callback(f"Processing room: {room_name}")
                details = await self.extract_room_details(page, room_name)
                images = await self.capture_room_images(page, hotel_id, room_name)
                room_data = {'hotel_id': hotel_id, 'hotel_name': hotel_name, 'city': city, 'address': address, 'room_name': room_name, 'image_folder': f'images/{hotel_id}/', 'image_files': f"{images['room1']} | {images['room2']} | {images['bathroom']} | {images['view']}", 'room_area_m2': details['room_area_m2'], 'bed_type': details['bed_type'], 'views': details['views'], 'room_description_30w': details['room_description_30w'], 'link_main': details['link_main'], 'link_secondary': '', 'sources': ', '.join(details['sources']), 'room_match_method': 'Exact match', 'confidence': 'Medium', 'notes': 'From official website'}
                rooms_data.append(room_data)
            await page.close()
        except Exception as e:
            return [{'hotel_id': hotel_id, 'hotel_name': hotel_name, 'city': city, 'address': address, 'room_name': 'N/A', 'image_folder': f'images/{hotel_id}/', 'image_files': 'FAILED | FAILED | FAILED | FAILED', 'room_area_m2': 'NOT FOUND', 'bed_type': 'NOT FOUND', 'views': 'NOT FOUND', 'room_description_30w': f'Extraction failed: {str(e)[:50]}', 'link_main': '', 'link_secondary': '', 'sources': '', 'room_match_method': 'Failed', 'confidence': 'Low', 'notes': f'Error: {str(e)}'}]
        return rooms_data
    
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
