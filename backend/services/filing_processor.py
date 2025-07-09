"""
Simple Filing Processor - downloads, parses, and stores filing sections and charts
"""

import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin
import logging

from config import FILINGS_DIR, settings
from database import DatabaseManager, FilingSection
from services.sec_client import SECClient
from services.parser import FilingParser

logger = logging.getLogger(__name__)

class FilingProcessor:
    """Simple processor for SEC filings - extracts sections and R# charts"""
    
    def __init__(self):
        self.sec_client = SECClient()
        
        # Simple chart type mapping based on common titles
        self.chart_keywords = {
            'balance_sheet': ['balance sheet', 'financial position'],
            'income_statement': ['income', 'operations', 'earnings'],
            'cash_flow_statement': ['cash flow'],
            'stockholders_equity': ['stockholders equity', 'shareholders equity']
        }
    
    def process_filing(self, company_cik: str, form_type: str = "10-K") -> bool:
        """
        Process the latest filing for a company
        
        Args:
            company_cik: Company CIK
            form_type: Form type (10-K, 10-Q)
            
        Returns:
            True if successful
        """
        try:
            # Get latest filing
            filings = self.sec_client.get_company_filings(company_cik, form_type, count=1)
            if not filings:
                logger.error(f"No {form_type} filings found for CIK {company_cik}")
                return False
            
            filing_info = filings[0]
            logger.info(f"Processing {filing_info.form_type} for {filing_info.company_name}")
            
            # Download and parse filing
            sections = self._download_and_parse_filing(filing_info)
            charts = self._download_and_parse_charts(filing_info)
            
            # Store in database
            self._store_filing_data(filing_info, sections, charts)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing filing: {e}")
            return False
    
    def _download_and_parse_filing(self, filing_info) -> Dict[str, str]:
        """Download HTML filing and extract sections"""
        try:
            # Get all documents for this filing
            documents = self.sec_client.get_filing_documents(filing_info)
            
            # Find the main 10-K document (not the index page)
            main_doc = None
            for doc in documents:
                doc_desc = doc.get('description', '').lower()
                doc_type = doc.get('type', '').lower()
                
                # Look for the main filing document
                if ('10-k' in doc_desc or '10-q' in doc_desc or 
                    'form 10-k' in doc_desc or 'form 10-q' in doc_desc or
                    doc_type == '10-k' or doc_type == '10-q'):
                    main_doc = doc
                    break
            
            if not main_doc:
                # Fallback: get the first document that's not an index
                for doc in documents:
                    if 'index' not in doc.get('description', '').lower():
                        main_doc = doc
                        break
            
            if not main_doc:
                logger.error("No main filing document found")
                return {}
            
            # Download the main document
            response = self.sec_client._make_request(main_doc['url'])
            
            # Save to file
            filename = f"{filing_info.cik}_{filing_info.form_type}_{filing_info.accession_number}.html"
            file_path = FILINGS_DIR / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Downloaded main filing ({len(response.text)} chars) to {file_path}")
            
            # Parse sections using inline XBRL handler
            from services.inline_xbrl_handler import InlineXBRLHandler
            handler = InlineXBRLHandler(response.text)
            
            # Extract data
            xbrl_data = handler.extract_financial_data()
            
            # Convert to sections format
            sections = {}
            
            # Add extracted sections
            for section in xbrl_data['sections']:
                sections[section['type']] = section['content']
            
            # Add financial tables as sections
            for table in xbrl_data['tables']:
                section_name = f"{table['type']}_table"
                sections[section_name] = table['html']
            
            logger.info(f"Extracted {len(sections)} sections using inline XBRL handler")
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing filing HTML: {e}")
            return {}
    
    def _download_and_parse_charts(self, filing_info) -> List[Dict]:
        """Download and parse R# chart files"""
        try:
            # Get all documents for this filing
            documents = self.sec_client.get_filing_documents(filing_info)
            
            # Find FilingSummary.xml
            filing_summary_url = None
            for doc in documents:
                if 'FilingSummary.xml' in doc.get('url', ''):
                    filing_summary_url = doc['url']
                    break
            
            if not filing_summary_url:
                logger.warning("No FilingSummary.xml found")
                return []
            
            # Download and parse FilingSummary.xml
            response = self.sec_client._make_request(filing_summary_url)
            root = ET.fromstring(response.text)
            
            # Extract R# file mappings
            charts = []
            for report in root.findall('.//Report'):
                r_number = report.get('id', '')
                title = report.get('longName', '')
                html_file = report.get('htmlFileName', '')
                
                if r_number and html_file:
                    # Download the R# file
                    base_url = filing_summary_url.rsplit('/', 1)[0] + '/'
                    chart_url = urljoin(base_url, html_file)
                    
                    try:
                        chart_response = self.sec_client._make_request(chart_url)
                        charts.append({
                            'r_number': r_number,
                            'title': title,
                            'content': chart_response.text,
                            'url': chart_url
                        })
                    except Exception as e:
                        logger.warning(f"Failed to download {r_number}: {e}")
            
            logger.info(f"Downloaded {len(charts)} R# charts")
            return charts
            
        except Exception as e:
            logger.error(f"Error parsing charts: {e}")
            return []
    
    def _classify_chart_type(self, title: str) -> str:
        """Simple chart type classification"""
        title_lower = title.lower()
        
        for chart_type, keywords in self.chart_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return chart_type
        
        return 'other'
    
    def _store_filing_data(self, filing_info, sections: Dict[str, str], charts: List[Dict]):
        """Store filing data in database"""
        try:
            with DatabaseManager() as db:
                # Get or create company
                company = db.get_or_create_company(
                    name=filing_info.company_name,
                    cik=filing_info.cik,
                    symbol=""  # We don't have symbol in filing_info
                )
                
                # Create filing record
                filing = db.create_filing(
                    company_id=company.id,
                    form_type=filing_info.form_type,
                    filing_date=filing_info.filing_date,
                    accession_number=filing_info.accession_number,
                    document_url=filing_info.document_url
                )
                
                # Store sections
                for section_type, content in sections.items():
                    if content and len(content.strip()) > 100:
                        db.create_section(
                            filing_id=filing.id,
                            section_type=section_type,
                            content=content,
                            chunk_type="text_chunk",
                            standard_type=section_type,
                            company_context=f"{company.name} {filing.form_type}"
                        )
                
                # Store charts
                for chart in charts:
                    standard_type = self._classify_chart_type(chart['title'])
                    db.create_chart(
                        filing_id=filing.id,
                        r_number=chart['r_number'],
                        original_title=chart['title'],
                        content=chart['content'],
                        standard_type=standard_type
                    )
                
                # Mark as processed
                filing.processed = True
                db.db.commit()
                
                logger.info(f"Stored filing with {len(sections)} sections and {len(charts)} charts")
                
        except Exception as e:
            logger.error(f"Error storing filing data: {e}")

# Simple test function
def test_filing_processor():
    """Test the filing processor with Apple"""
    processor = FilingProcessor()
    
    print("🚀 Testing Filing Processor with Apple 10-K")
    print("=" * 50)
    
    # Process Apple's latest 10-K
    success = processor.process_filing("0000320193", "10-K")
    
    if success:
        print("✅ Filing processed successfully!")
        
        # Show what was stored
        with DatabaseManager() as db:
            companies = db.get_all_companies()
            for company in companies:
                if company.cik == "0000320193":
                    filings = db.get_company_filings(company.id)
                    if filings:
                        filing = filings[0]
                        sections = db.db.query(FilingSection).filter(FilingSection.filing_id == filing.id).all()
                        charts = db.get_filing_charts(filing.id)
                        
                        print(f"\n📊 Results for {company.name}:")
                        print(f"  Sections: {len(sections)}")
                        print(f"  Charts: {len(charts)}")
                        
                        for chart in charts:
                            print(f"    {chart.r_number}: {chart.standard_type}")
    else:
        print("❌ Filing processing failed")

if __name__ == "__main__":
    test_filing_processor()