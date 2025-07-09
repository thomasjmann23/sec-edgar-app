#!/usr/bin/env python3
"""
Seed database with sample companies and fetch their latest filings
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Now the imports should work
from database import DatabaseManager, Filing, FilingSection
from config import COMPANIES_FILE
from services.sec_client import SECClient

def load_companies_from_file():
    """Load companies from JSON file"""
    if not COMPANIES_FILE.exists():
        print(f"❌ Companies file not found: {COMPANIES_FILE}")
        print("Run 'python scripts/setup_db.py' first to create the file")
        return []
    
    with open(COMPANIES_FILE, 'r') as f:
        companies = json.load(f)
    
    print(f"📁 Loaded {len(companies)} companies from {COMPANIES_FILE}")
    return companies

def seed_companies():
    """Add companies to the database"""
    print("🌱 Seeding database with companies...")
    
    companies = load_companies_from_file()
    if not companies:
        return
    
    with DatabaseManager() as db:
        for company_data in companies:
            try:
                company = db.get_or_create_company(
                    name=company_data['name'],
                    cik=company_data['cik'],
                    symbol=company_data.get('symbol')
                )
                
                print(f"✅ Added/Updated: {company.name} (CIK: {company.cik})")
                
            except Exception as e:
                print(f"❌ Error adding company {company_data.get('name', 'Unknown')}: {str(e)}")
    
    print("🌱 Company seeding complete!")

def fetch_latest_filings(form_type: str = "10-K", download_html: bool = False):
    """
    Fetch latest filings for all companies in the database
    
    Args:
        form_type: Type of filing to fetch (10-K, 10-Q, etc.)
        download_html: Whether to download the HTML files
    """
    print(f"📄 Fetching latest {form_type} filings for all companies...")
    
    sec_client = SECClient()
    
    with DatabaseManager() as db:
        companies = db.get_all_companies()
        
        for company in companies:
            try:
                print(f"\n📊 Processing {company.name} (CIK: {company.cik})...")
                
                # Get latest filing
                latest_filing = sec_client.get_latest_filing(company.cik, form_type)
                
                if not latest_filing:
                    print(f"  ⚠️  No {form_type} filing found for {company.name}")
                    continue
                
                # Check if we already have this filing
                existing_filing = db.get_filing_by_accession(latest_filing.accession_number)
                if existing_filing:
                    print(f"  ✅ Filing {latest_filing.accession_number} already exists")
                    continue
                
                # Create new filing record
                filing = db.create_filing(
                    company_id=company.id,
                    form_type=latest_filing.form_type,
                    filing_date=latest_filing.filing_date,
                    accession_number=latest_filing.accession_number,
                    document_url=latest_filing.document_url
                )
                
                print(f"  ✅ Added filing: {filing.form_type} ({filing.filing_date})")
                
                # Download HTML if requested
                if download_html:
                    try:
                        html_path = sec_client.download_filing_html(latest_filing)
                        if html_path:
                            filing.html_file_path = html_path
                            db.db.commit()
                            print(f"  📄 Downloaded HTML: {html_path}")
                        else:
                            print(f"  ⚠️  Failed to download HTML for {filing.accession_number}")
                    except Exception as e:
                        print(f"  ❌ Error downloading HTML: {str(e)}")
                
            except Exception as e:
                print(f"❌ Error processing {company.name}: {str(e)}")
                continue
    
    print(f"\n📄 Finished fetching {form_type} filings!")

def parse_downloaded_filings():
    """Parse any downloaded HTML files"""
    print("🔍 Parsing downloaded HTML files...")
    
    from services.parser import FilingParser

    with DatabaseManager() as db:
        # Get all filings that have HTML files but haven't been processed
        filings = db.db.query(Filing).filter(
            Filing.html_file_path.isnot(None),
            Filing.processed == False
        ).all()
        
        for filing in filings:
            try:
                print(f"\n📊 Parsing filing: {filing.form_type} for company_id {filing.company_id}")
                
                if not Path(filing.html_file_path).exists():
                    print(f"  ⚠️  HTML file not found: {filing.html_file_path}")
                    continue
                
                # Parse the filing
                parser = FilingParser(file_path=filing.html_file_path)
                sections = parser.extract_all_sections()
                
                # Save sections to database
                for section_type, content in sections.items():
                    if content and len(content.strip()) > 50:  # Only save substantial content
                        db.create_section(
                            filing_id=filing.id,
                            section_type=section_type,
                            content=content,
                            section_title=section_type.replace('_', ' ').title()
                        )
                        print(f"  ✅ Saved section: {section_type}")
                
                # Mark filing as processed
                filing.processed = True
                db.db.commit()
                
                print(f"  ✅ Processed filing with {len(sections)} sections")
                
            except Exception as e:
                print(f"❌ Error parsing filing {filing.accession_number}: {str(e)}")
                continue
    
    print("\n🔍 Finished parsing filings!")

def show_database_summary():
    """Show a summary of what's in the database"""
    print("\n📊 Database Summary:")
    print("=" * 50)
    
    with DatabaseManager() as db:
        companies = db.get_all_companies()
        print(f"Companies: {len(companies)}")
        
        for company in companies:
            filings = db.get_company_filings(company.id)
            print(f"  {company.name} ({company.symbol}): {len(filings)} filings")
            
            for filing in filings[:3]:  # Show first 3 filings
                sections = db.db.query(FilingSection).filter(
                    FilingSection.filing_id == filing.id
                ).all()
                print(f"    {filing.form_type} ({filing.filing_date.strftime('%Y-%m-%d')}): {len(sections)} sections")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed database with companies and filings')
    parser.add_argument('--companies', action='store_true', help='Seed companies from JSON file')
    parser.add_argument('--filings', action='store_true', help='Fetch latest filings')
    parser.add_argument('--download', action='store_true', help='Download HTML files')
    parser.add_argument('--parse', action='store_true', help='Parse downloaded HTML files')
    parser.add_argument('--all', action='store_true', help='Run all steps')
    parser.add_argument('--form-type', default='10-K', help='Type of filing to fetch (default: 10-K)')
    parser.add_argument('--summary', action='store_true', help='Show database summary')
    
    args = parser.parse_args()
    
    if not any([args.companies, args.filings, args.parse, args.all, args.summary]):
        parser.print_help()
        return
    
    print("🚀 SEC Filing Analyzer - Database Seeding")
    print("=" * 50)
    
    try:
        if args.all or args.companies:
            seed_companies()
        
        if args.all or args.filings:
            fetch_latest_filings(args.form_type, args.download or args.all)
        
        if args.all or args.parse:
            parse_downloaded_filings()
        
        if args.summary:
            show_database_summary()
            
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    
    print("\n🎉 Seeding complete!")

if __name__ == "__main__":
    # For backwards compatibility, run with default behavior if no args
    if len(sys.argv) == 1:
        print("🚀 SEC Filing Analyzer - Database Seeding")
        print("=" * 50)
        print("Running with default options: seed companies and fetch filings")
        print("For more options, run with --help")
        print()
        
        seed_companies()
        fetch_latest_filings("10-K", download_html=True)
        parse_downloaded_filings()
        show_database_summary()
    else:
        main()