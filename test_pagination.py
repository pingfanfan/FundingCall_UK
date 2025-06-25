#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

def test_ukri_pagination():
    """Test UKRI pagination to understand the URL structure."""
    base_url = "https://www.ukri.org/opportunity/"
    
    # Test different page URLs
    test_urls = [
        "https://www.ukri.org/opportunity/",
        "https://www.ukri.org/opportunity/?page=2",
        "https://www.ukri.org/opportunity/page/2/",
        "https://www.ukri.org/opportunity/?p=2"
    ]
    
    for url in test_urls:
        try:
            print(f"\nTesting URL: {url}")
            response = requests.get(url, timeout=10)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for opportunity links
                opportunity_links = soup.find_all('a', href=re.compile(r'/opportunity/[^/?]+/?$'))
                print(f"Found {len(opportunity_links)} opportunity links")
                
                # Look for pagination elements
                pagination = soup.find_all(['a', 'span'], string=re.compile(r'\d+|next|previous', re.IGNORECASE))
                print(f"Found {len(pagination)} pagination elements")
                
                # Look for "opportunities found" text
                opportunities_text = soup.find(string=re.compile(r'\d+\s+opportunities\s+found', re.IGNORECASE))
                if opportunities_text:
                    print(f"Found text: {opportunities_text.strip()}")
                
                # Print first few opportunity links
                for i, link in enumerate(opportunity_links[:3]):
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        print(f"  Link {i+1}: {full_url}")
                        
        except Exception as e:
            print(f"Error testing {url}: {e}")

if __name__ == "__main__":
    test_ukri_pagination()