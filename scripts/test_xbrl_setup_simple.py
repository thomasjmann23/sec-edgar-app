#!/usr/bin/env python3
"""
Simple test script to verify XBRL setup is working (No ML dependencies)
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

def test_database_setup():
    """Test that the database has the new tables"""
    print("🗄️  Testing database setup...")
    
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            # Test that we can access the database
            companies = db.get_all_companies()
            print(f"✅ Database connection successful")
            print(f"  - Found {len(companies)} companies")
            
            # Test that we can query the filings table
            from database import Filing
            filings = db.db.query(Filing).limit(5).all()
            print(f"  - Found {len(filings)} filings")
            
            return True
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def test_xbrl_dependencies():
    """Test that XBRL-specific packages are installed"""
    print("📦 Testing XBRL dependencies...")
    
    required_packages = [
        ("arelle", "Arelle XBRL processor"),
        ("lxml", "XML processing library"),
    ]
    
    missing_packages = []
    
    for package_name, description in required_packages:
        try:
            __import__(package_name)
            print(f"✅ {package_name} ({description}) installed")
        except ImportError:
            print(f"❌ {package_name} missing")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {missing_packages}")
        print("Run: pip install " + " ".join(missing_packages))
        return False
    
    return True

def test_basic_xml_parsing():
    """Test basic XML parsing functionality"""
    print("🧪 Testing basic XML parsing...")
    
    try:
        import xml.etree.ElementTree as ET
        
        # Create a simple test XML
        test_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <root xmlns:xbrli="http://www.xbrl.org/2003/instance">
            <xbrli:context id="test">
                <xbrli:period>
                    <xbrli:instant>2023-12-31</xbrli:instant>
                </xbrli:period>
            </xbrli:context>
            <TestConcept contextRef="test">1000000</TestConcept>
        </root>"""
        
        # Parse the XML
        root = ET.fromstring(test_xml)
        
        # Find the context
        contexts = root.findall('.//{http://www.xbrl.org/2003/instance}context')
        print(f"✅ Found {len(contexts)} contexts in test XML")
        
        # Find the fact
        facts = [elem for elem in root if not elem.tag.startswith('{http://www.xbrl.org/2003/instance}')]
        print(f"✅ Found {len(facts)} facts in test XML")
        
        return True
        
    except Exception as e:
        print(f"❌ XML parsing test failed: {e}")
        return False

def test_sec_client():
    """Test that SEC client is working"""
    print("🌐 Testing SEC client...")
    
    try:
        from services.sec_client import SECClient
        
        client = SECClient()
        print("✅ SEC client initialized")
        
        # Test with a known company (Apple)
        filings = client.get_company_filings("0000320193", "10-K", count=1)
        
        if filings:
            print(f"✅ Successfully retrieved {len(filings)} filing(s)")
            filing = filings[0]
            print(f"  - Form: {filing.form_type}")
            print(f"  - Date: {filing.filing_date}")
            print(f"  - Company: {filing.company_name}")
            return True
        else:
            print("⚠️  No filings retrieved (might be rate limited)")
            return False
            
    except Exception as e:
        print(f"❌ SEC client test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing XBRL Setup (Simplified)")
    print("=" * 50)
    
    tests = [
        ("XBRL Dependencies", test_xbrl_dependencies),
        ("Database Setup", test_database_setup),
        ("XML Parsing", test_basic_xml_parsing),
        ("SEC Client", test_sec_client),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your simplified XBRL setup is working.")
        print("\nNext steps:")
        print("1. Run the database migration: python scripts/migrate_db_xbrl.py")
        print("2. Test with real XBRL data: python scripts/test_simple_xbrl.py")
        print("3. Add ML features later when core functionality works")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")

if __name__ == "__main__":
    main()