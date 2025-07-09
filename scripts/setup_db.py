#!/usr/bin/env python3
"""
Database setup script for SEC Filing Analyzer
Run this script to initialize the database and create tables.
"""

import os
import sys
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import init_database, DatabaseManager
from config import COMPANIES_FILE, DATA_DIR

def setup_database():
    """Initialize database and create tables"""
    print("🔧 Setting up database...")
    
    try:
        # Initialize database tables
        init_database()
        print("✅ Database tables created successfully")
        
        # Create sample companies file if it doesn't exist
        create_sample_companies_file()
        
        print("✅ Database setup complete!")
        print(f"📁 Database location: {os.path.abspath('sec_filings.db')}")
        print(f"📁 Data directory: {DATA_DIR}")
        
    except Exception as e:
        print(f"❌ Error setting up database: {str(e)}")
        sys.exit(1)

def create_sample_companies_file():
    """Create sample companies.json file"""
    if not COMPANIES_FILE.exists():
        sample_companies = [
            {
                "name": "Apple Inc.",
                "cik": "0000320193",
                "symbol": "AAPL"
            },
            {
                "name": "Microsoft Corporation",
                "cik": "0000789019", 
                "symbol": "MSFT"
            },
            {
                "name": "Amazon.com Inc.",
                "cik": "0000018542",
                "symbol": "AMZN"
            },
            {
                "name": "Alphabet Inc.",
                "cik": "0001652044",
                "symbol": "GOOGL"
            },
            {
                "name": "Tesla, Inc.",
                "cik": "0001318605",
                "symbol": "TSLA"
            }
        ]
        
        with open(COMPANIES_FILE, 'w') as f:
            json.dump(sample_companies, f, indent=2)
        
        print(f"✅ Created sample companies file: {COMPANIES_FILE}")

def test_database_connection():
    """Test database connection and operations"""
    print("🧪 Testing database connection...")
    
    try:
        with DatabaseManager() as db:
            # Test creating a company
            test_company = db.get_or_create_company(
                name="Test Company",
                cik="0000000001",
                symbol="TEST"
            )
            
            print(f"✅ Test company created: {test_company.name}")
            
            # Test querying companies
            companies = db.get_all_companies()
            print(f"✅ Found {len(companies)} companies in database")
            
            # Clean up test company
            db.db.delete(test_company)
            db.db.commit()
            print("✅ Test company cleaned up")
            
    except Exception as e:
        print(f"❌ Database connection test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 SEC Filing Analyzer - Database Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("backend"):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Setup database
    setup_database()
    
    # Test connection
    test_database_connection()
    
    print("\n🎉 Setup complete! You can now run the application.")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and fill in your API keys")
    print("2. Run 'python scripts/seed_companies.py' to add sample companies")
    print("3. Run 'uvicorn backend.main:app --reload' to start the API")