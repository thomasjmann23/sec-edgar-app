"""
HTML parser for SEC filings
Extracts and standardizes different sections from SEC filing HTML documents
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import logging
import pandas as pd

from config import SECTION_MAPPINGS, FINANCIAL_STATEMENTS

logger = logging.getLogger(__name__)

class FilingParser:
    """Parser for SEC filing HTML documents"""
    
    def __init__(self, html_content: str = None, file_path: str = None):
        """
        Initialize parser with HTML content or file path
        
        Args:
            html_content: Raw HTML content
            file_path: Path to HTML file
        """
        if html_content:
            self.html_content = html_content
        elif file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.html_content = f.read()
        else:
            raise ValueError("Either html_content or file_path must be provided")
        
        self.soup = BeautifulSoup(self.html_content, 'html.parser')
        self.form_type = self._detect_form_type()
        
    def _detect_form_type(self) -> str:
        """Detect the form type from the HTML content"""
        # Look for form type in common locations
        form_patterns = [
            r'FORM\s+(10-K|10-Q|8-K)',
            r'UNITED STATES\s+SECURITIES AND EXCHANGE COMMISSION.*?FORM\s+(10-K|10-Q|8-K)',
            r'(10-K|10-Q|8-K)\s+ANNUAL REPORT|QUARTERLY REPORT|CURRENT REPORT'
        ]
        
        for pattern in form_patterns:
            match = re.search(pattern, self.html_content, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Default fallback
        return "10-K"
    
    def extract_all_sections(self) -> Dict[str, str]:
        """
        Extract all major sections from the filing
        
        Returns:
            Dictionary with section names as keys and content as values
        """
        sections = {}
        
        # Get section mappings for this form type
        section_mappings = SECTION_MAPPINGS.get(self.form_type, SECTION_MAPPINGS["10-K"])
        
        for section_name, section_patterns in section_mappings.items():
            content = self._extract_section_by_patterns(section_patterns)
            if content:
                sections[section_name] = content
        
        # Also try to extract financial statements
        financial_sections = self._extract_financial_statements()
        sections.update(financial_sections)
        
        return sections
    
    def _extract_section_by_patterns(self, patterns: List[str]) -> Optional[str]:
        """Extract section content using multiple search patterns"""
        for pattern in patterns:
            content = self._find_section_by_pattern(pattern)
            if content:
                return content
        return None
    
    def _find_section_by_pattern(self, pattern: str) -> Optional[str]:
        """Find section content using a specific pattern"""
        # Create regex pattern for the section
        regex_pattern = re.compile(r'(?i)' + re.escape(pattern) + r'\.?\s*')
        
        # Find all text that matches the pattern
        matches = []
        for text in self.soup.find_all(text=regex_pattern):
            parent = text.parent
            if parent:
                matches.append(parent)
        
        if not matches:
            return None
        
        # Get the content after the matching header
        for match in matches:
            content = self._extract_content_after_element(match)
            if content and len(content.strip()) > 100:  # Ensure we got substantial content
                return content
        
        return None
    
    def _extract_content_after_element(self, element: Tag) -> str:
        """Extract content that comes after a specific element"""
        content_parts = []
        
        # Get all following elements until we hit another major section
        current = element
        while current:
            current = current.find_next_sibling()
            if not current:
                break
                
            # Stop if we hit another major section header
            if self._is_section_header(current):
                break
            
            # Extract text content
            text = self._get_clean_text(current)
            if text:
                content_parts.append(text)
        
        return '\n'.join(content_parts)
    
    def _is_section_header(self, element: Tag) -> bool:
        """Check if an element is likely a section header"""
        if not element or not element.name:
            return False
        
        # Check for header tags
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return True
        
        # Check for common section header patterns
        text = element.get_text(strip=True)
        if not text:
            return False
        
        # Common section patterns
        section_patterns = [
            r'^(PART|ITEM)\s+[IVX\d]+',
            r'^Table of Contents',
            r'^[A-Z\s]+\s*\.\s*$',  # All caps with ending period
            r'^\d+\.\s+[A-Z]'  # Numbered sections
        ]
        
        for pattern in section_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _get_clean_text(self, element: Tag) -> str:
        """Get clean text from an element"""
        if not element:
            return ""
        
        # Skip script and style elements
        if element.name in ['script', 'style']:
            return ""
        
        # Get text and clean it up
        text = element.get_text(separator=' ', strip=True)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and other noise
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        return text.strip()
    
    def _extract_financial_statements(self) -> Dict[str, str]:
        """Extract financial statement tables"""
        financial_sections = {}
        
        # Look for tables that contain financial data
        tables = self.soup.find_all('table')
        
        for table in tables:
            # Check if this table contains financial data
            statement_type = self._classify_financial_table(table)
            if statement_type:
                table_content = self._extract_table_content(table)
                if table_content:
                    financial_sections[statement_type] = table_content
        
        return financial_sections
    
    def _classify_financial_table(self, table: Tag) -> Optional[str]:
        """Classify what type of financial statement a table represents"""
        # Get table text for analysis
        table_text = table.get_text().lower()
        
        # Classification patterns
        classifications = {
            'balance_sheet': [
                'balance sheet', 'statement of financial position',
                'assets', 'liabilities', 'stockholders equity'
            ],
            'income_statement': [
                'income statement', 'statement of operations',
                'revenues', 'net income', 'earnings per share'
            ],
            'cash_flow_statement': [
                'cash flow', 'statement of cash flows',
                'operating activities', 'investing activities', 'financing activities'
            ],
            'stockholders_equity': [
                'stockholders equity', 'shareholders equity',
                'statement of equity', 'retained earnings'
            ]
        }
        
        for statement_type, keywords in classifications.items():
            if any(keyword in table_text for keyword in keywords):
                return statement_type
        
        return None
    
    def _extract_table_content(self, table: Tag) -> str:
        """Extract content from a table in a structured format"""
        rows = []
        
        # Extract table rows
        for row in table.find_all('tr'):
            cells = []
            for cell in row.find_all(['td', 'th']):
                cell_text = cell.get_text(strip=True)
                cells.append(cell_text)
            
            if cells:  # Only add non-empty rows
                rows.append('\t'.join(cells))
        
        return '\n'.join(rows)
    
    def extract_risk_factors(self) -> Optional[str]:
        """Extract risk factors section specifically"""
        risk_patterns = [
            "Risk Factors",
            "Item 1A",
            "RISK FACTORS",
            "Principal Risks"
        ]
        
        return self._extract_section_by_patterns(risk_patterns)
    
    def extract_business_overview(self) -> Optional[str]:
        """Extract business overview section"""
        business_patterns = [
            "Business",
            "Item 1",
            "BUSINESS",
            "Overview"
        ]
        
        return self._extract_section_by_patterns(business_patterns)
    
    def extract_md_a(self) -> Optional[str]:
        """Extract Management's Discussion and Analysis"""
        mda_patterns = [
            "Management's Discussion and Analysis",
            "Item 7",
            "MD&A",
            "MANAGEMENT'S DISCUSSION"
        ]
        
        return self._extract_section_by_patterns(mda_patterns)
    
    def extract_financial_highlights(self) -> Dict[str, str]:
        """Extract key financial metrics and highlights"""
        highlights = {}
        
        # Look for common financial metrics in the text
        financial_patterns = {
            'revenue': r'revenue[s]?[:\s]+\$?([\d,]+(?:\.\d+)?)',
            'net_income': r'net income[:\s]+\$?([\d,]+(?:\.\d+)?)',
            'total_assets': r'total assets[:\s]+\$?([\d,]+(?:\.\d+)?)',
            'cash': r'cash and cash equivalents[:\s]+\$?([\d,]+(?:\.\d+)?)'
        }
        
        for metric, pattern in financial_patterns.items():
            matches = re.findall(pattern, self.html_content, re.IGNORECASE)
            if matches:
                highlights[metric] = matches[0]
        
        return highlights
    
    def get_filing_summary(self) -> Dict[str, str]:
        """Get a summary of the filing with key information"""
        summary = {
            'form_type': self.form_type,
            'total_length': len(self.html_content),
            'section_count': len(self.extract_all_sections()),
            'has_financial_data': bool(self._extract_financial_statements()),
            'filing_date': self._extract_filing_date(),
            'company_name': self._extract_company_name()
        }
        
        return summary
    
    def _extract_filing_date(self) -> Optional[str]:
        """Extract filing date from the document"""
        date_patterns = [
            r'Date of Report.*?(\d{1,2}/\d{1,2}/\d{4})',
            r'Filing Date.*?(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, self.html_content)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_company_name(self) -> Optional[str]:
        """Extract company name from the document"""
        # Look for company name in common locations
        name_patterns = [
            r'COMPANY\s+NAME[:.]?\s*([A-Z][A-Z\s&,\.]+)',
            r'REGISTRANT[:.]?\s*([A-Z][A-Z\s&,\.]+)',
            r'<title>([^<]+)</title>'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, self.html_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

def parse_filing_file(file_path: str) -> Dict[str, str]:
    """
    Convenience function to parse a filing file
    
    Args:
        file_path: Path to the HTML filing file
        
    Returns:
        Dictionary with extracted sections
    """
    parser = FilingParser(file_path=file_path)
    return parser.extract_all_sections()

def parse_filing_html(html_content: str) -> Dict[str, str]:
    """
    Convenience function to parse HTML content
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Dictionary with extracted sections
    """
    parser = FilingParser(html_content=html_content)
    return parser.extract_all_sections()