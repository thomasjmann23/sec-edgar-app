"""
FastAPI application for SEC Filing Analyzer
"""
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import asyncio

from database import get_db, DatabaseManager, Company, Filing, FilingSection, Analysis
from services.sec_client import SECClient
from services.parser import FilingParser
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SEC Filing Analyzer API",
    description="API for analyzing SEC filings with AI-powered insights",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global clients
sec_client = SECClient()

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SEC Filing Analyzer API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "companies": "/companies",
            "filings": "/filings",
            "analysis": "/analysis",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }

# Company endpoints
@app.get("/companies", response_model=List[Dict[str, Any]])
async def get_companies(db: Session = Depends(get_db)):
    """Get all companies"""
    try:
        companies = db.query(Company).all()
        return [company.to_dict() for company in companies]
    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch companies")

@app.get("/companies/{company_id}", response_model=Dict[str, Any])
async def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get a specific company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company.to_dict()

@app.post("/companies", response_model=Dict[str, Any])
async def create_company(company_data: Dict[str, str], db: Session = Depends(get_db)):
    """Create a new company"""
    try:
        with DatabaseManager() as db_manager:
            company = db_manager.get_or_create_company(
                name=company_data['name'],
                cik=company_data['cik'],
                symbol=company_data.get('symbol')
            )
            return company.to_dict()
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create company")

# Filing endpoints
@app.get("/filings", response_model=List[Dict[str, Any]])
async def get_filings(
    company_id: Optional[int] = Query(None),
    form_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Get filings with optional filtering"""
    try:
        query = db.query(Filing)
        
        if company_id:
            query = query.filter(Filing.company_id == company_id)
        
        if form_type:
            query = query.filter(Filing.form_type == form_type)
        
        filings = query.order_by(Filing.filing_date.desc()).limit(limit).all()
        return [filing.to_dict() for filing in filings]
    except Exception as e:
        logger.error(f"Error fetching filings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch filings")

@app.get("/filings/{filing_id}", response_model=Dict[str, Any])
async def get_filing(filing_id: int, db: Session = Depends(get_db)):
    """Get a specific filing with its sections"""
    filing = db.query(Filing).filter(Filing.id == filing_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    
    # Get sections for this filing
    sections = db.query(FilingSection).filter(FilingSection.filing_id == filing_id).all()
    
    filing_data = filing.to_dict()
    filing_data['sections'] = [
        {
            'id': section.id,
            'section_type': section.section_type,
            'section_title': section.section_title,
            'content_length': len(section.content) if section.content else 0,
            'has_content': bool(section.content)
        }
        for section in sections
    ]
    
    return filing_data

@app.get("/filings/{filing_id}/sections/{section_type}")
async def get_filing_section(
    filing_id: int, 
    section_type: str, 
    db: Session = Depends(get_db)
):
    """Get a specific section of a filing"""
    section = db.query(FilingSection).filter(
        FilingSection.filing_id == filing_id,
        FilingSection.section_type == section_type
    ).first()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return {
        'id': section.id,
        'filing_id': section.filing_id,
        'section_type': section.section_type,
        'section_title': section.section_title,
        'content': section.content,
        'processed_content': section.processed_content,
        'created_at': section.created_at.isoformat()
    }

@app.post("/filings/{filing_id}/parse")
async def parse_filing(filing_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Parse a filing to extract sections"""
    filing = db.query(Filing).filter(Filing.id == filing_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    
    if not filing.html_file_path:
        raise HTTPException(status_code=400, detail="No HTML file available for parsing")
    
    # Add parsing task to background
    background_tasks.add_task(parse_filing_background, filing_id)
    
    return {"message": "Filing parsing started", "filing_id": filing_id}

async def parse_filing_background(filing_id: int):
    """Background task to parse a filing"""
    try:
        with DatabaseManager() as db:
            filing = db.db.query(Filing).filter(Filing.id == filing_id).first()
            if not filing:
                return
            
            # Parse the filing
            parser = FilingParser(file_path=filing.html_file_path)
            sections = parser.extract_all_sections()
            
            # Save sections to database
            for section_type, content in sections.items():
                if content and len(content.strip()) > 50:
                    db.create_section(
                        filing_id=filing.id,
                        section_type=section_type,
                        content=content,
                        section_title=section_type.replace('_', ' ').title()
                    )
            
            # Mark as processed
            filing.processed = True
            db.db.commit()
            
            logger.info(f"Successfully parsed filing {filing_id} with {len(sections)} sections")
            
    except Exception as e:
        logger.error(f"Error parsing filing {filing_id}: {str(e)}")

# Company filing endpoints
@app.get("/companies/{company_id}/filings")
async def get_company_filings(
    company_id: int,
    form_type: Optional[str] = Query(None),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db)
):
    """Get filings for a specific company"""
    # Check if company exists
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get filings
    query = db.query(Filing).filter(Filing.company_id == company_id)
    
    if form_type:
        query = query.filter(Filing.form_type == form_type)
    
    filings = query.order_by(Filing.filing_date.desc()).limit(limit).all()
    
    return {
        'company': company.to_dict(),
        'filings': [filing.to_dict() for filing in filings]
    }

@app.post("/companies/{company_id}/sync")
async def sync_company_filings(
    company_id: int,
    form_type: str = Query("10-K"),
    download_html: bool = Query(False),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Sync latest filings for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Add sync task to background
    background_tasks.add_task(sync_company_filings_background, company_id, form_type, download_html)
    
    return {
        "message": f"Syncing {form_type} filings for {company.name}",
        "company_id": company_id
    }

async def sync_company_filings_background(company_id: int, form_type: str, download_html: bool):
    """Background task to sync company filings"""
    try:
        with DatabaseManager() as db:
            company = db.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return
            
            # Get latest filings from SEC
            filings = sec_client.get_company_filings(company.cik, form_type, count=5)
            
            for filing_info in filings:
                # Check if we already have this filing
                existing = db.get_filing_by_accession(filing_info.accession_number)
                if existing:
                    continue
                
                # Create new filing
                filing = db.create_filing(
                    company_id=company.id,
                    form_type=filing_info.form_type,
                    filing_date=filing_info.filing_date,
                    accession_number=filing_info.accession_number,
                    document_url=filing_info.document_url
                )
                
                # Download HTML if requested
                if download_html:
                    html_path = sec_client.download_filing_html(filing_info)
                    if html_path:
                        filing.html_file_path = html_path
                        db.db.commit()
                        
                        # Parse the filing
                        parser = FilingParser(file_path=html_path)
                        sections = parser.extract_all_sections()
                        
                        # Save sections
                        for section_type, content in sections.items():
                            if content and len(content.strip()) > 50:
                                db.create_section(
                                    filing_id=filing.id,
                                    section_type=section_type,
                                    content=content,
                                    section_title=section_type.replace('_', ' ').title()
                                )
                        
                        filing.processed = True
                        db.db.commit()
            
            logger.info(f"Successfully synced filings for company {company.name}")
            
    except Exception as e:
        logger.error(f"Error syncing filings for company {company_id}: {str(e)}")

# Analysis endpoints (placeholder for LLM integration)
@app.get("/analysis")
async def get_analyses(
    filing_id: Optional[int] = Query(None),
    analysis_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get analysis results"""
    query = db.query(Analysis)
    
    if filing_id:
        query = query.filter(Analysis.filing_id == filing_id)
    
    if analysis_type:
        query = query.filter(Analysis.analysis_type == analysis_type)
    
    analyses = query.order_by(Analysis.created_at.desc()).all()
    return [analysis.to_dict() for analysis in analyses]

@app.post("/analysis/compare")
async def compare_filings(
    filing_ids: List[int],
    comparison_type: str = Query("risk_factors"),
    db: Session = Depends(get_db)
):
    """Compare sections across multiple filings"""
    filings = db.query(Filing).filter(Filing.id.in_(filing_ids)).all()
    
    if len(filings) != len(filing_ids):
        raise HTTPException(status_code=404, detail="One or more filings not found")
    
    # Get sections for comparison
    sections = db.query(FilingSection).filter(
        FilingSection.filing_id.in_(filing_ids),
        FilingSection.section_type == comparison_type
    ).all()
    
    # Group by filing
    comparison_data = {}
    for section in sections:
        filing = next(f for f in filings if f.id == section.filing_id)
        company = db.query(Company).filter(Company.id == filing.company_id).first()
        
        comparison_data[filing.id] = {
            'filing': filing.to_dict(),
            'company': company.to_dict() if company else None,
            'section': {
                'content_length': len(section.content) if section.content else 0,
                'content_preview': section.content[:500] if section.content else None
            }
        }
    
    return {
        'comparison_type': comparison_type,
        'filings_compared': len(comparison_data),
        'data': comparison_data
    }

# Search endpoints
@app.get("/search")
async def search_filings(
    query: str = Query(..., min_length=3),
    form_type: Optional[str] = Query(None),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    """Search filings and companies"""
    # This is a simple search - in production you'd want full-text search
    results = {
        'companies': [],
        'filings': []
    }
    
    # Search companies
    companies = db.query(Company).filter(
        Company.name.ilike(f'%{query}%')
    ).limit(limit).all()
    
    results['companies'] = [company.to_dict() for company in companies]
    
    # Search filings (by company name)
    filing_query = db.query(Filing).join(Company).filter(
        Company.name.ilike(f'%{query}%')
    )
    
    if form_type:
        filing_query = filing_query.filter(Filing.form_type == form_type)
    
    filings = filing_query.order_by(Filing.filing_date.desc()).limit(limit).all()
    results['filings'] = [filing.to_dict() for filing in filings]
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )