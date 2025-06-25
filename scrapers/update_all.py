#!/usr/bin/env python3
"""
Main script to update all funding data by running all scrapers.

This script coordinates the execution of all individual scrapers:
- UKRI scraper
- National Academies scraper
- Charitable Foundations scraper

It also provides options for running individual scrapers and managing the update process.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from loguru import logger

# Import individual scrapers
from ukri_scraper import UKRIScraper
from academies_scraper import AcademiesScraper
from foundations_scraper import FoundationsScraper
from utils import setup_directories, update_database, save_json, load_json

class FundingDataUpdater:
    """Main class to coordinate funding data updates."""
    
    def __init__(self):
        self.dirs = setup_directories()
        self.scrapers = {
            'ukri': UKRIScraper(),
            'academies': AcademiesScraper(),
            'foundations': FoundationsScraper()
        }
        
        # Configure logging
        log_file = self.dirs['logs'] / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logger.add(log_file, level="INFO")
    
    def update_all(self) -> bool:
        """Run all scrapers and update the database."""
        logger.info("Starting complete funding data update...")
        
        all_fundings = []
        success_count = 0
        
        for scraper_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Running {scraper_name} scraper...")
                
                if scraper_name == 'ukri':
                    fundings = scraper.scrape_all_councils()
                elif scraper_name == 'academies':
                    fundings = scraper.scrape_all_academies()
                elif scraper_name == 'foundations':
                    fundings = scraper.scrape_all_foundations()
                else:
                    continue
                
                if fundings:
                    all_fundings.extend(fundings)
                    self.save_individual_fundings(fundings, scraper_name)
                    success_count += 1
                    logger.info(f"Successfully scraped {len(fundings)} opportunities from {scraper_name}")
                else:
                    logger.warning(f"No opportunities found from {scraper_name}")
                    
            except Exception as e:
                logger.error(f"Failed to run {scraper_name} scraper: {e}")
        
        # Update main database
        if all_fundings:
            database_path = self.dirs['data'] / 'funding_database.json'
            if update_database(all_fundings, database_path):
                logger.info(f"Successfully updated database with {len(all_fundings)} total opportunities")
                self.generate_summary_report(all_fundings)
                return True
            else:
                logger.error("Failed to update main database")
        else:
            logger.warning("No funding opportunities collected from any scraper")
        
        return False
    
    def update_specific(self, scraper_names: List[str]) -> bool:
        """Run specific scrapers only."""
        logger.info(f"Running specific scrapers: {', '.join(scraper_names)}")
        
        all_fundings = []
        
        for scraper_name in scraper_names:
            if scraper_name not in self.scrapers:
                logger.error(f"Unknown scraper: {scraper_name}")
                continue
            
            try:
                scraper = self.scrapers[scraper_name]
                logger.info(f"Running {scraper_name} scraper...")
                
                if scraper_name == 'ukri':
                    fundings = scraper.scrape_all_councils()
                elif scraper_name == 'academies':
                    fundings = scraper.scrape_all_academies()
                elif scraper_name == 'foundations':
                    fundings = scraper.scrape_all_foundations()
                else:
                    continue
                
                if fundings:
                    all_fundings.extend(fundings)
                    self.save_individual_fundings(fundings, scraper_name)
                    logger.info(f"Successfully scraped {len(fundings)} opportunities from {scraper_name}")
                
            except Exception as e:
                logger.error(f"Failed to run {scraper_name} scraper: {e}")
        
        # Update database
        if all_fundings:
            database_path = self.dirs['data'] / 'funding_database.json'
            return update_database(all_fundings, database_path)
        
        return False
    
    def save_individual_fundings(self, fundings: List[Dict], scraper_name: str) -> None:
        """Save individual funding files."""
        for funding in fundings:
            filename = f"{scraper_name}_{funding['subcategory']}_{funding['id']}.json"
            file_path = self.dirs['individual_fundings'] / filename
            save_json(funding, file_path)
    
    def generate_summary_report(self, fundings: List[Dict]) -> None:
        """Generate a summary report of the update."""
        logger.info("Generating summary report...")
        
        # Count by category
        category_counts = {}
        for funding in fundings:
            category = funding['category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by career stage
        career_stage_counts = {}
        for funding in fundings:
            stage = funding['eligibility']['career_stage']
            career_stage_counts[stage] = career_stage_counts.get(stage, 0) + 1
        
        # Calculate funding amounts
        total_min_funding = sum(f['funding_details']['amount']['min'] for f in fundings)
        total_max_funding = sum(f['funding_details']['amount']['max'] for f in fundings)
        
        # Count deadlines in next 30 days
        upcoming_deadlines = 0
        current_date = datetime.now()
        for funding in fundings:
            try:
                deadline = datetime.strptime(funding['application']['deadline'], '%Y-%m-%d')
                if (deadline - current_date).days <= 30 and (deadline - current_date).days >= 0:
                    upcoming_deadlines += 1
            except:
                pass
        
        # Create summary report
        report = {
            'update_timestamp': datetime.now().isoformat(),
            'total_opportunities': len(fundings),
            'category_breakdown': category_counts,
            'career_stage_breakdown': career_stage_counts,
            'funding_totals': {
                'min_total_gbp': total_min_funding,
                'max_total_gbp': total_max_funding
            },
            'upcoming_deadlines_30_days': upcoming_deadlines,
            'data_sources': list(self.scrapers.keys())
        }
        
        # Save report
        report_path = self.dirs['data'] / 'update_summary.json'
        save_json(report, report_path)
        
        # Log summary
        logger.info(f"Update Summary:")
        logger.info(f"  Total opportunities: {len(fundings)}")
        logger.info(f"  By category: {category_counts}")
        logger.info(f"  By career stage: {career_stage_counts}")
        logger.info(f"  Upcoming deadlines (30 days): {upcoming_deadlines}")
        logger.info(f"  Total funding range: £{total_min_funding:,} - £{total_max_funding:,}")
    
    def clean_old_data(self, days_old: int = 30) -> None:
        """Clean old individual funding files."""
        logger.info(f"Cleaning funding files older than {days_old} days...")
        
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        cleaned_count = 0
        
        for file_path in self.dirs['individual_fundings'].glob('*.json'):
            if file_path.stat().st_mtime < cutoff_date:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
        
        logger.info(f"Cleaned {cleaned_count} old funding files")
    
    def validate_data(self) -> bool:
        """Validate the current database."""
        logger.info("Validating funding database...")
        
        database_path = self.dirs['data'] / 'funding_database.json'
        database = load_json(database_path)
        
        if not database:
            logger.error("Database file not found or empty")
            return False
        
        fundings = database.get('fundings', [])
        if not fundings:
            logger.warning("No fundings in database")
            return True
        
        # Validate each funding
        valid_count = 0
        for funding in fundings:
            required_fields = ['id', 'title', 'organization', 'category', 'description']
            if all(field in funding for field in required_fields):
                valid_count += 1
            else:
                logger.warning(f"Invalid funding: {funding.get('id', 'unknown')}")
        
        logger.info(f"Validation complete: {valid_count}/{len(fundings)} fundings are valid")
        return valid_count == len(fundings)

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Update UK funding opportunities database')
    parser.add_argument('--scrapers', nargs='+', 
                       choices=['ukri', 'academies', 'foundations'],
                       help='Specific scrapers to run (default: all)')
    parser.add_argument('--clean', type=int, metavar='DAYS',
                       help='Clean old data files (older than DAYS)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate existing database')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Initialize updater
    updater = FundingDataUpdater()
    
    try:
        # Handle different operations
        if args.validate:
            success = updater.validate_data()
            sys.exit(0 if success else 1)
        
        if args.clean:
            updater.clean_old_data(args.clean)
            return
        
        # Run scrapers
        if args.scrapers:
            success = updater.update_specific(args.scrapers)
        else:
            success = updater.update_all()
        
        if success:
            logger.info("Update completed successfully")
            sys.exit(0)
        else:
            logger.error("Update failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()