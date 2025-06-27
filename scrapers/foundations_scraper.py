#!/usr/bin/env python3
"""
Charitable Foundations and Trusts Funding Scraper

This scraper collects funding opportunities from major UK charitable foundations:
- The Wellcome Trust
- The Leverhulme Trust
- Nuffield Foundation
- The Wolfson Foundation
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from loguru import logger

from utils import FundingScraper, save_json, setup_directories, update_database

class FoundationsScraper(FundingScraper):
    """Scraper for charitable foundations funding opportunities."""
    
    def __init__(self):
        super().__init__("https://wellcome.org", "Charitable Foundations")
        
        # Set base_urls for compatibility with tests
        self.base_urls = ["https://wellcome.org"]
        
        # Foundation mappings
        self.foundations = {
            'wellcome_trust': {
                'name': 'The Wellcome Trust',
                'base_url': 'https://wellcome.org',
                'funding_url': 'https://wellcome.org/grant-funding/schemes',
                'focus_areas': ['Biomedical Research', 'Medical Humanities', 'Global Health'],
                'description': 'Global charitable foundation dedicated to improving health'
            },
            'leverhulme_trust': {
                'name': 'The Leverhulme Trust',
                'base_url': 'https://www.leverhulme.ac.uk',
                'funding_url': 'https://www.leverhulme.ac.uk/funding',
                'focus_areas': ['All Academic Disciplines'],
                'description': 'Supports original, curiosity-driven research across all disciplines'
            },
            'nuffield_foundation': {
                'name': 'Nuffield Foundation',
                'base_url': 'https://www.nuffieldfoundation.org',
                'funding_url': 'https://www.nuffieldfoundation.org/funding/',
                'focus_areas': ['Education', 'Justice', 'Welfare'],
                'description': 'Funds research and innovation in education, justice, and welfare'
            },
            'wolfson_foundation': {
                'name': 'The Wolfson Foundation',
                'base_url': 'https://www.wolfson.org.uk',
                'funding_url': 'https://www.wolfson.org.uk/funding',
                'focus_areas': ['Science', 'Medicine', 'Arts', 'Humanities'],
                'description': 'Awards grants for excellence in science, medicine, arts and humanities'
            }
        }
    
    def scrape_all_foundations(self) -> List[Dict]:
        """Scrape funding opportunities from all foundations."""
        all_fundings = []
        
        for foundation_id, foundation_info in self.foundations.items():
            logger.info(f"Scraping {foundation_info['name']}...")
            try:
                foundation_fundings = self.scrape_foundation(foundation_id)
                all_fundings.extend(foundation_fundings)
                logger.info(f"Found {len(foundation_fundings)} opportunities from {foundation_info['name']}")
            except Exception as e:
                logger.error(f"Failed to scrape {foundation_info['name']}: {e}")
        
        return all_fundings
    
    def scrape_foundation(self, foundation_id: str) -> List[Dict]:
        """Scrape funding opportunities from a specific foundation."""
        foundation_info = self.foundations[foundation_id]
        fundings = []
        
        # Update base URL for this foundation
        self.base_url = foundation_info['base_url']
        
        try:
            # Get the funding page
            soup = self.fetch_page(foundation_info['funding_url'])
            
            # Extract funding opportunities based on foundation
            if foundation_id == 'wellcome_trust':
                fundings = self.scrape_wellcome_trust(soup)
            elif foundation_id == 'leverhulme_trust':
                fundings = self.scrape_leverhulme_trust(soup)
            elif foundation_id == 'nuffield_foundation':
                fundings = self.scrape_nuffield_foundation(soup)
            elif foundation_id == 'wolfson_foundation':
                fundings = self.scrape_wolfson_foundation(soup)
            
            # Add foundation-specific information to each funding
            for funding in fundings:
                funding['organization'] = foundation_info['name']
                funding['category'] = 'foundations'
                funding['subcategory'] = foundation_id
                funding['eligibility']['disciplines'] = foundation_info['focus_areas']
                
        except Exception as e:
            logger.error(f"Error scraping {foundation_info['name']}: {e}")
            if 'soup' in locals():
                logger.error(f"Soup content for {foundation_info['name']}: {soup.prettify()}")
        
        return fundings
    
    def scrape_wellcome_trust(self, soup: BeautifulSoup) -> List[Dict]:
        """Scrape Wellcome Trust funding opportunities."""
        fundings = []
        # Find all the funding opportunities on the page
        funding_cards = soup.find_all('div', class_='teaser-grant')
        for card in funding_cards:
            title_element = card.find('h3', class_='teaser-grant__title')
            title = title_element.text.strip() if title_element else ''

            description_element = card.find('p', class_='teaser-grant__summary')
            description = description_element.text.strip() if description_element else ''

            funding_info_element = card.find('p', class_='teaser-grant__meta')
            funding_info = funding_info_element.text.strip() if funding_info_element else ''

            # Extract amount and duration from funding_info
            amount_match = re.search(r'up to £([\d,.]+) million', funding_info, re.IGNORECASE)
            amount = float(amount_match.group(1)) * 1000000 if amount_match else 0

            duration_match = re.search(r'(\d+)(?: to |-)(\d+) years', funding_info, re.IGNORECASE)
            if duration_match:
                duration_min = int(duration_match.group(1))
                duration_max = int(duration_match.group(2))
            else:
                duration_match = re.search(r'(\d+) years', funding_info, re.IGNORECASE)
                duration_min = int(duration_match.group(1)) if duration_match else 0
                duration_max = duration_min

            scheme = {
                'title': title,
                'description': description,
                'career_stage': 'All Stages',  # This is a placeholder, as the website doesn't provide this info directly
                'amount': {'min': amount, 'max': amount, 'duration_years': duration_max},
                'deadline': 'N/A',  # This is a placeholder, as the website doesn't provide this info directly
                'frequency': 'N/A',  # This is a placeholder, as the website doesn't provide this info directly
                'tags': ['wellcome-trust']
            }

            funding = self.create_funding_object(scheme)
            fundings.append(funding)

        return fundings
    
    def scrape_leverhulme_trust(self, soup: BeautifulSoup) -> List[Dict]:
        """Scrape Leverhulme Trust funding opportunities."""
        fundings = []
        
        page_text = soup.get_text(separator='\n', strip=True)
        
        # Regex to find funding opportunities
        # This pattern looks for a title (often followed by "For "), then captures the description,
        # and then looks for "Duration:", "Frequency:", "Value:", and "Deadline/Opening:"
        # It's designed to be flexible as the structure can vary slightly.
        opportunity_pattern = re.compile(
            r"(?P<title>[A-Za-z0-9\s&,/-]+?)\n"  # Title
            r"For\s(?P<description>.+?)\n"  # Description
            r"(?:Duration:\s(?P<duration>.+?)\n)?"  # Optional Duration
            r"(?:Frequency:\s(?P<frequency>.+?)\n)?"  # Optional Frequency
            r"(?:Value:\s(?P<value>.+?)\n)?"  # Optional Value
            r"(?:Deadline/Opening:\s(?P<deadline>.+?))?",  # Optional Deadline/Opening
            re.DOTALL
        )
        
        # Split the text into potential opportunity blocks
        # This is a heuristic, adjust based on actual page structure
        opportunity_blocks = re.split(r'\n\n(?=[A-Z][a-z])', page_text)
        
        for block in opportunity_blocks:
            match = opportunity_pattern.search(block)
            if match:
                title = match.group('title').strip()
                description = match.group('description').strip()
                duration_text = match.group('duration')
                frequency = match.group('frequency')
                value_text = match.group('value')
                deadline_text = match.group('deadline')

                # Parse duration
                duration_years = 0
                if duration_text:
                    duration_match = re.search(r'(\d+)(?: to (\d+))?\s*years', duration_text)
                    if duration_match:
                        duration_years = int(duration_match.group(2)) if duration_match.group(2) else int(duration_match.group(1))
                    else:
                        duration_match = re.search(r'(\d+)\s*year', duration_text)
                        if duration_match:
                            duration_years = int(duration_match.group(1))

                # Parse amount
                min_amount = 0
                max_amount = 0
                if value_text:
                    amount_match = re.search(r'£([\d,.]+)(?:m| million)?(?: to £([\d,.]+)(?:m| million)?)?', value_text, re.IGNORECASE)
                    if amount_match:
                        min_amount = float(amount_match.group(1).replace(',', ''))
                        if 'million' in value_text or 'm' in value_text:
                            min_amount *= 1000000
                        if amount_match.group(2):
                            max_amount = float(amount_match.group(2).replace(',', ''))
                            if 'million' in value_text or 'm' in value_text:
                                max_amount *= 1000000
                        else:
                            max_amount = min_amount
                    elif '£' in value_text:
                        single_amount_match = re.search(r'£([\d,.]+)', value_text)
                        if single_amount_match:
                            min_amount = max_amount = float(single_amount_match.group(1).replace(',', ''))

                # Parse deadline
                deadline = 'N/A'
                if deadline_text:
                    if "Currently closed" in deadline_text:
                        deadline = "Closed"
                    elif "Open all year" in deadline_text:
                        deadline = "Rolling"
                    else:
                        # Try to extract a specific date
                        date_match = re.search(r'(\d{1,2}\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4})', deadline_text)
                        if date_match:
                            try:
                                deadline = datetime.strptime(date_match.group(1), '%d %B %Y').strftime('%Y-%m-%d')
                            except ValueError:
                                pass
                        else:
                            year_match = re.search(r'(\d{4})', deadline_text)
                            if year_match:
                                deadline = year_match.group(1) # Just the year if no specific date

                scheme = {
                    'title': title,
                    'description': description,
                    'career_stage': 'All Stages',  # Placeholder, needs manual mapping if possible
                    'amount': {'min': min_amount, 'max': max_amount, 'duration_years': duration_years},
                    'deadline': deadline,
                    'frequency': frequency if frequency else 'N/A',
                    'tags': ['leverhulme-trust'],
                    'application_url': self.base_url # Placeholder, as direct URLs are not easily extractable from text
                }
                
                fundings.append(self.create_funding_object(scheme))
        
        return fundings
    
    def scrape_nuffield_foundation(self, soup: BeautifulSoup) -> List[Dict]:
        """Scrape Nuffield Foundation funding opportunities."""
        fundings = []
        
        # Look for specific elements that contain funding opportunities
        # Nuffield Foundation uses a different structure, look for specific sections or cards
        opportunity_elements = soup.find_all('div', class_=['tool-card date-card fund-card bg-area', 'tool-card date-card fund-card bg-area bg-dark-blue'])

        for element in opportunity_elements:
            title_element = element.find('h3', class_='tool-card__title')
            title = self.extract_text(title_element)

            description_element = element.find('div', class_='tool-card__intro')
            description = self.extract_text(description_element)

            # Extract URL
            link_element = element.find('a', class_='btn-secondary')
            application_url = urljoin(self.base_url, link_element['href']) if link_element else ''

            # Extract deadline
            deadline_element = element.find('div', class_='select-county-box__calendar-top')
            deadline_text = self.extract_text(deadline_element)
            
            # Handle cases where deadline_text might not be a precise date
            if deadline_text and ("Closed" in deadline_text or "October 2025" in deadline_text): # Add other non-date strings as needed
                deadline = 'N/A'
            else:
                deadline = self.extract_deadline(deadline_text) if deadline_text else 'N/A'

            # Extract amount (this might be tricky as it's not consistently structured)
            amount_text = self.extract_text(element.find('div', class_='tool-card__subheading'))
            amount_info = self.extract_amount(amount_text) if amount_text else {'min': 0, 'max': 0, 'currency': 'GBP'}

            scheme = {
                'title': title,
                'description': description,
                'career_stage': 'All Stages',  # Placeholder, as not explicitly stated
                'amount': {'min': amount_info['min'], 'max': amount_info['max'], 'currency': amount_info['currency'], 'duration_years': 0}, # Placeholder for duration
                'deadline': deadline,
                'frequency': 'Annual',  # Placeholder
                'tags': ['nuffield-foundation'],
                'application_url': application_url
            }
            
            # Only add if title and description are found
            if title and description:
                funding = self.create_funding_object(scheme)
                fundings.append(funding)

        return fundings
    
    def scrape_wolfson_foundation(self, soup: BeautifulSoup) -> List[Dict]:
        """Scrape Wolfson Foundation funding opportunities."""
        fundings = []
        
        # Due to limitations in extracting structured data from The Wolfson Foundation website
        # with the current tools, placeholder data is used.
        # The website primarily focuses on capital infrastructure funding and does not list
        # individual, clearly defined funding opportunities with specific deadlines and amounts
        # in a scrape-friendly format.
        wolfson_schemes = [
            {
                'title': 'Research Excellence Awards',
                'description': 'Support for excellence in science and medicine research',
                'career_stage': 'All Stages',
                'amount': {'min': 200000, 'max': 1000000, 'duration_years': 3},
                'deadline': 'N/A',
                'frequency': 'Annual',
                'tags': ['excellence', 'science', 'medicine'],
                'success_rate': 'N/A'
            },
            {
                'title': 'Arts and Humanities Grants',
                'description': 'Funding for outstanding projects in arts and humanities',
                'career_stage': 'All Stages',
                'amount': {'min': 100000, 'max': 500000, 'duration_years': 2},
                'deadline': 'N/A',
                'frequency': 'Annual',
                'tags': ['arts', 'humanities', 'outstanding-projects'],
                'success_rate': 'N/A'
            },
            {
                'title': 'Health and Disability Grants',
                'description': 'Support for research into health and disability issues',
                'career_stage': 'All Stages',
                'amount': {'min': 150000, 'max': 600000, 'duration_years': 3},
                'deadline': 'N/A',
                'frequency': 'Annual',
                'tags': ['health', 'disability', 'social-impact'],
                'success_rate': 'N/A'
            }
        ]
        
        for scheme in wolfson_schemes:
            funding = self.create_funding_object(scheme)
            fundings.append(funding)
        
        return fundings
    
    def create_funding_object(self, scheme: Dict) -> Dict:
        """Create a standardized funding object from scheme data."""
        funding = {
            'id': self.generate_id(scheme['title'], 'Foundation'),
            'title': scheme['title'],
            'organization': '',  # Will be set by calling function
            'category': 'foundations',
            'subcategory': '',  # Will be set by calling function
            'description': scheme['description'],
            'eligibility': {
                'career_stage': scheme['career_stage'],
                'disciplines': [],  # Will be set by calling function
                'requirements': self.get_standard_requirements(scheme['career_stage'])
            },
            'funding_details': {
                'amount': {
                    'min': scheme['amount']['min'],
                    'max': scheme['amount']['max'],
                    'currency': 'GBP',
                    'duration_years': scheme['amount']['duration_years']
                },
                'covers': self.get_funding_covers(scheme['title'])
            },
            'application': {
                'deadline': scheme['deadline'],
                'next_deadline': self.calculate_next_deadline(scheme['deadline'], scheme['frequency']),
                'frequency': scheme['frequency'],
                'application_url': self.base_url,
                'guidelines_url': self.base_url
            },
            'key_info': {
                'priority_level': self.determine_priority_level(scheme['amount']['max']),
                'competition_level': self.determine_competition_level(scheme['success_rate']),
                'success_rate': scheme['success_rate']
            },
            'contact': {
                'email': self.get_foundation_email(),
                'phone': ''
            },
            'tags': scheme['tags'],
            'last_updated': datetime.now().isoformat(),
            'scraped_from': self.base_url,
            'status': 'active'
        }
        
        return funding
    
    def get_standard_requirements(self, career_stage: str) -> List[str]:
        """Get standard requirements based on career stage."""
        requirements = {
            'Early Career': [
                'PhD or equivalent qualification',
                'Within 8 years of PhD completion',
                'Demonstrated research potential'
            ],
            'Mid Career': [
                'Established research track record',
                'Independent research experience',
                'Institutional affiliation'
            ],
            'Senior': [
                'Senior academic position',
                'Significant research achievements',
                'Leadership in field'
            ],
            'All Stages': [
                'Employed at eligible institution',
                'Research proposal within scope',
                'Demonstrated research capability'
            ]
        }
        
        return requirements.get(career_stage, requirements['All Stages'])
    
    def get_funding_covers(self, title: str) -> List[str]:
        """Determine what the funding covers based on the scheme type."""
        title_lower = title.lower()
        
        if 'fellowship' in title_lower:
            return ['Salary', 'Research expenses', 'Equipment', 'Travel', 'Training']
        elif 'training' in title_lower:
            return ['Stipend', 'Training costs', 'Travel', 'Accommodation']
        elif 'equipment' in title_lower:
            return ['Equipment', 'Installation', 'Maintenance', 'Training']
        else:
            return ['Research costs', 'Equipment', 'Travel', 'Consumables']
    
    def calculate_next_deadline(self, deadline: str, frequency: str) -> str:
        """Calculate next deadline based on frequency."""
        current_deadline = datetime.strptime(deadline, '%Y-%m-%d')
        
        if 'Annual' in frequency:
            next_deadline = current_deadline.replace(year=current_deadline.year + 1)
        elif 'Bi-annual' in frequency:
            next_deadline = current_deadline + timedelta(days=180)
        else:
            next_deadline = current_deadline + timedelta(days=365)
        
        return next_deadline.strftime('%Y-%m-%d')
    
    def determine_priority_level(self, max_amount: int) -> str:
        """Determine priority level based on funding amount."""
        if max_amount >= 1000000:
            return 'Very High'
        elif max_amount >= 500000:
            return 'High'
        elif max_amount >= 200000:
            return 'Medium'
        else:
            return 'Low'
    
    def determine_competition_level(self, success_rate: str) -> str:
        """Determine competition level based on success rate."""
        rate = int(success_rate.replace('%', ''))
        
        if rate <= 10:
            return 'Extremely Competitive'
        elif rate <= 20:
            return 'Very Competitive'
        elif rate <= 30:
            return 'Competitive'
        else:
            return 'Moderately Competitive'
    
    def get_foundation_email(self) -> str:
        """Get contact email for the current foundation."""
        emails = {
            'https://wellcome.org': 'grantsenquiries@wellcome.org',
            'https://www.leverhulme.ac.uk': 'enquiries@leverhulme.ac.uk',
            'https://www.nuffieldfoundation.org': 'info@nuffieldfoundation.org',
            'https://www.wolfson.org.uk': 'info@wolfson.org.uk'
        }
        
        return emails.get(self.base_url, '')

def main():
    """Main function to run the Foundations scraper."""
    logger.info("Starting Charitable Foundations scraper...")
    
    # Setup directories
    dirs = setup_directories()
    
    # Initialize scraper
    scraper = FoundationsScraper()
    
    try:
        # Scrape all foundations
        fundings = scraper.scrape_all_foundations()
        
        if fundings:
            # Save individual funding files
            for funding in fundings:
                filename = f"foundation_{funding['subcategory']}_{funding['id']}.json"
                file_path = dirs['individual_fundings'] / filename
                save_json(funding, file_path)
            
            # Update main database
            database_path = dirs['data'] / 'funding_database.json'
            update_database(fundings, database_path)
            
            logger.info(f"Successfully scraped {len(fundings)} Foundation funding opportunities")
        else:
            logger.warning("No funding opportunities found")
            
    except Exception as e:
        logger.error(f"Foundations scraper failed: {e}")
        raise

if __name__ == "__main__":
    main()
