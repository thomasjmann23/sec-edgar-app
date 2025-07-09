"""
Simple Inline XBRL Handler - extracts financial data from modern SEC filings
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class InlineXBRLHandler:
    """Simple handler for inline XBRL data in SEC filings"""
    
    def __init__(self, html_content: str):
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
        
    def extract_financial_data(self) -> Dict[str, List[Dict]]:
        """Extract financial data from inline XBRL"""
        
        # Find elements with inline XBRL attributes
        xbrl_elements = self.soup.find_all(attrs={'contextref': True})
        
        financial_data = {
            'facts': [],
            'tables': [],
            'sections': []
        }
        
        # Extract individual facts
        for element in xbrl_elements:
            fact = self._extract_fact(element)
            if fact:
                financial_data['facts'].append(fact)
        
        # Extract tables containing financial data
        tables = self._extract_financial_tables()
        financial_data['tables'] = tables
        
        # Extract major sections
        sections = self._extract_major_sections()
        financial_data['sections'] = sections
        
        return financial_data
    
    def _extract_fact(self, element) -> Optional[Dict]:
        """Extract a single XBRL fact"""
        try:
            # Get the concept name (tag name without namespace)
            concept_name = element.name
            if ':' in concept_name:
                concept_name = concept_name.split(':')[-1]
            
            # Get the value
            value = element.get_text(strip=True)
            
            # Get XBRL attributes
            context_ref = element.get('contextref', '')
            unit_ref = element.get('unitref', '')
            scale = element.get('scale', '')
            decimals = element.get('decimals', '')
            
            # Only return if we have meaningful data
            if value and concept_name:
                return {
                    'concept': concept_name,
                    'value': value,
                    'context_ref': context_ref,
                    'unit_ref': unit_ref,
                    'scale': scale,
                    'decimals': decimals,
                    'is_monetary': 'usd' in unit_ref.lower() if unit_ref else False
                }
        except Exception as e:
            logger.warning(f"Error extracting fact: {e}")
            
        return None
    
    def _extract_financial_tables(self) -> List[Dict]:
        """Extract tables that contain financial data"""
        tables = []
        
        # Find tables with financial keywords
        all_tables = self.soup.find_all('table')
        
        financial_keywords = [
            'balance sheet', 'income statement', 'cash flow', 
            'assets', 'liabilities', 'revenue', 'expenses',
            'consolidated', 'financial position'
        ]
        
        for table in all_tables:
            table_text = table.get_text().lower()
            
            # Check if table contains financial keywords
            if any(keyword in table_text for keyword in financial_keywords):
                
                # Try to identify table type
                table_type = self._classify_table_type(table_text)
                
                # Extract table data
                table_data = self._extract_table_data(table)
                
                if table_data:
                    tables.append({
                        'type': table_type,
                        'data': table_data,
                        'html': str(table)
                    })
        
        return tables
    
    def _classify_table_type(self, table_text: str) -> str:
        """Classify the type of financial table"""
        table_text = table_text.lower()
        
        if any(keyword in table_text for keyword in ['balance sheet', 'financial position']):
            return 'balance_sheet'
        elif any(keyword in table_text for keyword in ['income statement', 'operations', 'earnings']):
            return 'income_statement'
        elif any(keyword in table_text for keyword in ['cash flow']):
            return 'cash_flow_statement'
        elif any(keyword in table_text for keyword in ['stockholders equity', 'shareholders equity']):
            return 'stockholders_equity'
        else:
            return 'other_financial_table'
    
    def _extract_table_data(self, table) -> List[List[str]]:
        """Extract data from a table"""
        rows = []
        
        for row in table.find_all('tr'):
            cells = []
            for cell in row.find_all(['td', 'th']):
                cell_text = cell.get_text(strip=True)
                cells.append(cell_text)
            
            if cells:  # Only add non-empty rows
                rows.append(cells)
        
        return rows
    
    def _extract_major_sections(self) -> List[Dict]:
        """Extract major sections from the filing"""
        sections = []
        
        # Look for common section headers
        section_patterns = [
            (r'item\s+1a\s*[.\-:]?\s*risk\s+factors', 'risk_factors'),
            (r'item\s+1\s*[.\-:]?\s*business', 'business'),
            (r'item\s+7\s*[.\-:]?\s*management', 'md_a'),
            (r'item\s+8\s*[.\-:]?\s*financial\s+statements', 'financial_statements'),
            (r'consolidated\s+balance\s+sheets?', 'balance_sheet'),
            (r'consolidated\s+statements?\s+of\s+operations', 'income_statement'),
            (r'consolidated\s+statements?\s+of\s+cash\s+flows?', 'cash_flow_statement')
        ]
        
        for pattern, section_type in section_patterns:
            content = self._extract_section_content(pattern)
            if content:
                sections.append({
                    'type': section_type,
                    'content': content,
                    'length': len(content)
                })
        
        return sections
    
    def _extract_section_content(self, pattern: str) -> Optional[str]:
        """Extract content for a specific section pattern"""
        # Find headers matching the pattern
        headers = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'])
        
        for header in headers:
            header_text = header.get_text(strip=True).lower()
            
            if re.search(pattern, header_text, re.IGNORECASE):
                # Extract content after this header
                content_parts = []
                current = header
                
                # Get content until next major header
                while current:
                    current = current.find_next_sibling()
                    if not current:
                        break
                    
                    # Stop at next major header
                    if current.name in ['h1', 'h2', 'h3'] and self._is_major_section_header(current):
                        break
                    
                    text = current.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                
                content = '\n'.join(content_parts)
                
                # Only return if we have substantial content
                if len(content) > 200:
                    return content
        
        return None
    
    def _is_major_section_header(self, element) -> bool:
        """Check if element is a major section header"""
        text = element.get_text(strip=True).lower()
        
        major_patterns = [
            r'item\s+\d+[a-z]?',
            r'part\s+[ivx]+',
            r'table\s+of\s+contents'
        ]
        
        return any(re.search(pattern, text) for pattern in major_patterns)
    
    def get_summary(self) -> Dict:
        """Get a summary of extracted data"""
        data = self.extract_financial_data()
        
        return {
            'total_facts': len(data['facts']),
            'total_tables': len(data['tables']),
            'total_sections': len(data['sections']),
            'table_types': [table['type'] for table in data['tables']],
            'section_types': [section['type'] for section in data['sections']],
            'has_balance_sheet': any(t['type'] == 'balance_sheet' for t in data['tables']),
            'has_income_statement': any(t['type'] == 'income_statement' for t in data['tables']),
            'has_cash_flow': any(t['type'] == 'cash_flow_statement' for t in data['tables']),
            'sample_facts': data['facts'][:5]  # First 5 facts as examples
        }

# Simple test function
def test_inline_xbrl_handler():
    """Test with the downloaded Apple filing"""
    from pathlib import Path
    
    # Find the downloaded Apple filing
    filings_dir = Path("data/filings")
    apple_files = list(filings_dir.glob("*0000320193*10-K*.html"))
    
    if not apple_files:
        print("❌ No Apple 10-K file found. Run the filing processor first.")
        return
    
    apple_file = apple_files[0]
    print(f"🍎 Testing with Apple filing: {apple_file.name}")
    
    # Read the file
    with open(apple_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Process with inline XBRL handler
    handler = InlineXBRLHandler(html_content)
    summary = handler.get_summary()
    
    print(f"\n📊 Inline XBRL Extraction Results:")
    print(f"  Total facts: {summary['total_facts']}")
    print(f"  Total tables: {summary['total_tables']}")
    print(f"  Total sections: {summary['total_sections']}")
    print(f"  Table types: {summary['table_types']}")
    print(f"  Section types: {summary['section_types']}")
    print(f"  Has balance sheet: {summary['has_balance_sheet']}")
    print(f"  Has income statement: {summary['has_income_statement']}")
    print(f"  Has cash flow: {summary['has_cash_flow']}")
    
    if summary['sample_facts']:
        print(f"\n🔍 Sample Facts:")
        for fact in summary['sample_facts']:
            print(f"  {fact['concept']}: {fact['value']} ({fact['unit_ref']})")

if __name__ == "__main__":
    test_inline_xbrl_handler()