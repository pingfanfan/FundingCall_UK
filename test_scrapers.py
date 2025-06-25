#!/usr/bin/env python3
"""
Test script for UK Funding Tracker scrapers.

This script provides basic testing functionality for the scrapers
to ensure they work correctly before deployment.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add scrapers directory to path
sys.path.append(str(Path(__file__).parent / 'scrapers'))

from scrapers.utils import setup_directories, validate_funding_data
from scrapers.ukri_scraper import UKRIScraper
from scrapers.academies_scraper import AcademiesScraper
from scrapers.foundations_scraper import FoundationsScraper

def test_directory_setup():
    """Test that directories are set up correctly."""
    print("Testing directory setup...")
    
    try:
        dirs = setup_directories()
        required_dirs = ['data', 'individual_fundings', 'logs']
        
        for dir_name in required_dirs:
            if dir_name not in dirs:
                print(f"❌ Missing directory: {dir_name}")
                return False
            
            if not dirs[dir_name].exists():
                print(f"❌ Directory does not exist: {dirs[dir_name]}")
                return False
        
        print("✅ Directory setup successful")
        return True
        
    except Exception as e:
        print(f"❌ Directory setup failed: {e}")
        return False

def test_data_validation():
    """Test data validation functions."""
    print("Testing data validation...")
    
    # Test valid funding data
    valid_funding = {
        "id": "test_001",
        "title": "Test Funding Opportunity",
        "organization": "Test Organization",
        "category": "UKRI",
        "subcategory": "AHRC",
        "description": "A test funding opportunity",
        "eligibility": {
            "career_stage": "Early Career",
            "requirements": ["PhD required"],
            "restrictions": []
        },
        "funding_details": {
            "amount": {
                "min": 50000,
                "max": 100000,
                "currency": "GBP"
            },
            "duration": {
                "min_months": 12,
                "max_months": 24
            },
            "type": "Grant"
        },
        "application": {
            "deadline": "2024-12-31",
            "process": "Online application",
            "requirements": ["Research proposal"]
        },
        "key_info": {
            "highlights": ["Competitive funding"],
            "notes": ["Annual call"]
        },
        "contact": {
            "email": "test@example.com",
            "phone": "+44 123 456 7890",
            "website": "https://example.com"
        },
        "tags": ["research", "grant"],
        "last_updated": datetime.now().isoformat(),
        "scrape_source": "test",
        "status": "active"
    }
    
    try:
        if validate_funding_data(valid_funding):
            print("✅ Valid funding data passed validation")
        else:
            print("❌ Valid funding data failed validation")
            return False
        
        # Test invalid funding data
        invalid_funding = {"id": "test_002"}  # Missing required fields
        
        if not validate_funding_data(invalid_funding):
            print("✅ Invalid funding data correctly rejected")
        else:
            print("❌ Invalid funding data incorrectly accepted")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Data validation test failed: {e}")
        return False

def test_scraper_initialization():
    """Test that scrapers can be initialized."""
    print("Testing scraper initialization...")
    
    scrapers = {
        'UKRI': UKRIScraper,
        'Academies': AcademiesScraper,
        'Foundations': FoundationsScraper
    }
    
    try:
        for name, scraper_class in scrapers.items():
            scraper = scraper_class()
            if hasattr(scraper, 'base_urls') and scraper.base_urls:
                print(f"✅ {name} scraper initialized successfully")
            else:
                print(f"❌ {name} scraper missing base_urls")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Scraper initialization failed: {e}")
        return False

def test_sample_data_loading():
    """Test loading of sample data."""
    print("Testing sample data loading...")
    
    try:
        sample_file = Path('data/individual_fundings/sample_funding.json')
        
        if not sample_file.exists():
            print(f"❌ Sample file not found: {sample_file}")
            return False
        
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        if validate_funding_data(sample_data):
            print("✅ Sample data loaded and validated successfully")
            return True
        else:
            print("❌ Sample data validation failed")
            return False
        
    except Exception as e:
        print(f"❌ Sample data loading failed: {e}")
        return False

def test_database_structure():
    """Test the main database structure."""
    print("Testing database structure...")
    
    try:
        db_file = Path('data/funding_database.json')
        
        if not db_file.exists():
            print(f"❌ Database file not found: {db_file}")
            return False
        
        with open(db_file, 'r', encoding='utf-8') as f:
            database = json.load(f)
        
        required_fields = ['last_updated', 'total_fundings', 'categories', 'fundings']
        
        for field in required_fields:
            if field not in database:
                print(f"❌ Missing required field in database: {field}")
                return False
        
        print("✅ Database structure is valid")
        return True
        
    except Exception as e:
        print(f"❌ Database structure test failed: {e}")
        return False

def test_web_interface():
    """Test that web interface files exist."""
    print("Testing web interface files...")
    
    required_files = [
        'index.html',
        'css/style.css',
        'js/main.js'
    ]
    
    try:
        for file_path in required_files:
            file_obj = Path(file_path)
            if not file_obj.exists():
                print(f"❌ Missing web interface file: {file_path}")
                return False
            
            if file_obj.stat().st_size == 0:
                print(f"❌ Empty web interface file: {file_path}")
                return False
        
        print("✅ Web interface files exist and are not empty")
        return True
        
    except Exception as e:
        print(f"❌ Web interface test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("🧪 Running UK Funding Tracker Tests\n")
    print("=" * 50)
    
    tests = [
        ("Directory Setup", test_directory_setup),
        ("Data Validation", test_data_validation),
        ("Scraper Initialization", test_scraper_initialization),
        ("Sample Data Loading", test_sample_data_loading),
        ("Database Structure", test_database_structure),
        ("Web Interface Files", test_web_interface)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The project is ready for deployment.")
        return True
    else:
        print(f"❌ {total - passed} test(s) failed. Please fix the issues before deployment.")
        return False

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test UK Funding Tracker')
    parser.add_argument('--test', choices=[
        'directories', 'validation', 'scrapers', 'sample', 'database', 'web', 'all'
    ], default='all', help='Specific test to run')
    
    args = parser.parse_args()
    
    if args.test == 'all':
        success = run_all_tests()
    elif args.test == 'directories':
        success = test_directory_setup()
    elif args.test == 'validation':
        success = test_data_validation()
    elif args.test == 'scrapers':
        success = test_scraper_initialization()
    elif args.test == 'sample':
        success = test_sample_data_loading()
    elif args.test == 'database':
        success = test_database_structure()
    elif args.test == 'web':
        success = test_web_interface()
    else:
        print(f"Unknown test: {args.test}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()