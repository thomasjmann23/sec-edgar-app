#!/usr/bin/env python3
"""
Test script to verify the system is working correctly
"""
import sys
import requests
import time
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import DatabaseManager
from services.sec_client import SECClient
from services.parser import FilingParser
from config import settings

def test_database():
    """Test database connection and operations"""
    print("🗄️  Testing database...")
    
    try:
        with DatabaseManager() as db:
            companies = db.get_all_companies()
            print(f"  ✅ Database connected - found {len(companies)} companies")
            
            if companies:
                company = companies[0]
                filings = db.get_company_filings(company.id)
                print(f"  ✅ Found {len(filings)} filings for {company.name}")
            
            return True
    except Exception as e:
        print(f"  ❌ Database test failed: {str(e)}")
        return False

def test_sec_client():
    """Test SEC client functionality"""
    print("🌐 Testing SEC client...")
    
    try:
        client = SECClient()
        
        # Test with Apple (known to have filings)
        apple_cik = "0000320193"
        filings = client.get_company_filings(apple_cik, "10-K", count=1)
        
        if filings:
            print(f"  ✅ Successfully fetched {len(filings)} filing(s) for Apple")
            print(f"  📄 Latest filing: {filings[0].form_type} ({filings[0].filing_date})")
            return True
        else:
            print("  ⚠️  No filings found (may be rate limited)")
            return False
            
    except Exception as e:
        print(f"  ❌ SEC client test failed: {str(e)}")
        return False

def test_parser():
    """Test HTML parser with sample content"""
    print("📝 Testing HTML parser...")
    
    try:
        # Create a simple test HTML
        test_html = """
        <html>
        <head><title>Test Filing</title></head>
        <body>
            <h1>FORM 10-K</h1>
            <h2>Item 1A - Risk Factors</h2>
            <p>Our business faces various risks including market volatility, 
            regulatory changes, and competitive pressures. These risks could 
            materially affect our financial results.</p>
            
            <h2>Item 1 - Business</h2>
            <p>We operate in the technology sector, developing innovative 
            solutions for our customers worldwide.</p>
            
            <table>
                <tr><th>Assets</th><th>2023</th><th>2022</th></tr>
                <tr><td>Cash</td><td>$100M</td><td>$80M</td></tr>
                <tr><td>Total Assets</td><td>$500M</td><td>$450M</td></tr>
            </table>
        </body>
        </html>
        """
        
        parser = FilingParser(html_content=test_html)
        sections = parser.extract_all_sections()
        
        if sections:
            print(f"  ✅ Successfully parsed {len(sections)} sections")
            for section_type in sections.keys():
                print(f"    - {section_type}")
            return True
        else:
            print("  ⚠️  No sections extracted")
            return False
            
    except Exception as e:
        print(f"  ❌ Parser test failed: {str(e)}")
        return False

def test_api(port=8000):
    """Test API endpoints"""
    print("🚀 Testing API endpoints...")
    
    base_url = f"http://localhost:{port}"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("  ✅ Health endpoint working")
        else:
            print(f"  ❌ Health endpoint returned {response.status_code}")
            return False
        
        # Test companies endpoint
        response = requests.get(f"{base_url}/companies", timeout=5)
        if response.status_code == 200:
            companies = response.json()
            print(f"  ✅ Companies endpoint working - found {len(companies)} companies")
        else:
            print(f"  ❌ Companies endpoint returned {response.status_code}")
            return False
        
        # Test filings endpoint
        response = requests.get(f"{base_url}/filings?limit=5", timeout=5)
        if response.status_code == 200:
            filings = response.json()
            print(f"  ✅ Filings endpoint working - found {len(filings)} filings")
        else:
            print(f"  ❌ Filings endpoint returned {response.status_code}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("  ❌ API not running - start with 'uvicorn backend.main:app --reload'")
        return False
    except Exception as e:
        print(f"  ❌ API test failed: {str(e)}")
        return False

def test_config():
    """Test configuration"""
    print("⚙️  Testing configuration...")
    
    try:
        # Check required settings
        if not settings.GEMINI_API_KEY:
            print("  ⚠️  GEMINI_API_KEY not set (required for analysis)")
        else:
            print("  ✅ GEMINI_API_KEY configured")
        
        if "contact@example.com" in settings.SEC_USER_AGENT:
            print("  ⚠️  SEC_USER_AGENT still has default email")
        else:
            print("  ✅ SEC_USER_AGENT configured")
        
        print(f"  ✅ Database URL: {settings.DATABASE_URL}")
        print(f"  ✅ API will run on: {settings.API_HOST}:{settings.API_PORT}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {str(e)}")
        return False

def run_integration_test():
    """Run a full integration test"""
    print("🔄 Running integration test...")
    
    try:
        # Test the full pipeline with a known company
        with DatabaseManager() as db:
            # Get or create a test company
            test_company = db.get_or_create_company(
                name="Apple Inc.",
                cik="0000320193",
                symbol="AAPL"
            )
            
            print(f"  ✅ Test company: {test_company.name}")
            
            # Try to get latest filing (without downloading to avoid rate limits)
            sec_client = SECClient()
            latest_filing = sec_client.get_latest_filing(test_company.cik, "10-K")
            
            if latest_filing:
                print(f"  ✅ Found latest filing: {latest_filing.form_type} ({latest_filing.filing_date})")
                
                # Check if we already have this filing
                existing = db.get_filing_by_accession(latest_filing.accession_number)
                if not existing:
                    print("  ✅ This would be a new filing to process")
                else:
                    print("  ✅ Filing already exists in database")
                
                return True
            else:
                print("  ⚠️  No recent filings found (may be rate limited)")
                return False
                
    except Exception as e:
        print(f"  ❌ Integration test failed: {str(e)}")
        return False

def print_getting_started():
    """Print getting started instructions"""
    print("\n🎯 Getting Started:")
    print("=" * 50)
    print("1. Make sure you have a .env file with your API keys:")
    print("   GEMINI_API_KEY=your_key_here")
    print("   SEC_USER_AGENT=YourApp your-email@example.com")
    print()
    print("2. Seed the database with sample companies:")
    print("   python scripts/seed_companies.py --all")
    print()
    print("3. Start the API server:")
    print("   uvicorn backend.main:app --reload")
    print()
    print("4. Test the API in your browser:")
    print("   http://localhost:8000/docs")
    print()
    print("5. Build the React frontend (next step)")

def main():
    """Main test function"""
    print("🧪 SEC Filing Analyzer - System Test")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_config),
        ("Database", test_database),
        ("SEC Client", test_sec_client),
        ("HTML Parser", test_parser),
        ("Integration", run_integration_test)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        results[test_name] = test_func()
        time.sleep(1)  # Brief pause between tests
    
    # Test API if it's running
    print(f"\nAPI Server:")
    print("-" * 20)
    results["API Server"] = test_api()
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<15} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your system is ready to go.")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Check the errors above.")
    
    # Print getting started guide if basic tests pass
    if results.get("Configuration") and results.get("Database"):
        print_getting_started()

if __name__ == "__main__":
    main()