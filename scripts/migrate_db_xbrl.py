#!/usr/bin/env python3
"""
Simple database migration script for XBRL support
Run this to add XBRL tables to your existing database
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from database import Base, engine

def add_xbrl_tables():
    """Add XBRL tables to existing database"""
    
    print("🔧 Adding XBRL support to your database...")
    
    try:
        # First, let's add the new columns to the existing filings table
        with engine.connect() as conn:
            # Add new columns one by one (this is safe if they already exist)
            try:
                conn.execute(text("ALTER TABLE filings ADD COLUMN xbrl_file_path VARCHAR(500)"))
                print("✅ Added xbrl_file_path column")
            except Exception:
                print("⚠️  xbrl_file_path column already exists")
            
            try:
                conn.execute(text("ALTER TABLE filings ADD COLUMN filing_summary_path VARCHAR(500)"))
                print("✅ Added filing_summary_path column")
            except Exception:
                print("⚠️  filing_summary_path column already exists")
            
            try:
                conn.execute(text("ALTER TABLE filings ADD COLUMN has_xbrl BOOLEAN DEFAULT FALSE"))
                print("✅ Added has_xbrl column")
            except Exception:
                print("⚠️  has_xbrl column already exists")
            
            try:
                conn.execute(text("ALTER TABLE filings ADD COLUMN xbrl_processed BOOLEAN DEFAULT FALSE"))
                print("✅ Added xbrl_processed column")
            except Exception:
                print("⚠️  xbrl_processed column already exists")
            
            conn.commit()
        
        print("✅ Updated filings table successfully")
        
    except Exception as e:
        print(f"❌ Error updating filings table: {e}")
        return False
    
    return True

def create_new_tables():
    """Create the new XBRL tables"""
    
    print("🏗️  Creating new XBRL tables...")
    
    try:
        # Create the new tables
        Base.metadata.create_all(bind=engine)
        print("✅ Created all new tables successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def main():
    """Main migration function"""
    
    print("🚀 Starting XBRL Database Migration")
    print("=" * 50)
    
    # Step 1: Add new columns to existing table
    if not add_xbrl_tables():
        print("❌ Failed to update existing tables")
        return
    
    # Step 2: Create new tables
    if not create_new_tables():
        print("❌ Failed to create new tables")
        return
    
    print("\n🎉 Database migration completed successfully!")
    print("\nNext steps:")
    print("1. Run 'python scripts/test_xbrl_setup.py' to test the setup")
    print("2. Update your service files")

if __name__ == "__main__":
    main()