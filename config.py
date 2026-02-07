import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings"""
    
    # Browser settings
    HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'
    
    # Timing
    PAGE_LOAD_TIMEOUT = 30000  # milliseconds
    SCREENSHOT_DELAY = 1  # seconds to wait before screenshot
    
    # Output
    OUTPUT_DIR = 'output'
    IMAGES_DIR = 'images'
    
    # Image settings
    SCREENSHOT_QUALITY = 90  # JPEG quality
    MAX_IMAGE_WIDTH = 1920
    MAX_IMAGE_HEIGHT = 1080
    
    # Description
    DESCRIPTION_WORD_COUNT = 30
    
    # User agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
