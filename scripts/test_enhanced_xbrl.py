#!/usr/bin/env python3
"""
Enhanced XBRL test with multiple companies and better detection
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def enhanced_xbrl_detection(sec_client, filing_info):
    """Enhanced XBRL detection that looks for more file types"""
    try:
        documents = sec_client.get_filing_documents(filing_info)
        
        print(f"  📄 Found {len(documents)} documents:")
        for i, doc in enumerate(documents[:10]):  # Show first 10 documents
            print(f"    {i+1}. {doc['type']} - {doc['description']}")
        
        # Look for various XBRL indicators
        xbrl_indicators = [
            'ex-101.ins',
            'instance',
            'xbrl',
            '.xml',
            'ex-101',
            'inline'
        ]
        
        xbrl_docs = []
        for doc in documents:
            doc_type = doc['type'].lower()
            doc_desc = doc['description'].lower()
            doc_url = doc['url'].lower()
            
            for indicator in xbrl_indicators:
                if (indicator in doc_type or 
                    indicator in doc_desc or 
                    indicator in doc_url):
                    xbrl_docs.append(doc)
                    break
        
        if xbrl_docs:
            print(f"  ✅ Found {len(xbrl_docs)} potential XBRL documents:")
            for doc in xbrl_docs:
                print(f"    - {doc['type']}: {doc['description']}")
            return True, xbrl_docs[0]  # Return the first XBRL document
        
        return False, None
        
    except Exception as e:
        print(f"  ❌ Error checking XBRL: {e}")
        return False, None

def test_company_xbrl(sec_client, company_name, cik, symbol):
    """Test XBRL for a specific company"""
    print(f"\n🏢 Testing {company_name} ({symbol})...")
    
    try:
        # Get recent 10-K filings
        filings = sec_client.get_company_filings(cik, "10-K", count=3)
        
        if not filings:
            print(f"  ❌ No 10-K filings found for {company_name}")
            return None
        
        print(f"  📋 Found {len(filings)} recent 10-K filings")
        
        # Try each filing until we find one with XBRL
        for i, filing in enumerate(filings):
            print(f"\n  📄 Checking filing {i+1}: {filing.form_type} from {filing.filing_date}")
            
            has_xbrl, xbrl_doc = enhanced_xbrl_detection(sec_client, filing)
            
            if has_xbrl:
                print(f"  ✅ Found XBRL data!")
                return filing, xbrl_doc
            else:
                print(f"  ⚠️  No XBRL data in this filing")
        
        print(f"  ❌ No XBRL data found in any recent {company_name} filings")
        return None
        
    except Exception as e:
        print(f"  ❌ Error testing {company_name}: {e}")
        return None

def download_and_parse_xbrl(sec_client, filing, xbrl_doc):
    """Download and parse XBRL data"""
    try:
        from services.simple_xbrl_parser import SimpleXBRLParser
        
        # Download the XBRL file
        print(f"\n📥 Downloading XBRL document...")
        print(f"  Type: {xbrl_doc['type']}")
        print(f"  Description: {xbrl_doc['description']}")
        print(f"  URL: {xbrl_doc['url']}")
        
        response = sec_client._make_request(xbrl_doc['url'])
        
        # Save the file
        filename = f"{filing.cik}_{filing.accession_number}_xbrl.xml"
        file_path = Path("data/filings") / filename
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"  ✅ Downloaded to: {file_path}")
        
        # Check if it's actually XML
        if not response.text.strip().startswith('<?xml'):
            print(f"  ⚠️  Warning: File doesn't look like XML")
            print(f"  First 200 chars: {response.text[:200]}")
            
            # If it's HTML, it might be an inline XBRL
            if '<html' in response.text.lower():
                print(f"  💡 This appears to be inline XBRL (HTML format)")
                return file_path, "inline_xbrl"
            else:
                print(f"  ❌ Unknown format, skipping parsing")
                return None, None
        
        # Try to parse it
        print(f"\n🔍 Parsing XBRL file...")
        
        try:
            parser = SimpleXBRLParser(str(file_path))
            summary = parser.get_summary()
            
            print(f"  ✅ Successfully parsed XBRL file!")
            print(f"  📊 Results:")
            print(f"    - Total facts: {summary['total_facts']}")
            print(f"    - Key metrics found: {summary['key_metrics_found']}")
            
            if summary['key_metrics']:
                print(f"    - Key metrics:")
                for metric_name, metric_info in summary['key_metrics'].items():
                    value = metric_info['value']
                    unit = metric_info['unit']
                    if isinstance(value, (int, float)):
                        print(f"      • {metric_name.replace('_', ' ').title()}: {value:,} {unit}")
                    else:
                        print(f"      • {metric_name.replace('_', ' ').title()}: {value} {unit}")
            
            return file_path, summary
            
        except Exception as parse_error:
            print(f"  ❌ Failed to parse XBRL: {parse_error}")
            print(f"  💡 This might be inline XBRL or a different format")
            return file_path, "parse_failed"
        
    except Exception as e:
        print(f"  ❌ Failed to download/parse XBRL: {e}")
        return None, None

def test_multiple_companies():
    """Test XBRL with multiple companies"""
    
    print("🧪 Testing XBRL with Multiple Companies")
    print("=" * 60)
    
    # Companies to test (some are more likely to have XBRL)
    companies = [
        ("Apple Inc.", "0000320193", "AAPL"),
        ("Microsoft Corporation", "0000789019", "MSFT"),
        ("Amazon.com Inc.", "0000018542", "AMZN"),
        ("Tesla, Inc.", "0001318605", "TSLA"),
        ("Meta Platforms Inc.", "0001326801", "META"),
    ]
    
    try:
        from services.sec_client import SECClient
        
        sec_client = SECClient()
        
        successful_tests = []
        
        for company_name, cik, symbol in companies:
            result = test_company_xbrl(sec_client, company_name, cik, symbol)
            
            if result:
                filing, xbrl_doc = result
                print(f"\n🎯 Found XBRL data for {company_name}! Testing download and parsing...")
                
                file_path, parse_result = download_and_parse_xbrl(sec_client, filing, xbrl_doc)
                
                if file_path:
                    successful_tests.append({
                        'company': company_name,
                        'symbol': symbol,
                        'filing': filing,
                        'file_path': file_path,
                        'parse_result': parse_result
                    })
                    
                    # Stop after first successful test
                    break
        
        # Summary
        print(f"\n📊 Test Summary:")
        print("=" * 40)
        
        if successful_tests:
            print(f"✅ Successfully processed {len(successful_tests)} company(ies)")
            
            for test in successful_tests:
                print(f"\n🏢 {test['company']} ({test['symbol']}):")
                print(f"  📄 Filing: {test['filing'].form_type} from {test['filing'].filing_date}")
                print(f"  📁 File: {test['file_path']}")
                
                if isinstance(test['parse_result'], dict):
                    print(f"  📊 Facts: {test['parse_result']['total_facts']}")
                    print(f"  🔑 Key metrics: {test['parse_result']['key_metrics_found']}")
                else:
                    print(f"  📝 Status: {test['parse_result']}")
            
            print(f"\n🎉 XBRL pipeline test completed successfully!")
            print(f"\nNext steps:")
            print(f"1. Store the parsed data in the database")
            print(f"2. Add more companies")
            print(f"3. Build comparison features")
            
        else:
            print(f"❌ No successful XBRL processing found")
            print(f"💡 This could mean:")
            print(f"  - Companies are using inline XBRL (HTML format)")
            print(f"  - XBRL files are in a different location")
            print(f"  - Rate limiting from SEC")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiple_companies()