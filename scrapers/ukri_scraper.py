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

from utils import (
    FundingScraper,
    canonicalize_url,
    save_json,
    setup_directories,
    update_database,
)

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
        logger.info("Scraping all UKRI opportunities...")

        collected_links: List[Dict] = []
        seen_urls: set[str] = set()

        try:
            main_links = self.collect_main_opportunity_links(seen_urls)
            collected_links.extend(main_links)
            logger.info(
                "Collected %s links from main listing (unique so far: %s)"
                % (len(main_links), len(collected_links))
            )
        except Exception as exc:
            logger.error(f"Failed to collect links from main opportunities: {exc}")

        for council_id, council_info in self.councils.items():
            logger.info(f"Collecting links for {council_info['name']}...")
            try:
                council_links = self.collect_council_links(council_id, seen_urls)
                collected_links.extend(council_links)
                logger.info(
                    "Collected %s additional links from %s (unique so far: %s)"
                    % (
                        len(council_links),
                        council_info["name"],
                        len(collected_links),
                    )
                )
            except Exception as exc:
                logger.error(f"Failed to collect links for {council_info['name']}: {exc}")

        if not collected_links:
            logger.warning("No UKRI opportunity links discovered")
            return []

        logger.info(
            "Discovered %s unique UKRI opportunity URLs – fetching details in second stage"
            % len(collected_links)
        )
        return self.build_fundings_from_links(collected_links)

    def collect_main_opportunity_links(self, seen_urls: set[str]) -> List[Dict]:
        """Collect opportunity links from the main UKRI opportunities page."""
        collected: List[Dict] = []
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
                    url_key = canonicalize_url(link)
                    if url_key in seen_urls:
                        continue

                    seen_urls.add(url_key)
                    new_links_found += 1

                    collected.append(
                        {
                            "url": link,
                            "council_id": self.determine_council_from_url(link),
                        }
                    )

                logger.info(
                    "Found %s new opportunity links on page %s (unique so far: %s)"
                    % (new_links_found, page, len(collected))
                )

                # If no new links were found, we might have reached the end
                if new_links_found == 0:
                    logger.info(f"No new opportunities found on page {page}, stopping pagination")
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to scrape opportunities page {page}: {e}")
                break
        
        logger.info(
            "Completed link collection from main opportunities. Total pages: %s, unique links: %s"
            % (page - 1, len(collected))
        )
        return collected

    def collect_council_links(self, council_id: str, seen_urls: set[str]) -> List[Dict]:
        """Collect opportunity links from a specific council listing."""
        council_info = self.councils[council_id]
        collected: List[Dict] = []

        # Get the opportunities listing page
        soup = self.fetch_page(council_info['funding_url'])

        # Find opportunity links
        opportunity_links = self.extract_opportunity_links(soup)

        for link in opportunity_links:
            url_key = canonicalize_url(link)
            if url_key in seen_urls:
                continue

            seen_urls.add(url_key)

            collected.append({"url": link, "council_id": council_id})

        return collected

    def build_fundings_from_links(self, link_batch: List[Dict]) -> List[Dict]:
        """Fetch and build funding payloads for a batch of collected links."""

        fundings: List[Dict] = []
        for item in link_batch:
            try:
                funding = self.scrape_opportunity_details(item["url"], item.get("council_id"))
            except Exception as exc:
                logger.error(f"Failed to scrape opportunity {item['url']}: {exc}")
                continue

            if funding:
                fundings.append(funding)

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
        application_info = self.extract_application_info(soup, url)
        last_updated = self.extract_last_updated(soup) or datetime.now().isoformat()

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
            'last_updated': last_updated,
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
        """Extract funding amount and related details."""

        funding_details = {
            'amount': {'min': 0, 'max': 0, 'currency': 'GBP', 'duration_years': 1},
            'covers': ['Research costs', 'Equipment', 'Travel']
        }

        amount_info = None
        for candidate in self._amount_candidates(soup):
            try:
                info = self.extract_amount(candidate)
            except Exception as exc:
                logger.debug(f"Amount parsing failed for candidate '{candidate[:80]}…': {exc}")
                continue
            if info and (info.get('min') or info.get('max')):
                amount_info = info
                break

        if not amount_info:
            try:
                amount_info = self.extract_amount(soup.get_text(separator=' '))
            except Exception as exc:
                logger.error(f"Could not extract amount from opportunity page: {exc}")
                amount_info = None

        if amount_info:
            funding_details['amount'].update(amount_info)
            min_amount = funding_details['amount'].get('min') or 0
            max_amount = funding_details['amount'].get('max') or 0
            if max_amount and min_amount and min_amount > max_amount:
                funding_details['amount']['min'], funding_details['amount']['max'] = max_amount, min_amount

        # Extract duration from nearby sections.
        duration_text = self._find_duration_text(soup)
        if duration_text:
            duration_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|month)', duration_text, re.IGNORECASE)
            if duration_match:
                value = float(duration_match.group(1))
                if 'month' in duration_match.group(0).lower():
                    funding_details['amount']['duration_years'] = max(1, int(round(value / 12)))
                else:
                    funding_details['amount']['duration_years'] = max(1, int(round(value)))

        return funding_details

    def extract_application_info(self, soup: BeautifulSoup, detail_url: str) -> Dict:
        """Extract application deadline and process information."""

        now = datetime.now()
        application = {
            'deadline': (now + timedelta(days=90)).strftime('%Y-%m-%d'),
            'next_deadline': (now + timedelta(days=365)).strftime('%Y-%m-%d'),
            'frequency': 'Annual',
            'application_url': detail_url,
            'guidelines_url': ''
        }

        text_content = soup.get_text(separator=' ')
        deadline = self.extract_deadline(text_content)
        if deadline:
            application['deadline'] = deadline

        apply_links = soup.find_all('a', string=re.compile(r'apply|application|start now', re.IGNORECASE))
        for link in apply_links:
            href = link.get('href')
            if not href or href.startswith('#'):
                continue
            application['application_url'] = urljoin(detail_url, href)
            break

        guidelines_link = soup.find('a', string=re.compile(r'guidance|guidelines', re.IGNORECASE))
        if guidelines_link and guidelines_link.get('href'):
            application['guidelines_url'] = urljoin(detail_url, guidelines_link['href'])

        return application

    def extract_last_updated(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the last updated timestamp from the opportunity page."""

        meta = soup.find('meta', attrs={'property': 'article:modified_time'})
        if meta and meta.get('content'):
            parsed = self._parse_datetime(meta['content'])
            if parsed:
                return parsed

        time_element = soup.find('time')
        if time_element:
            datetime_attr = time_element.get('datetime')
            text_value = time_element.get_text(strip=True)
            for candidate in filter(None, [datetime_attr, text_value]):
                parsed = self._parse_datetime(candidate)
                if parsed:
                    return parsed

        label = soup.find(string=re.compile(r'(last updated|updated|published)', re.IGNORECASE))
        if label:
            parsed = self._parse_datetime(str(label))
            if parsed:
                return parsed

        return None

    def _amount_candidates(self, soup: BeautifulSoup) -> List[str]:
        """Return text snippets that are likely to contain funding amounts."""

        candidates: List[str] = []
        seen: set[str] = set()
        labels = soup.find_all(
            ['dt', 'th', 'h2', 'h3', 'h4'],
            string=re.compile(r'funding amount|funding available|award|you can apply for', re.IGNORECASE),
        )

        for label in labels:
            for sibling in label.find_all_next(['dd', 'td', 'p', 'li'], limit=3):
                text = self.clean_text(sibling.get_text())
                if text and text not in seen:
                    seen.add(text)
                    candidates.append(text)

        return candidates

    def _find_duration_text(self, soup: BeautifulSoup) -> Optional[str]:
        duration_label = soup.find(
            string=re.compile(r'duration|project length|award length', re.IGNORECASE)
        )
        if duration_label:
            parent = duration_label.parent
            if parent:
                return self.clean_text(parent.get_text())
        return None

    def _parse_datetime(self, value: str) -> Optional[str]:
        if not value:
            return None
        cleaned = value.strip().replace('Z', '+00:00')
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        # Fallback to existing date extraction (returns YYYY-MM-DD)
        date_only = self.extract_deadline(value)
        if date_only:
            try:
                dt = datetime.strptime(date_only, "%Y-%m-%d")
                return dt.isoformat()
            except ValueError:
                return date_only
        return None
    
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
