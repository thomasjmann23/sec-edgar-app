#!/usr/bin/env python3
"""
Direct test to download and process Apple's 10-K filing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'backend'))

import requests
from bs4 import BeautifulSoup
import time

def download_apple_10k():
    """Download Apple's latest 10-K filing directly"""
    
    # Apple's latest 10-K filing URL (from SEC website)
    # This is the direct link to the actual filing document
    apple_10k_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
    
    print(f"📥 Downloading Apple 10-K directly from: {apple_10k_url}")
    
    # Set up headers
    headers = {
        'User-Agent': 'SEC-Filing-Analyzer Thomas Mann thomasjmann23@gmail.com'
    }
    
    # Download the filing
    try:
        response = requests.get(apple_10k_url, headers=headers)
        response.raise_for_status()
        
        # Save to file
        file_path = Path("data/filings/apple_10k_direct.html")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✅ Downloaded {len(response.text)} characters to {file_path}")
        return file_path, response.text
        
    except Exception as e:
        print(f"❌ Error downloading filing: {e}")
        return None, None

def test_with_real_filing():
    """Test our inline XBRL handler with the real filing"""
    
    # Download the filing
    file_path, content = download_apple_10k()
    
    if not content:
        print("❌ Failed to download filing")
        return
    
    # Quick content check
    print(f"\n📊 Content Analysis:")
    print(f"  File size: {len(content):,} characters")
    print(f"  Contains 'contextref': {'contextref' in content}")
    print(f"  Contains 'xbrl': {'xbrl' in content.lower()}")
    print(f"  Contains 'table': {'<table' in content}")
    print(f"  Contains 'Item 1A': {'Item 1A' in content}")
    print(f"  Contains 'Risk Factors': {'Risk Factors' in content}")
    
    # Test inline XBRL handler
    from services.inline_xbrl_handler import InlineXBRLHandler
    
    handler = InlineXBRLHandler(content)
    summary = handler.get_summary()
    
    print(f"\n📊 Inline XBRL Handler Results:")
    print(f"  Total facts: {summary['total_facts']}")
    print(f"  Total tables: {summary['total_tables']}")
    print(f"  Total sections: {summary['total_sections']}")
    print(f"  Table types: {summary['table_types']}")
    print(f"  Section types: {summary['section_types']}")
    
    if summary['sample_facts']:
        print(f"\n🔍 Sample Facts:")
        for fact in summary['sample_facts'][:3]:
            print(f"  {fact['concept']}: {fact['value']}")
    
    # Test basic HTML parsing
    soup = BeautifulSoup(content, 'html.parser')
    
    # Look for section headers
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4'])
    section_headers = []
    for header in headers[:10]:  # First 10 headers
        text = header.get_text(strip=True)
        if text and len(text) < 100:
            section_headers.append(text)
    
    print(f"\n📋 Section Headers Found:")
    for header in section_headers:
        print(f"  - {header}")
    
    # Look for tables
    tables = soup.find_all('table')
    print(f"\n📊 Found {len(tables)} tables in the filing")
    
    if tables:
        print(f"  First table preview:")
        first_table = tables[0]
        rows = first_table.find_all('tr')[:3]  # First 3 rows
        for i, row in enumerate(rows):
            cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
            if cells:
                print(f"    Row {i+1}: {cells[:4]}")  # First 4 cells

if __name__ == "__main__":
    print("🍎 Direct Apple 10-K Filing Test")
    print("=" * 50)
    
    test_with_real_filing()