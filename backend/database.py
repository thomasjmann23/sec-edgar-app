"""
Database models and setup for SEC Filing Analyzer (Simplified)
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import json
import hashlib
from typing import Dict, List, Optional, Any
import logging

from config import settings

logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Company(Base):
    """Company model for tracking companies we analyze"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    cik = Column(String(10), unique=True, index=True, nullable=False)
    symbol = Column(String(10), index=True)
    industry = Column(String(100))
    sector = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    filings = relationship("Filing", back_populates="company")
    
    def __repr__(self):
        return f"<Company(name='{self.name}', cik='{self.cik}', symbol='{self.symbol}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert company to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "cik": self.cik,
            "symbol": self.symbol,
            "industry": self.industry,
            "sector": self.sector,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Filing(Base):
    """Filing model for storing SEC filing information"""
    __tablename__ = "filings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    form_type = Column(String(10), nullable=False)  # 10-K, 10-Q, 8-K
    filing_date = Column(DateTime, nullable=False)
    period_end_date = Column(DateTime)
    accession_number = Column(String(25), unique=True, index=True)
    document_url = Column(String(500))
    html_file_path = Column(String(500))  # Local path to saved HTML
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    

    
    # Relationships
    company = relationship("Company", back_populates="filings")
    sections = relationship("FilingSection", back_populates="filing")
    charts = relationship("FilingChart", back_populates="filing")
    analyses = relationship("Analysis", back_populates="filing")

    def __repr__(self):
        return f"<Filing(form_type='{self.form_type}', filing_date='{self.filing_date}', company_id={self.company_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filing to dictionary"""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "form_type": self.form_type,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "period_end_date": self.period_end_date.isoformat() if self.period_end_date else None,
            "accession_number": self.accession_number,
            "document_url": self.document_url,
            "processed": self.processed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class FilingSection(Base):
    """Model for storing parsed sections from filings"""
    __tablename__ = "filing_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), nullable=False)
    section_type = Column(String(50), nullable=False)  # risk_factors, md_a, etc.
    section_title = Column(String(200))
    content = Column(Text)
    processed_content = Column(Text)  # Cleaned/processed version
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # New metadata columns for RAG
    chunk_type = Column(String(50))  # text_chunk, chart_complete, table_row
    standard_type = Column(String(50))  # risk_factors, balance_sheet, etc.
    company_context = Column(String(200))  # company name for RAG context
    content_hash = Column(String(64))  # for deduplication
    
    # Relationships
    filing = relationship("Filing", back_populates="sections")
    
    def __repr__(self):
        return f"<FilingSection(section_type='{self.section_type}', filing_id={self.filing_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary"""
        return {
            "id": self.id,
            "filing_id": self.filing_id,
            "section_type": self.section_type,
            "section_title": self.section_title,
            "content": self.content,
            "processed_content": self.processed_content,
            "chunk_type": self.chunk_type,
            "standard_type": self.standard_type,
            "company_context": self.company_context,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def generate_content_hash(self):
        """Generate hash for content deduplication"""
        if self.content:
            return hashlib.sha256(self.content.encode()).hexdigest()[:16]
        return None

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
    
    # Relationships
    filing = relationship("Filing", back_populates="charts")
    
    def __repr__(self):
        return f"<FilingChart(r_number='{self.r_number}', standard_type='{self.standard_type}', filing_id={self.filing_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chart to dictionary"""
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

class Analysis(Base):
    """Model for storing LLM analysis results"""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    filing_id = Column(Integer, ForeignKey("filings.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)  # risk_summary, financial_summary, etc.
    prompt_used = Column(Text)
    raw_response = Column(Text)  # Raw LLM response
    structured_data = Column(Text)  # JSON structured insights
    confidence_score = Column(String(20))  # High, Medium, Low
    model_used = Column(String(50))  # gemini-pro, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    filing = relationship("Filing", back_populates="analyses")
    
    def __repr__(self):
        return f"<Analysis(analysis_type='{self.analysis_type}', filing_id={self.filing_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary"""
        structured_data = None
        if self.structured_data:
            try:
                structured_data = json.loads(self.structured_data)
            except json.JSONDecodeError:
                structured_data = self.structured_data
        
        return {
            "id": self.id,
            "filing_id": self.filing_id,
            "analysis_type": self.analysis_type,
            "raw_response": self.raw_response,
            "structured_data": structured_data,
            "confidence_score": self.confidence_score,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database with tables"""
    logger.info("Initializing database...")
    create_tables()
    logger.info("Database initialized successfully")

class DatabaseManager:
    """Database manager with common operations"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def get_or_create_company(self, name: str, cik: str, symbol: str = None) -> Company:
        """Get existing company or create new one"""
        company = self.db.query(Company).filter(Company.cik == cik).first()
        
        if not company:
            company = Company(name=name, cik=cik, symbol=symbol)
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
            logger.info(f"Created new company: {name} (CIK: {cik})")
        
        return company
    
    def get_company_by_cik(self, cik: str) -> Optional[Company]:
        """Get company by CIK"""
        return self.db.query(Company).filter(Company.cik == cik).first()
    
    def get_all_companies(self) -> List[Company]:
        """Get all companies"""
        return self.db.query(Company).all()
    
    def create_filing(self, company_id: int, form_type: str, filing_date: datetime, 
                     accession_number: str, document_url: str = None) -> Filing:
        """Create new filing record"""
        filing = Filing(
            company_id=company_id,
            form_type=form_type,
            filing_date=filing_date,
            accession_number=accession_number,
            document_url=document_url
        )
        
        self.db.add(filing)
        self.db.commit()
        self.db.refresh(filing)
        
        logger.info(f"Created new filing: {form_type} for company_id {company_id}")
        return filing
    
    def get_filing_by_accession(self, accession_number: str) -> Optional[Filing]:
        """Get filing by accession number"""
        return self.db.query(Filing).filter(Filing.accession_number == accession_number).first()
    
    def get_company_filings(self, company_id: int, form_type: str = None) -> List[Filing]:
        """Get filings for a company"""
        query = self.db.query(Filing).filter(Filing.company_id == company_id)
        
        if form_type:
            query = query.filter(Filing.form_type == form_type)
        
        return query.order_by(Filing.filing_date.desc()).all()
    
    def create_section(self, filing_id: int, section_type: str, content: str, 
                      section_title: str = None, chunk_type: str = "text_chunk",
                      standard_type: str = None, company_context: str = None) -> FilingSection:
        """Create new filing section"""
        section = FilingSection(
            filing_id=filing_id,
            section_type=section_type,
            section_title=section_title,
            content=content,
            chunk_type=chunk_type,
            standard_type=standard_type or section_type,
            company_context=company_context
        )
        
        # Generate content hash for deduplication
        section.content_hash = section.generate_content_hash()
        
        self.db.add(section)
        self.db.commit()
        self.db.refresh(section)
        
        return section
    
    def create_chart(self, filing_id: int, r_number: str, original_title: str,
                    content: str, standard_type: str = None, 
                    confidence_score: str = "medium") -> FilingChart:
        """Create new filing chart"""
        chart = FilingChart(
            filing_id=filing_id,
            r_number=r_number,
            original_title=original_title,
            content=content,
            standard_type=standard_type,
            confidence_score=confidence_score
        )
        
        self.db.add(chart)
        self.db.commit()
        self.db.refresh(chart)
        
        return chart
    
    def create_analysis(self, filing_id: int, analysis_type: str, prompt: str, 
                       response: str, structured_data: Dict = None, 
                       confidence_score: str = None, model_used: str = "gemini-pro") -> Analysis:
        """Create new analysis record"""
        analysis = Analysis(
            filing_id=filing_id,
            analysis_type=analysis_type,
            prompt_used=prompt,
            raw_response=response,
            structured_data=json.dumps(structured_data) if structured_data else None,
            confidence_score=confidence_score,
            model_used=model_used
        )
        
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        
        return analysis
    
    def get_filing_analyses(self, filing_id: int) -> List[Analysis]:
        """Get all analyses for a filing"""
        return self.db.query(Analysis).filter(Analysis.filing_id == filing_id).all()
    
    def get_filing_charts(self, filing_id: int) -> List[FilingChart]:
        """Get all charts for a filing"""
        return self.db.query(FilingChart).filter(FilingChart.filing_id == filing_id).all()
    
    def get_charts_by_standard_type(self, standard_type: str) -> List[FilingChart]:
        """Get charts by standardized type across all filings"""
        return self.db.query(FilingChart).filter(FilingChart.standard_type == standard_type).all()
    
    def search_filings(self, company_name: str = None, form_type: str = None, 
                      limit: int = 50) -> List[Filing]:
        """Search filings with optional filters"""
        query = self.db.query(Filing).join(Company)
        
        if company_name:
            query = query.filter(Company.name.ilike(f"%{company_name}%"))
        
        if form_type:
            query = query.filter(Filing.form_type == form_type)
        
        return query.order_by(Filing.filing_date.desc()).limit(limit).all()

# Initialize database on import
if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!")