#!/usr/bin/env python3
"""
Simple database migration script to clean up XBRL tables and add FilingChart table
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL, echo=False)
Base = declarative_base()

# Define the new FilingChart table
class FilingChart(Base):
    """Model for storing standardized chart elements from filings"""
    __tablename__ = "filing_charts"
    
    id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), nullable=False)
    
    # Chart identification
    r_number = Column(String(10), nullable=False)  # R1, R2, R3, etc.
    original_title = Column(String(500))  # Original title from filing
    
    # Standardized chart type
    standard_type = Column(String(50), index=True)  # balance_sheet, income_statement, etc.
    confidence_score = Column(String(20))  # high, medium, low
    
    # Content
    content = Column(Text)  # Raw HTML/text content
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "filing_id": self.filing_id,
            "r_number": self.r_number,
            "original_title": self.original_title,
            "standard_type": self.standard_type,
            "confidence_score": self.confidence_score,
            "content_length": len(self.content) if self.content else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

def add_metadata_to_filing_sections():
    """Add metadata columns to existing filing_sections table"""
    print("🔧 Adding metadata columns to filing_sections table...")
    
    try:
        with engine.connect() as conn:
            # Add new columns one by one (safe if they already exist)
            columns_to_add = [
                ("chunk_type", "VARCHAR(50)"),  # text_chunk, chart_complete, table_row
                ("standard_type", "VARCHAR(50)"),  # risk_factors, balance_sheet, etc.
                ("company_context", "VARCHAR(200)"),  # company name for RAG context
                ("content_hash", "VARCHAR(64)"),  # for deduplication
            ]
            
            for column_name, column_type in columns_to_add:
                try:
                    conn.execute(text(f"ALTER TABLE filing_sections ADD COLUMN {column_name} {column_type}"))
                    print(f"✅ Added {column_name} column")
                except Exception:
                    print(f"⚠️  {column_name} column already exists or failed to add")
            
            conn.commit()
        
        print("✅ Updated filing_sections table successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error updating filing_sections table: {e}")
        return False

def create_filing_charts_table():
    """Create the new filing_charts table"""
    print("🏗️  Creating filing_charts table...")
    
    try:
        # Create the table with raw SQL to avoid foreign key issues
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS filing_charts (
                    id INTEGER PRIMARY KEY,
                    filing_id INTEGER NOT NULL,
                    r_number VARCHAR(10) NOT NULL,
                    original_title VARCHAR(500),
                    standard_type VARCHAR(50),
                    confidence_score VARCHAR(20),
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (filing_id) REFERENCES filings (id)
                )
            """))
            
            # Create index on standard_type for faster queries
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_filing_charts_standard_type ON filing_charts(standard_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_filing_charts_filing_id ON filing_charts(filing_id)"))
            
            conn.commit()
        
        print("✅ Created filing_charts table successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating filing_charts table: {e}")
        return False

def drop_xbrl_tables():
    """Drop the complex XBRL tables we don't need"""
    print("🗑️  Dropping unused XBRL tables...")
    
    xbrl_tables = [
        "xbrl_facts",
        "xbrl_concepts", 
        "financial_statements"
    ]
    
    dropped_count = 0
    
    try:
        with engine.connect() as conn:
            for table_name in xbrl_tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    print(f"✅ Dropped {table_name} table")
                    dropped_count += 1
                except Exception as e:
                    print(f"⚠️  Could not drop {table_name}: {e}")
            
            conn.commit()
        
        print(f"✅ Dropped {dropped_count} XBRL tables")
        return True
        
    except Exception as e:
        print(f"❌ Error dropping XBRL tables: {e}")
        return False

def test_new_schema():
    """Test the new database schema"""
    print("🧪 Testing new database schema...")
    
    try:
        # Test that we can access all tables
        with engine.connect() as conn:
            # Check that core tables exist
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ["companies", "filings", "filing_sections", "filing_charts", "analyses"]
            
            for table in expected_tables:
                if table in tables:
                    print(f"✅ {table} table exists")
                else:
                    print(f"⚠️  {table} table missing")
            
            # Check filing_sections columns
            result = conn.execute(text("PRAGMA table_info(filing_sections)"))
            columns = [row[1] for row in result.fetchall()]
            
            expected_columns = ["chunk_type", "standard_type", "company_context", "content_hash"]
            for col in expected_columns:
                if col in columns:
                    print(f"✅ filing_sections.{col} column exists")
                else:
                    print(f"⚠️  filing_sections.{col} column missing")
            
            # Test inserting a record to filing_charts (if filings table exists)
            if "filing_charts" in tables:
                try:
                    conn.execute(text("INSERT INTO filing_charts (filing_id, r_number, original_title, standard_type) VALUES (999, 'R1', 'Test Chart', 'test_type')"))
                    conn.execute(text("DELETE FROM filing_charts WHERE filing_id = 999"))
                    conn.commit()
                    print("✅ filing_charts table is functional")
                except Exception as e:
                    print(f"⚠️  filing_charts table issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting Database Schema Cleanup")
    print("=" * 50)
    
    # Step 1: Add metadata columns to filing_sections
    if not add_metadata_to_filing_sections():
        print("❌ Failed to add metadata columns")
        return
    
    # Step 2: Create new filing_charts table
    if not create_filing_charts_table():
        print("❌ Failed to create filing_charts table")
        return
    
    # Step 3: Drop unused XBRL tables
    if not drop_xbrl_tables():
        print("❌ Failed to drop XBRL tables")
        return
    
    # Step 4: Test the new schema
    if not test_new_schema():
        print("❌ Schema test failed")
        return
    
    print("\n🎉 Database schema cleanup completed successfully!")
    print("\nUpdated schema:")
    print("✓ companies - unchanged")
    print("✓ filings - unchanged") 
    print("✓ filing_sections - added metadata columns")
    print("✓ filing_charts - new table for R# chart elements")
    print("✓ analyses - unchanged")
    print("✗ Removed: xbrl_facts, xbrl_concepts, financial_statements")

if __name__ == "__main__":
    main()