#!/usr/bin/env python3
"""
UKRI (UK Research and Innovation) Funding Scraper

This scraper collects funding opportunities from UKRI and its constituent councils:
- Arts and Humanities Research Council (AHRC)
- Biotechnology and Biological Sciences Research Council (BBSRC)
- Economic and Social Research Council (ESRC)
- Engineering and Physical Sciences Research Council (EPSRC)
- Medical Research Council (MRC)
- Natural Environment Research Council (NERC)
- Science and Technology Facilities Council (STFC)
- Innovate UK
- Research England
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from loguru import logger

from utils import FundingScraper, save_json, setup_directories, update_database

class UKRIScraper(FundingScraper):
    """Scraper for UKRI funding opportunities."""
    
    def __init__(self):
        super().__init__("https://www.ukri.org", "UKRI")
        
        # Set base_urls for compatibility with tests
        self.base_urls = ["https://www.ukri.org"]
        
        # UKRI council mappings
        self.councils = {
            'ahrc': {
                'name': 'Arts and Humanities Research Council',
                'url': 'https://www.ukri.org/councils/ahrc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=ahrc'
            },
            'bbsrc': {
                'name': 'Biotechnology and Biological Sciences Research Council',
                'url': 'https://www.ukri.org/councils/bbsrc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=bbsrc'
            },
            'esrc': {
                'name': 'Economic and Social Research Council',
                'url': 'https://www.ukri.org/councils/esrc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=esrc'
            },
            'epsrc': {
                'name': 'Engineering and Physical Sciences Research Council',
                'url': 'https://www.ukri.org/councils/epsrc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=epsrc'
            },
            'mrc': {
                'name': 'Medical Research Council',
                'url': 'https://www.ukri.org/councils/mrc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=mrc'
            },
            'nerc': {
                'name': 'Natural Environment Research Council',
                'url': 'https://www.ukri.org/councils/nerc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=nerc'
            },
            'stfc': {
                'name': 'Science and Technology Facilities Council',
                'url': 'https://www.ukri.org/councils/stfc/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=stfc'
            },
            'innovate_uk': {
                'name': 'Innovate UK',
                'url': 'https://www.ukri.org/councils/innovate-uk/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=innovate-uk'
            },
            'research_england': {
                'name': 'Research England',
                'url': 'https://www.ukri.org/councils/research-england/',
                'funding_url': 'https://www.ukri.org/opportunity/?filter_council=research-england'
            }
        }
    
    def scrape_all_councils(self) -> List[Dict]:
        """Scrape funding opportunities from all UKRI councils without duplicates."""
        all_fundings = []
        scraped_urls = set()  # Track scraped URLs to avoid duplicates
        
        logger.info("Scraping all UKRI opportunities...")
        
        # Scrape from main opportunities page first
        try:
            main_fundings = self.scrape_main_opportunities(scraped_urls)
            all_fundings.extend(main_fundings)
            logger.info(f"Found {len(main_fundings)} opportunities from main page")
        except Exception as e:
            logger.error(f"Failed to scrape main opportunities: {e}")
        
        # Then scrape each council's specific opportunities
        for council_id, council_info in self.councils.items():
            logger.info(f"Scraping {council_info['name']}...")
            try:
                council_fundings = self.scrape_council(council_id, scraped_urls)
                all_fundings.extend(council_fundings)
                logger.info(f"Found {len(council_fundings)} new opportunities from {council_info['name']}")
            except Exception as e:
                logger.error(f"Failed to scrape {council_info['name']}: {e}")
        
        return all_fundings
    
    def scrape_main_opportunities(self, scraped_urls: set) -> List[Dict]:
        """Scrape opportunities from the main UKRI opportunities page with pagination."""
        fundings = []
        base_url = "https://www.ukri.org/opportunity/"
        page = 1
        max_pages = 15  # Safety limit - UKRI has ~109 opportunities, so ~10 pages
        
        while page <= max_pages:
            try:
                # Construct URL with page parameter
                if page == 1:
                    url = base_url
                else:
                    # Use the /page/X/ format which works reliably
                    url = f"{base_url}page/{page}/"
                
                logger.info(f"Scraping UKRI opportunities page {page}: {url}")
                soup = self.fetch_page(url)
                
                # Check if we got a valid page (not 404)
                if not soup:
                    logger.info(f"Page {page} returned no content, stopping pagination")
                    break
                
                # Extract opportunity links from current page
                opportunity_links = self.extract_opportunity_links(soup)
                
                # If no links found, we've reached the end
                if not opportunity_links:
                    logger.info(f"No more opportunities found on page {page}, stopping pagination")
                    break
                
                new_links_found = 0
                for link in opportunity_links:
                    # Skip if already scraped
                    if link in scraped_urls:
                        continue
                        
                    scraped_urls.add(link)
                    new_links_found += 1
                    
                    try:
                        # Determine council from URL or page content
                        council_id = self.determine_council_from_url(link)
                        funding = self.scrape_opportunity_details(link, council_id)
                        if funding:
                            fundings.append(funding)
                    except Exception as e:
                        logger.error(f"Failed to scrape opportunity {link}: {e}")
                
                logger.info(f"Found {new_links_found} new opportunities on page {page} (total so far: {len(fundings)})")
                
                # If no new links were found, we might have reached the end
                if new_links_found == 0:
                    logger.info(f"No new opportunities found on page {page}, stopping pagination")
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to scrape opportunities page {page}: {e}")
                break
        
        logger.info(f"Completed scraping main opportunities. Total pages: {page-1}, Total opportunities: {len(fundings)}")
        return fundings
    
    def scrape_council(self, council_id: str, scraped_urls: set) -> List[Dict]:
        """Scrape funding opportunities from a specific council."""
        council_info = self.councils[council_id]
        fundings = []
        
        # Get the opportunities listing page
        soup = self.fetch_page(council_info['funding_url'])
        
        # Find opportunity links
        opportunity_links = self.extract_opportunity_links(soup)
        
        for link in opportunity_links:
            # Skip if already scraped
            if link in scraped_urls:
                continue
                
            scraped_urls.add(link)
            
            try:
                funding = self.scrape_opportunity_details(link, council_id)
                if funding:
                    fundings.append(funding)
            except Exception as e:
                logger.error(f"Failed to scrape opportunity {link}: {e}")
        
        return fundings
    
    def determine_council_from_url(self, url: str) -> str:
        """Determine which council an opportunity belongs to from URL or page content."""
        # Try to determine from URL patterns first
        url_lower = url.lower()
        
        # Check for council-specific keywords in URL
        council_keywords = {
            'ahrc': ['arts', 'humanities', 'ahrc'],
            'bbsrc': ['biotechnology', 'biological', 'bbsrc'],
            'esrc': ['economic', 'social', 'esrc'],
            'epsrc': ['engineering', 'physical', 'epsrc'],
            'mrc': ['medical', 'health', 'mrc'],
            'nerc': ['environment', 'natural', 'nerc'],
            'stfc': ['science', 'technology', 'facilities', 'stfc'],
            'innovate_uk': ['innovation', 'business', 'innovate'],
            'research_england': ['research-england']
        }
        
        for council_id, keywords in council_keywords.items():
            if any(keyword in url_lower for keyword in keywords):
                return council_id
        
        # Try to fetch page content to determine council
        try:
            soup = self.fetch_page(url)
            page_text = soup.get_text().lower()
            
            # Check page content for council mentions
            for council_id, keywords in council_keywords.items():
                if any(keyword in page_text for keyword in keywords):
                    return council_id
        except Exception as e:
            logger.warning(f"Could not fetch page content for {url}: {e}")
        
        # Default to general UKRI if can't determine
        return 'ahrc'  # Default to first council
    
    def extract_opportunity_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract opportunity detail page links from listing page."""
        links = []
        
        # Look for opportunity cards or links - more specific pattern
        # UKRI opportunity detail pages typically have URLs like /opportunity/some-opportunity-name/
        opportunity_elements = soup.find_all(['a'], href=re.compile(r'/opportunity/[^/?]+/?$'))
        
        for element in opportunity_elements:
            href = element.get('href')
            if href:
                # Skip filter links and other non-opportunity URLs
                if any(param in href for param in ['filter_', 'sort_', 'page=', '?']):
                    continue
                    
                full_url = urljoin(self.base_url, href)
                if full_url not in links:
                    links.append(full_url)
        
        # Also look for opportunity cards with specific CSS classes
        opportunity_cards = soup.find_all(['div', 'article'], class_=re.compile(r'opportunity|card|listing'))
        for card in opportunity_cards:
            link_element = card.find('a', href=re.compile(r'/opportunity/[^/?]+/?$'))
            if link_element:
                href = link_element.get('href')
                if href and not any(param in href for param in ['filter_', 'sort_', 'page=', '?']):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in links:
                        links.append(full_url)
        
        return links
    
    def scrape_opportunity_details(self, url: str, council_id: str) -> Optional[Dict]:
        """Scrape detailed information from an opportunity page."""
        soup = self.fetch_page(url)
        
        # Extract basic information
        title = self.extract_title(soup)
        if not title:
            return None
        
        # Skip funding finder pages (these are search result pages, not individual opportunities)
        if title.lower() == 'funding finder':
            logger.info(f"Skipping funding finder page: {url}")
            return None
        
        description = self.extract_description(soup)
        eligibility = self.extract_eligibility(soup)
        funding_details = self.extract_funding_details(soup)
        application_info = self.extract_application_info(soup)
        
        # Generate funding data structure
        funding = {
            'id': self.generate_id(title, self.councils[council_id]['name']),
            'title': title,
            'organization': self.councils[council_id]['name'],
            'category': 'ukri',
            'subcategory': council_id,
            'description': description,
            'eligibility': eligibility,
            'funding_details': funding_details,
            'application': application_info,
            'key_info': self.extract_key_info(soup),
            'contact': self.extract_contact_info(soup),
            'tags': self.generate_tags(title, description, council_id),
            'last_updated': datetime.now().isoformat(),
            'scraped_from': url,
            'status': 'active'
        }
        
        return funding
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract opportunity title."""
        # Try different selectors for title
        selectors = [
            'h1.page-title',
            'h1',
            '.opportunity-title',
            '.page-header h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return self.clean_text(element.get_text())
        
        return ""
    
    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract opportunity description."""
        # Look for description in various locations
        selectors = [
            '.opportunity-summary',
            '.page-summary',
            '.lead',
            '.intro-text'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return self.clean_text(element.get_text())
        
        # Fallback: get first few paragraphs
        paragraphs = soup.find_all('p')[:3]
        if paragraphs:
            return ' '.join([self.clean_text(p.get_text()) for p in paragraphs])
        
        return ""
    
    def extract_eligibility(self, soup: BeautifulSoup) -> Dict:
        """Extract eligibility information."""
        eligibility = {
            'career_stage': 'All Stages',
            'disciplines': [],
            'requirements': []
        }
        
        # Look for eligibility section
        eligibility_section = soup.find(['div', 'section'], 
                                      string=re.compile(r'eligibility', re.IGNORECASE))
        
        if eligibility_section:
            # Extract requirements from lists
            lists = eligibility_section.find_next_siblings(['ul', 'ol'])
            for ul in lists:
                items = ul.find_all('li')
                for item in items:
                    req = self.clean_text(item.get_text())
                    if req:
                        eligibility['requirements'].append(req)
        
        # Determine career stage from title/description
        text_content = soup.get_text().lower()
        if 'early career' in text_content or 'postdoc' in text_content:
            eligibility['career_stage'] = 'Early Career'
        elif 'senior' in text_content or 'professor' in text_content:
            eligibility['career_stage'] = 'Senior'
        elif 'fellowship' in text_content:
            eligibility['career_stage'] = 'Mid Career'
        
        return eligibility
    
    def extract_funding_details(self, soup: BeautifulSoup) -> Dict:
        """Extract funding amount and details."""
        funding_details = {
            'amount': {'min': 0, 'max': 0, 'currency': 'GBP', 'duration_years': 1},
            'covers': ['Research costs', 'Equipment', 'Travel']
        }
        
        # Look for funding amount in text
        text_content = soup.get_text()
        amount_info = self.extract_amount(text_content)
        funding_details['amount'].update(amount_info)
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*year', text_content, re.IGNORECASE)
        if duration_match:
            funding_details['amount']['duration_years'] = int(duration_match.group(1))
        
        return funding_details
    
    def extract_application_info(self, soup: BeautifulSoup) -> Dict:
        """Extract application deadline and process information."""
        application = {
            'deadline': (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d'),
            'next_deadline': (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
            'frequency': 'Annual',
            'application_url': soup.find('base', href=True)['href'] if soup.find('base', href=True) else '',
            'guidelines_url': ''
        }
        
        # Look for deadline information
        text_content = soup.get_text()
        deadline = self.extract_deadline(text_content)
        if deadline:
            application['deadline'] = deadline
        
        # Look for application links
        apply_links = soup.find_all('a', string=re.compile(r'apply|application', re.IGNORECASE))
        if apply_links:
            href = apply_links[0].get('href')
            if href:
                application['application_url'] = urljoin(self.base_url, href)
        
        return application
    
    def extract_key_info(self, soup: BeautifulSoup) -> Dict:
        """Extract key information like competition level, success rate."""
        return {
            'priority_level': 'High',
            'competition_level': 'Very Competitive',
            'success_rate': 'N/A'
        }
    
    def extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extract contact information."""
        contact = {'email': '', 'phone': ''}
        
        # Look for email addresses
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            contact['email'] = emails[0]
        
        return contact
    
    def generate_tags(self, title: str, description: str, council_id: str) -> List[str]:
        """Generate relevant tags for the funding opportunity."""
        tags = [council_id]
        
        # Add tags based on title and description
        text = f"{title} {description}".lower()
        
        tag_keywords = {
            'fellowship': 'fellowship',
            'grant': 'grant',
            'early career': 'early-career',
            'postdoc': 'postdoctoral',
            'innovation': 'innovation',
            'collaboration': 'collaboration',
            'international': 'international',
            'equipment': 'equipment',
            'training': 'training',
            'network': 'networking'
        }
        
        for keyword, tag in tag_keywords.items():
            if keyword in text:
                tags.append(tag)
        
        return tags

def main():
    """Main function to run the UKRI scraper."""
    logger.info("Starting UKRI scraper...")
    
    # Setup directories
    dirs = setup_directories()
    
    # Initialize scraper
    scraper = UKRIScraper()
    
    try:
        # Scrape all councils
        fundings = scraper.scrape_all_councils()
        
        if fundings:
            # Save individual funding files
            for funding in fundings:
                filename = f"ukri_{funding['subcategory']}_{funding['id']}.json"
                file_path = dirs['individual_fundings'] / filename
                save_json(funding, file_path)
            
            # Update main database
            database_path = dirs['data'] / 'funding_database.json'
            update_database(fundings, database_path)
            
            logger.info(f"Successfully scraped {len(fundings)} UKRI funding opportunities")
        else:
            logger.warning("No funding opportunities found")
            
    except Exception as e:
        logger.error(f"UKRI scraper failed: {e}")
        raise

if __name__ == "__main__":
    main()