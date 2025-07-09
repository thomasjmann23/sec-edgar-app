"""
SEC API Client for fetching filing data
"""
import requests
import time
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import logging
from dataclasses import dataclass

from config import settings, FILINGS_DIR

logger = logging.getLogger(__name__)

@dataclass
class FilingInfo:
    """Data class for filing information"""
    form_type: str
    filing_date: datetime
    accession_number: str
    document_url: str
    company_name: str
    cik: str
    
    def __post_init__(self):
        """Convert string dates to datetime objects"""
        if isinstance(self.filing_date, str):
            self.filing_date = datetime.strptime(self.filing_date, "%Y-%m-%d")

class SECClient:
    """Client for interacting with SEC EDGAR database"""
    
    def __init__(self):
        self.base_url = "https://www.sec.gov"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.SEC_USER_AGENT,
            'Accept': 'application/json, text/html, */*'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.request_delay = settings.SEC_REQUEST_DELAY
        
    def _rate_limit(self):
        """Implement rate limiting to be respectful to SEC servers"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict = None) -> requests.Response:
        """Make a rate-limited request to SEC"""
        self._rate_limit()
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            raise
    
    def get_company_filings(self, cik: str, form_type: str = "10-K", 
                           count: int = 10) -> List[FilingInfo]:
        """
        Get recent filings for a company
        
        Args:
            cik: Company CIK (Central Index Key)
            form_type: Type of filing (10-K, 10-Q, etc.)
            count: Number of filings to retrieve
            
        Returns:
            List of FilingInfo objects
        """
        # Clean and format CIK
        cik = str(int(cik)).zfill(10)
        
        # Use the company search endpoint
        url = f"{self.base_url}/cgi-bin/browse-edgar"
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': form_type,
            'dateb': '',
            'count': count,
            'output': 'atom'  # Get XML format for easier parsing
        }
        
        logger.info(f"Fetching {form_type} filings for CIK {cik}")
        
        try:
            response = self._make_request(url, params)
            return self._parse_company_filings(response.text, cik)
        except Exception as e:
            logger.error(f"Failed to get filings for CIK {cik}: {str(e)}")
            return []
    
    def _parse_company_filings(self, xml_content: str, cik: str) -> List[FilingInfo]:
        """Parse XML response from SEC company search"""
        from xml.etree import ElementTree as ET
        
        try:
            root = ET.fromstring(xml_content)
            filings = []
            
            # Find all entry elements (each represents a filing)
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            for entry in entries:
                try:
                    # Extract filing information
                    title = entry.find('.//{http://www.w3.org/2005/Atom}title').text
                    
                    # Parse form type from title (e.g., "10-K - Annual report")
                    form_match = re.search(r'(\d+\-[A-Z]+)', title)
                    form_type = form_match.group(1) if form_match else "Unknown"
                    
                    # Get filing date
                    updated = entry.find('.//{http://www.w3.org/2005/Atom}updated').text
                    filing_date = datetime.fromisoformat(updated.replace('Z', '+00:00')).date()
                    
                    # Get document link
                    link = entry.find('.//{http://www.w3.org/2005/Atom}link[@type="text/html"]')
                    if link is not None:
                        document_url = link.get('href')
                        
                        # Extract accession number from URL
                        accession_match = re.search(r'accession[_-]number=([0-9-]+)', document_url)
                        accession_number = accession_match.group(1) if accession_match else None
                        
                        # Get company name from content
                        content = entry.find('.//{http://www.w3.org/2005/Atom}content')
                        company_name = "Unknown"
                        if content is not None and content.text:
                            # Extract company name from content
                            lines = content.text.split('\n')
                            for line in lines:
                                if 'Company Name:' in line:
                                    company_name = line.split('Company Name:')[1].strip()
                                    break
                        
                        filing_info = FilingInfo(
                            form_type=form_type,
                            filing_date=filing_date,
                            accession_number=accession_number,
                            document_url=document_url,
                            company_name=company_name,
                            cik=cik
                        )
                        filings.append(filing_info)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse filing entry: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(filings)} filings")
            return filings
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response: {str(e)}")
            return []
    
    def get_filing_documents(self, filing_info: FilingInfo) -> List[Dict[str, str]]:
        """
        Get all documents for a specific filing
        
        Args:
            filing_info: FilingInfo object
            
        Returns:
            List of document dictionaries with 'type', 'description', and 'url'
        """
        try:
            response = self._make_request(filing_info.document_url)
            return self._parse_filing_documents(response.text, filing_info.document_url)
        except Exception as e:
            logger.error(f"Failed to get documents for filing {filing_info.accession_number}: {str(e)}")
            return []
    
    def _parse_filing_documents(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Parse filing page to extract document links"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        documents = []
        
        # Find the documents table
        table = soup.find('table', {'class': 'tableFile'})
        if not table:
            logger.warning("No documents table found in filing page")
            return documents
        
        # Parse each document row
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all('td')
            if len(cells) >= 4:
                # Extract document info
                doc_link = cells[2].find('a')
                if doc_link:
                    doc_url = urljoin(base_url, doc_link.get('href'))
                    doc_type = cells[3].text.strip()
                    description = cells[1].text.strip()
                    
                    documents.append({
                        'type': doc_type,
                        'description': description,
                        'url': doc_url
                    })
        
        return documents
    
    def download_filing_html(self, filing_info: FilingInfo, save_path: Path = None) -> Optional[str]:
        """
        Download the main HTML document for a filing
        
        Args:
            filing_info: FilingInfo object
            save_path: Optional path to save the file
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Get all documents for this filing
            documents = self.get_filing_documents(filing_info)
            
            # Find the main filing document (usually the first one or one with specific type)
            main_doc = None
            for doc in documents:
                if any(keyword in doc['type'].lower() for keyword in ['10-k', '10-q', '8-k', 'form']):
                    main_doc = doc
                    break
            
            if not main_doc:
                # If no specific form found, use the first document
                main_doc = documents[0] if documents else None
            
            if not main_doc:
                logger.error(f"No suitable document found for filing {filing_info.accession_number}")
                return None
            
            # Download the document
            response = self._make_request(main_doc['url'])
            
            # Determine save path
            if save_path is None:
                filename = f"{filing_info.cik}_{filing_info.form_type}_{filing_info.accession_number}.html"
                save_path = FILINGS_DIR / filename
            
            # Save the file
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Downloaded filing to {save_path}")
            return str(save_path)
            
        except Exception as e:
            logger.error(f"Failed to download filing {filing_info.accession_number}: {str(e)}")
            return None
    
    def get_company_facts(self, cik: str) -> Optional[Dict]:
        """
        Get company facts from SEC API (newer structured data)
        
        Args:
            cik: Company CIK
            
        Returns:
            Company facts dictionary or None if failed
        """
        cik = str(int(cik)).zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        
        try:
            response = self._make_request(url)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get company facts for CIK {cik}: {str(e)}")
            return None
    
    def search_filings(self, query: str, start_date: datetime = None, 
                      end_date: datetime = None) -> List[FilingInfo]:
        """
        Search for filings using text search
        
        Args:
            query: Search query
            start_date: Start date for search
            end_date: End date for search
            
        Returns:
            List of FilingInfo objects
        """
        # This would use the SEC's search API
        # For now, we'll implement a simple company-based search
        logger.info(f"Searching for filings with query: {query}")
        
        # This is a placeholder - in a full implementation, you'd use the SEC search API
        # For now, we'll return empty list
        return []
    
    def get_latest_filing(self, cik: str, form_type: str) -> Optional[FilingInfo]:
        """
        Get the most recent filing of a specific type for a company
        
        Args:
            cik: Company CIK
            form_type: Form type (10-K, 10-Q, etc.)
            
        Returns:
            Most recent FilingInfo or None
        """
        filings = self.get_company_filings(cik, form_type, count=1)
        return filings[0] if filings else None
    
    def is_filing_recent(self, filing_info: FilingInfo, days: int = None) -> bool:
        """
        Check if a filing is recent (within specified days)
        
        Args:
            filing_info: FilingInfo object
            days: Number of days to consider recent (default from settings)
            
        Returns:
            True if filing is recent
        """
        if days is None:
            days = settings.MAX_FILING_AGE_DAYS
        
        cutoff_date = datetime.now().date() - timedelta(days=days)
        return filing_info.filing_date >= cutoff_date

    def download_xbrl_for_filing(self, filing_info: FilingInfo, save_dir: Path = None) -> Optional[str]:
        """
        Simple method to download XBRL file for a filing
        
        Args:
            filing_info: FilingInfo object
            save_dir: Directory to save the file
            
        Returns:
            Path to downloaded XBRL file or None if failed
        """
        if save_dir is None:
            save_dir = FILINGS_DIR
        
        try:
            # Get all documents for this filing
            documents = self.get_filing_documents(filing_info)
            
            # Look for XBRL instance document
            xbrl_doc = None
            for doc in documents:
                # Look for common XBRL file indicators
                if (doc['type'].lower() == 'ex-101.ins' or 
                    'instance' in doc['description'].lower() or
                    doc['url'].endswith('.xml')):
                    xbrl_doc = doc
                    break
            
            if not xbrl_doc:
                logger.warning(f"No XBRL document found for filing {filing_info.accession_number}")
                return None
            
            # Download the XBRL file
            response = self._make_request(xbrl_doc['url'])
            
            # Create filename
            filename = f"{filing_info.cik}_{filing_info.accession_number}_instance.xml"
            file_path = save_dir / filename
            
            # Save the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            logger.info(f"Downloaded XBRL file to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to download XBRL file: {e}")
            return None

    def check_filing_has_xbrl(self, filing_info: FilingInfo) -> bool:
        """
        Check if a filing has XBRL data available
        
        Args:
            filing_info: FilingInfo object
            
        Returns:
            True if XBRL data is available
        """
        try:
            documents = self.get_filing_documents(filing_info)
            
            # Look for XBRL indicators
            for doc in documents:
                if (doc['type'].lower() == 'ex-101.ins' or 
                    'instance' in doc['description'].lower() or
                    'xbrl' in doc['description'].lower()):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check XBRL availability: {e}")
            return False
    



# Utility functions
def format_cik(cik: str) -> str:
    """Format CIK to standard 10-digit format"""
    return str(int(cik)).zfill(10)

def parse_accession_number(accession: str) -> str:
    """Parse and format accession number"""
    # Remove any non-alphanumeric characters and format
    clean_accession = re.sub(r'[^0-9]', '', accession)
    if len(clean_accession) == 18:
        return f"{clean_accession[:10]}-{clean_accession[10:12]}-{clean_accession[12:]}"
    return accession

def extract_cik_from_url(url: str) -> Optional[str]:
    """Extract CIK from SEC URL"""
    cik_match = re.search(r'CIK=(\d+)', url)
    return cik_match.group(1) if cik_match else None

