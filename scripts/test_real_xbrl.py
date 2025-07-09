#!/usr/bin/env python3
"""
Test with real XBRL data (simplified version)
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def test_real_xbrl_data():
    """Test downloading and parsing real XBRL data"""
    
    print("🧪 Testing with Real XBRL Data")
    print("=" * 50)
    
    try:
        from services.sec_client import SECClient
        from services.simple_xbrl_parser import SimpleXBRLParser
        from database import DatabaseManager
        
        # Step 1: Get a recent filing
        print("\n1. Getting recent Apple 10-K filing...")
        
        sec_client = SECClient()
        filings = sec_client.get_company_filings("0000320193", "10-K", count=1)
        
        if not filings:
            print("❌ No filings found")
            return False
        
        filing = filings[0]
        print(f"✅ Found filing: {filing.form_type} from {filing.filing_date}")
        
        # Step 2: Check if it has XBRL
        print("\n2. Checking for XBRL data...")
        
        has_xbrl = sec_client.check_filing_has_xbrl(filing)
        print(f"✅ XBRL available: {has_xbrl}")
        
        if not has_xbrl:
            print("⚠️  This filing doesn't have XBRL data")
            print("Let's try a different year...")
            
            # Try 2023
            filings_2023 = sec_client.get_company_filings("0000320193", "10-K", count=5)
            for f in filings_2023:
                if "2023" in str(f.filing_date):
                    filing = f
                    has_xbrl = sec_client.check_filing_has_xbrl(filing)
                    print(f"Trying filing from {filing.filing_date}: XBRL = {has_xbrl}")
                    if has_xbrl:
                        break
        
        if not has_xbrl:
            print("❌ No XBRL data found in recent filings")
            return False
        
        # Step 3: Download XBRL file
        print("\n3. Downloading XBRL file...")
        
        xbrl_file_path = sec_client.download_xbrl_for_filing(filing)
        
        if not xbrl_file_path:
            print("❌ Failed to download XBRL file")
            return False
        
        print(f"✅ Downloaded XBRL file: {xbrl_file_path}")
        
        # Step 4: Parse XBRL file
        print("\n4. Parsing XBRL file...")
        
        parser = SimpleXBRLParser(xbrl_file_path)
        summary = parser.get_summary()
        
        print(f"✅ Parsed XBRL file successfully")
        print(f"  - Total facts: {summary['total_facts']}")
        print(f"  - Key metrics found: {summary['key_metrics_found']}")
        
        # Print key metrics
        if summary['key_metrics']:
            print("\n📊 Key Financial Metrics:")
            for metric_name, metric_info in summary['key_metrics'].items():
                value = metric_info['value']
                unit = metric_info['unit']
                if isinstance(value, (int, float)):
                    print(f"  - {metric_name.replace('_', ' ').title()}: {value:,} {unit}")
                else:
                    print(f"  - {metric_name.replace('_', ' ').title()}: {value} {unit}")
        
        # Step 5: Store in database (basic version)
        print("\n5. Storing in database...")
        
        with DatabaseManager() as db:
            # Get or create company
            company = db.get_or_create_company(
                name=filing.company_name,
                cik=filing.cik,
                symbol="AAPL"  # We know this is Apple
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
            db_filing.xbrl_file_path = xbrl_file_path
            db_filing.has_xbrl = True
            db_filing.xbrl_processed = True
            db.db.commit()
            
            print(f"✅ Stored filing in database (ID: {db_filing.id})")
            
            # Store some key facts
            facts_stored = 0
            for metric_name, metric_info in summary['key_metrics'].items():
                try:
                    fact = db.create_xbrl_fact(
                        filing_id=db_filing.id,
                        concept_name=metric_info['concept'],
                        value=str(metric_info['value']),
                        unit_ref=metric_info['unit'],
                        is_monetary=metric_info['unit'] == 'USD'
                    )
                    facts_stored += 1
                except Exception as e:
                    print(f"⚠️  Failed to store fact {metric_name}: {e}")
            
            print(f"✅ Stored {facts_stored} key facts in database")
        
        print("\n🎉 Full XBRL pipeline test completed successfully!")
        print("\nNext steps:")
        print("1. Add more companies")
        print("2. Create comparison features")
        print("3. Build frontend interface")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_real_xbrl_data()