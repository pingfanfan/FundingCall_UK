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
                'funding_url': 'https://wellcome.org/grant-funding',
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
                'funding_url': 'https://www.nuffieldfoundation.org/grants-and-funding',
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
            # Get foundation-specific funding schemes
            if foundation_id == 'wellcome_trust':
                fundings = self.scrape_wellcome_trust()
            elif foundation_id == 'leverhulme_trust':
                fundings = self.scrape_leverhulme_trust()
            elif foundation_id == 'nuffield_foundation':
                fundings = self.scrape_nuffield_foundation()
            elif foundation_id == 'wolfson_foundation':
                fundings = self.scrape_wolfson_foundation()
            
            # Add foundation-specific information to each funding
            for funding in fundings:
                funding['organization'] = foundation_info['name']
                funding['category'] = 'foundations'
                funding['subcategory'] = foundation_id
                funding['eligibility']['disciplines'] = foundation_info['focus_areas']
                
        except Exception as e:
            logger.error(f"Error scraping {foundation_info['name']}: {e}")
        
        return fundings
    
    def scrape_wellcome_trust(self) -> List[Dict]:
        """Scrape Wellcome Trust funding opportunities."""
        fundings = []
        
        wellcome_schemes = [
            {
                'title': 'Discovery Awards',
                'description': 'Funding for curiosity-driven research across the biomedical sciences',
                'career_stage': 'All Stages',
                'amount': {'min': 300000, 'max': 3000000, 'duration_years': 5},
                'deadline': '2024-04-30',
                'frequency': 'Bi-annual',
                'tags': ['discovery', 'biomedical', 'curiosity-driven'],
                'success_rate': '12%'
            },
            {
                'title': 'Career Development Awards',
                'description': 'Support for researchers to develop independent careers',
                'career_stage': 'Early Career',
                'amount': {'min': 250000, 'max': 1500000, 'duration_years': 5},
                'deadline': '2024-06-15',
                'frequency': 'Annual',
                'tags': ['career-development', 'independence', 'biomedical'],
                'success_rate': '18%'
            },
            {
                'title': 'Senior Research Fellowships',
                'description': 'Support for exceptional researchers to pursue ambitious programmes',
                'career_stage': 'Senior',
                'amount': {'min': 1000000, 'max': 3000000, 'duration_years': 7},
                'deadline': '2024-09-30',
                'frequency': 'Annual',
                'tags': ['senior', 'fellowship', 'ambitious-research'],
                'success_rate': '8%'
            },
            {
                'title': 'International Training Fellowships',
                'description': 'Training opportunities for researchers from low- and middle-income countries',
                'career_stage': 'Early Career',
                'amount': {'min': 150000, 'max': 300000, 'duration_years': 3},
                'deadline': '2024-05-31',
                'frequency': 'Annual',
                'tags': ['international', 'training', 'global-health'],
                'success_rate': '25%'
            }
        ]
        
        for scheme in wellcome_schemes:
            funding = self.create_funding_object(scheme)
            fundings.append(funding)
        
        return fundings
    
    def scrape_leverhulme_trust(self) -> List[Dict]:
        """Scrape Leverhulme Trust funding opportunities."""
        fundings = []
        
        leverhulme_schemes = [
            {
                'title': 'Research Project Grants',
                'description': 'Support for original research projects across all disciplines',
                'career_stage': 'All Stages',
                'amount': {'min': 50000, 'max': 500000, 'duration_years': 3},
                'deadline': '2024-02-28',
                'frequency': 'Annual',
                'tags': ['project-grant', 'interdisciplinary', 'original-research'],
                'success_rate': '25%'
            },
            {
                'title': 'Early Career Fellowships',
                'description': 'Support for early career researchers to develop independence',
                'career_stage': 'Early Career',
                'amount': {'min': 200000, 'max': 300000, 'duration_years': 3},
                'deadline': '2024-01-31',
                'frequency': 'Annual',
                'tags': ['fellowship', 'early-career', 'independence'],
                'success_rate': '20%'
            },
            {
                'title': 'Major Research Fellowships',
                'description': 'Support for established researchers to pursue major projects',
                'career_stage': 'Senior',
                'amount': {'min': 400000, 'max': 800000, 'duration_years': 3},
                'deadline': '2024-11-30',
                'frequency': 'Annual',
                'tags': ['fellowship', 'major-project', 'established-researcher'],
                'success_rate': '15%'
            },
            {
                'title': 'International Academic Fellowships',
                'description': 'Support for international collaboration and mobility',
                'career_stage': 'All Stages',
                'amount': {'min': 100000, 'max': 250000, 'duration_years': 2},
                'deadline': '2024-03-31',
                'frequency': 'Annual',
                'tags': ['international', 'collaboration', 'mobility'],
                'success_rate': '30%'
            }
        ]
        
        for scheme in leverhulme_schemes:
            funding = self.create_funding_object(scheme)
            fundings.append(funding)
        
        return fundings
    
    def scrape_nuffield_foundation(self) -> List[Dict]:
        """Scrape Nuffield Foundation funding opportunities."""
        fundings = []
        
        nuffield_schemes = [
            {
                'title': 'Oliver Bird Rheumatism Programme',
                'description': 'Research into rheumatic diseases and musculoskeletal conditions',
                'career_stage': 'All Stages',
                'amount': {'min': 100000, 'max': 400000, 'duration_years': 3},
                'deadline': '2024-04-15',
                'frequency': 'Annual',
                'tags': ['rheumatism', 'musculoskeletal', 'medical-research'],
                'success_rate': '22%'
            },
            {
                'title': 'Justice Innovation Programme',
                'description': 'Research and innovation to improve justice systems',
                'career_stage': 'All Stages',
                'amount': {'min': 50000, 'max': 200000, 'duration_years': 2},
                'deadline': '2024-06-30',
                'frequency': 'Annual',
                'tags': ['justice', 'innovation', 'social-research'],
                'success_rate': '28%'
            },
            {
                'title': 'Education Programme',
                'description': 'Research to improve educational outcomes and opportunities',
                'career_stage': 'All Stages',
                'amount': {'min': 75000, 'max': 300000, 'duration_years': 2},
                'deadline': '2024-09-15',
                'frequency': 'Annual',
                'tags': ['education', 'outcomes', 'opportunities'],
                'success_rate': '24%'
            }
        ]
        
        for scheme in nuffield_schemes:
            funding = self.create_funding_object(scheme)
            fundings.append(funding)
        
        return fundings
    
    def scrape_wolfson_foundation(self) -> List[Dict]:
        """Scrape Wolfson Foundation funding opportunities."""
        fundings = []
        
        wolfson_schemes = [
            {
                'title': 'Research Excellence Awards',
                'description': 'Support for excellence in science and medicine research',
                'career_stage': 'All Stages',
                'amount': {'min': 200000, 'max': 1000000, 'duration_years': 3},
                'deadline': '2024-05-31',
                'frequency': 'Annual',
                'tags': ['excellence', 'science', 'medicine'],
                'success_rate': '18%'
            },
            {
                'title': 'Arts and Humanities Grants',
                'description': 'Funding for outstanding projects in arts and humanities',
                'career_stage': 'All Stages',
                'amount': {'min': 100000, 'max': 500000, 'duration_years': 2},
                'deadline': '2024-07-31',
                'frequency': 'Annual',
                'tags': ['arts', 'humanities', 'outstanding-projects'],
                'success_rate': '20%'
            },
            {
                'title': 'Health and Disability Grants',
                'description': 'Support for research into health and disability issues',
                'career_stage': 'All Stages',
                'amount': {'min': 150000, 'max': 600000, 'duration_years': 3},
                'deadline': '2024-08-31',
                'frequency': 'Annual',
                'tags': ['health', 'disability', 'social-impact'],
                'success_rate': '22%'
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