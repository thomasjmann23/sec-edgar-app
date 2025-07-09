#!/usr/bin/env python3
"""
Simple test script to verify XBRL setup is working
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
        from database import DatabaseManager, XBRLFact, XBRLConcept, FinancialStatement
        
        with DatabaseManager() as db:
            # Test that we can query the new tables
            facts = db.db.query(XBRLFact).limit(1).all()
            concepts = db.db.query(XBRLConcept).limit(1).all()
            statements = db.db.query(FinancialStatement).limit(1).all()
            
            print(f"✅ Database setup successful")
            print(f"  - XBRLFact table: {len(facts)} records")
            print(f"  - XBRLConcept table: {len(concepts)} records")
            print(f"  - FinancialStatement table: {len(statements)} records")
            
            return True
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def test_dependencies():
    """Test that all required packages are installed"""
    print("📦 Testing dependencies...")
    
    required_packages = [
        "sentence_transformers",
        "chromadb",
        "arelle",
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {missing_packages}")
        print("Run: pip install " + " ".join(missing_packages))
        return False
    
    return True

def test_basic_functionality():
    """Test basic XBRL functionality"""
    print("🧪 Testing basic XBRL functionality...")
    
    try:
        # Test that we can import the sentence transformer
        from sentence_transformers import SentenceTransformer
        
        # Test loading a small model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Test encoding a simple sentence
        embedding = model.encode("This is a test sentence")
        
        print(f"✅ Sentence transformer working (embedding size: {len(embedding)})")
        
        # Test ChromaDB
        import chromadb
        client = chromadb.Client()
        collection = client.create_collection("test_collection")
        
        # Add a simple document
        collection.add(
            documents=["This is a test document"],
            metadatas=[{"source": "test"}],
            ids=["test_1"]
        )
        
        # Query it
        results = collection.query(
            query_texts=["test"],
            n_results=1
        )
        
        print(f"✅ ChromaDB working (found {len(results['documents'][0])} documents)")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing XBRL Setup")
    print("=" * 50)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Database Setup", test_database_setup),
        ("Basic Functionality", test_basic_functionality),
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
        print("\n🎉 All tests passed! Your XBRL setup is working.")
        print("\nNext steps:")
        print("1. Create the XBRL service files")
        print("2. Test with a real XBRL filing")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")

if __name__ == "__main__":
    main()