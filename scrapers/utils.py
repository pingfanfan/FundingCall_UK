#!/usr/bin/env python3
"""
Utility functions for web scraping funding opportunities.

This module provides common functionality for all scrapers including:
- HTTP requests with retry logic
- Data validation and cleaning
- JSON file operations
- Date parsing and formatting
- Logging configuration
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger
from ratelimit import limits, sleep_and_retry

# Configure logging
logger.add("scrapers.log", rotation="1 week", retention="1 month", level="INFO")

class ScrapingError(Exception):
    """Custom exception for scraping errors."""
    pass

class FundingScraper:
    """Base class for funding opportunity scrapers."""
    
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    @sleep_and_retry
    @limits(calls=10, period=60)  # Rate limit: 10 calls per minute
    def fetch_page(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """Fetch a web page with rate limiting and error handling."""        
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise ScrapingError(f"Failed to fetch {url}: {e}")
    
    def extract_text(self, element, default: str = "") -> str:
        """Safely extract text from a BeautifulSoup element."""
        if element:
            return element.get_text(strip=True)
        return default

    def fetch_page_with_selenium(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """Fetch a web page using Selenium for dynamic content."""
        try:
            logger.info(f"Fetching with Selenium: {url}")
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get(url)
            time.sleep(5)  # Wait for dynamic content to load
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()
            
            return soup
            
        except Exception as e:
            logger.error(f"Failed to fetch {url} with Selenium: {e}")
            raise ScrapingError(f"Failed to fetch {url} with Selenium: {e}")
    
    def extract_amount(self, text: str) -> Dict[str, Any]:
        """Extract funding amount from text."""
        # Common patterns for UK funding amounts
        patterns = [
            r'£([\d,]+)(?:\s*-\s*£([\d,]+))?',  # £100,000 or £100,000 - £500,000
            r'([\d,]+)(?:\s*-\s*([\d,]+))?\s*(?:thousand|k)',  # 100k or 100-500k
            r'([\d,]+)(?:\s*-\s*([\d,]+))?\s*(?:million|m)',  # 1m or 1-5m
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                min_amount = self._parse_amount(match.group(1))
                max_amount = self._parse_amount(match.group(2)) if match.group(2) else min_amount
                
                # Handle k/m suffixes
                if 'thousand' in text.lower() or 'k' in text.lower():
                    min_amount *= 1000
                    max_amount *= 1000
                elif 'million' in text.lower() or 'm' in text.lower():
                    min_amount *= 1000000
                    max_amount *= 1000000
                
                return {
                    'min': min_amount,
                    'max': max_amount,
                    'currency': 'GBP'
                }
        
        return {'min': 0, 'max': 0, 'currency': 'GBP'}
    
    def _parse_amount(self, amount_str: str) -> int:
        """Parse amount string to integer."""
        if not amount_str:
            return 0
        return int(re.sub(r'[^\d]', '', amount_str))
    
    def extract_deadline(self, text: str) -> Optional[str]:
        """Extract deadline from text and return ISO format date."""
        # Common date patterns
        patterns = [
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if pattern == patterns[0]:  # Month name format
                            day, month_name, year = match.groups()
                            month_map = {
                                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                                'september': 9, 'october': 10, 'november': 11, 'december': 12
                            }
                            month = month_map.get(month_name.lower(), 1)
                            date_obj = datetime(int(year), month, int(day))
                        elif pattern == patterns[1]:  # DD/MM/YYYY
                            day, month, year = match.groups()
                            date_obj = datetime(int(year), int(month), int(day))
                        else:  # YYYY-MM-DD
                            year, month, day = match.groups()
                            date_obj = datetime(int(year), int(month), int(day))
                        
                        return date_obj.isoformat().split('T')[0]
                except ValueError:
                    continue
        
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        return text
    
    def generate_id(self, title: str, organization: str) -> str:
        """Generate a unique ID for a funding opportunity based on its content."""
        # Create a slug from title and organization
        combined = f"{organization}_{title}"
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', combined.lower())
        slug = re.sub(r'_+', '_', slug).strip('_')
        
        # Use a hash of the combined string to ensure uniqueness based on content
        import hashlib
        content_hash = hashlib.md5(combined.encode()).hexdigest()
        return f"{slug}_{content_hash}"

def load_json(file_path: Path) -> Dict:
    """Load JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return {}

def save_json(data: Dict, file_path: Path) -> bool:
    """Save data to JSON file."""
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved data to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save {file_path}: {e}")
        return False

def validate_funding_data(funding: Dict) -> bool:
    """Validate funding data structure."""
    required_fields = [
        'id', 'title', 'organization', 'category', 'description',
        'eligibility', 'funding_details', 'application'
    ]
    
    for field in required_fields:
        if field not in funding:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Validate nested structures
    if 'amount' not in funding['funding_details']:
        logger.error("Missing funding amount")
        return False
    
    if 'deadline' not in funding['application']:
        logger.error("Missing application deadline")
        return False
    
    return True

def update_database(new_fundings: List[Dict], database_path: Path) -> bool:
    """Update the main funding database with new entries."""
    try:
        # Load existing database
        database = load_json(database_path)
        
        if not database:
            database = {
                'last_updated': datetime.now().isoformat(),
                'total_fundings': 0,
                'fundings': []
            }
        
        existing_ids = {f['id'] for f in database.get('fundings', [])}
        
        # Add new fundings (avoid duplicates)
        new_count = 0
        for funding in new_fundings:
            if validate_funding_data(funding) and funding['id'] not in existing_ids:
                database['fundings'].append(funding)
                new_count += 1
        
        # Update metadata
        database['last_updated'] = datetime.now().isoformat()
        database['total_fundings'] = len(database['fundings'])
        
        # Save updated database
        if save_json(database, database_path):
            logger.info(f"Added {new_count} new funding opportunities to database")
            return True
        
    except Exception as e:
        logger.error(f"Failed to update database: {e}")
    
    return False

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent

def setup_directories() -> Dict[str, Path]:
    """Setup and return project directory paths."""
    root = get_project_root()
    
    dirs = {
        'root': root,
        'data': root / 'data',
        'individual_fundings': root / 'data' / 'individual_fundings',
        'scrapers': root / 'scrapers',
        'logs': root / 'logs'
    }
    
    # Create directories if they don't exist
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs

if __name__ == "__main__":
    # Test the utility functions
    dirs = setup_directories()
    print(f"Project directories: {dirs}")
    
    # Test amount extraction
    scraper = FundingScraper("https://example.com", "test")
    test_amounts = [
        "£100,000 - £500,000",
        "Up to £1.5 million",
        "500k funding available",
        "Between 50-200 thousand pounds"
    ]
    
    for amount_text in test_amounts:
        result = scraper.extract_amount(amount_text)
        print(f"{amount_text} -> {result}")