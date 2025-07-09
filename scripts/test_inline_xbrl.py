#!/usr/bin/env python3
"""
Test inline XBRL parsing with real SEC filings
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def test_inline_xbrl():
    """Test inline XBRL parsing with real filings"""
    
    print("🧪 Testing Inline XBRL with Real SEC Filings")
    print("=" * 60)
    
    # Companies to test
    companies = [
        ("Apple Inc.", "0000320193", "AAPL"),
        ("Microsoft Corporation", "0000789019", "MSFT"),
        ("Tesla, Inc.", "0001318605", "TSLA"),
    ]
    
    try:
        from services.sec_client import SECClient
        from services.inline_xbrl_parser import InlineXBRLParser
        from database import DatabaseManager
        
        sec_client = SECClient()
        successful_tests = []
        
        for company_name, cik, symbol in companies:
            print(f"\n🏢 Testing {company_name} ({symbol})...")
            
            try:
                # Get recent filing
                filings = sec_client.get_company_filings(cik, "10-K", count=1)
                
                if not filings:
                    print(f"  ❌ No filings found")
                    continue
                
                filing = filings[0]
                print(f"  📄 Found filing: {filing.form_type} from {filing.filing_date}")
                
                # Download HTML filing
                print(f"  📥 Downloading HTML filing...")
                html_path = sec_client.download_filing_html(filing)
                
                if not html_path:
                    print(f"  ❌ Failed to download HTML")
                    continue
                
                print(f"  ✅ Downloaded to: {html_path}")
                
                # Parse inline XBRL
                print(f"  🔍 Parsing inline XBRL...")
                parser = InlineXBRLParser(html_file_path=html_path)
                
                if not parser.has_xbrl_data():
                    print(f"  ⚠️  No inline XBRL data found")
                    continue
                
                summary = parser.get_summary()
                
                print(f"  ✅ Found inline XBRL data!")
                print(f"    - Total facts: {summary['total_facts']}")
                print(f"    - Key metrics: {summary['key_metrics_found']}")
                print(f"    - Data types: {summary['data_types']}")
                
                # Show key metrics
                if summary['key_metrics']:
                    print(f"  📊 Key Financial Metrics:")
                    for metric_name, metric_info in summary['key_metrics'].items():
                        value = metric_info['value']
                        unit = metric_info['unit'] or ''
                        if isinstance(value, (int, float)):
                            print(f"    • {metric_name.replace('_', ' ').title()}: ${value:,.0f}" if 'usd' in unit.lower() else f"    • {metric_name.replace('_', ' ').title()}: {value:,} {unit}")
                        else:
                            print(f"    • {metric_name.replace('_', ' ').title()}: {value} {unit}")
                
                # Store in database
                print(f"  💾 Storing in database...")
                
                with DatabaseManager() as db:
                    # Get or create company
                    company = db.get_or_create_company(
                        name=company_name,
                        cik=cik,
                        symbol=symbol
                    )
                    
                    # Create filing record
                    db_filing = db.create_filing(
                        company_id=company.id,
                        form_type=filing.form_type,
                        filing_date=filing.filing_date,
                        accession_number=filing.accession_number,
                        document_url=filing.document_url
                    )
                    
                    # Update with XBRL info
                    db_filing.html_file_path = html_path
                    db_filing.has_xbrl = True
                    db_filing.xbrl_processed = True
                    db.db.commit()
                    
                    # Store key facts
                    facts_stored = 0
                    for metric_name, metric_info in summary['key_metrics'].items():
                        try:
                            fact = db.create_xbrl_fact(
                                filing_id=db_filing.id,
                                concept_name=metric_info['concept'],
                                value=str(metric_info['value']),
                                unit_ref=metric_info['unit'] or '',
                                is_monetary='usd' in (metric_info['unit'] or '').lower()
                            )
                            facts_stored += 1
                        except Exception as e:
                            print(f"    ⚠️  Failed to store fact {metric_name}: {e}")
                    
                    print(f"  ✅ Stored filing (ID: {db_filing.id}) with {facts_stored} key facts")
                
                successful_tests.append({
                    'company': company_name,
                    'symbol': symbol,
                    'filing': filing,
                    'html_path': html_path,
                    'summary': summary
                })
                
                # Stop after first successful test to avoid rate limiting
                break
                
            except Exception as e:
                print(f"  ❌ Error testing {company_name}: {e}")
                continue
        
        # Summary
        print(f"\n📊 Test Results:")
        print("=" * 40)
        
        if successful_tests:
            print(f"✅ Successfully processed {len(successful_tests)} company(ies)")
            
            for test in successful_tests:
                print(f"\n🏢 {test['company']} ({test['symbol']}):")
                print(f"  📄 Filing: {test['filing'].form_type} from {test['filing'].filing_date}")
                print(f"  📁 HTML file: {test['html_path']}")
                print(f"  📊 XBRL facts: {test['summary']['total_facts']}")
                print(f"  🔑 Key metrics: {test['summary']['key_metrics_found']}")
            
            print(f"\n🎉 Inline XBRL pipeline test completed successfully!")
            print(f"\n✅ What we accomplished:")
            print(f"  ✓ Downloaded real SEC HTML filings")
            print(f"  ✓ Parsed inline XBRL data from HTML")
            print(f"  ✓ Extracted key financial metrics")
            print(f"  ✓ Stored data in database")
            
            print(f"\n🚀 Next steps:")
            print(f"  1. Add more companies to database")
            print(f"  2. Create comparison features")
            print(f"  3. Build search and analysis tools")
            print(f"  4. Add frontend interface")
            
        else:
            print(f"❌ No successful inline XBRL processing found")
            print(f"💡 This could mean:")
            print(f"  - Rate limiting from SEC")
            print(f"  - Different HTML structure than expected")
            print(f"  - Network connectivity issues")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_inline_xbrl()