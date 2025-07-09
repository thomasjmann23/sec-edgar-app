#!/usr/bin/env python3
"""
Inline XBRL Parser for modern SEC filings
This parser extracts XBRL data embedded in HTML files
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class InlineXBRLParser:
    """Parser for Inline XBRL data embedded in HTML filings"""
    
    def __init__(self, html_file_path: str = None, html_content: str = None):
        """
        Initialize with either file path or HTML content
        
        Args:
            html_file_path: Path to HTML filing
            html_content: Raw HTML content
        """
        if html_file_path:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                self.html_content = f.read()
            self.file_path = html_file_path
        elif html_content:
            self.html_content = html_content
            self.file_path = None
        else:
            raise ValueError("Either html_file_path or html_content must be provided")
        
        self.soup = BeautifulSoup(self.html_content, 'html.parser')
        self.xbrl_facts = []
        self.contexts = {}
        self.units = {}
        
        # Parse the inline XBRL data
        self._parse_inline_xbrl()
    
    def _parse_inline_xbrl(self):
        """Parse inline XBRL data from HTML"""
        try:
            # Look for XBRL namespace declarations
            self._find_xbrl_namespaces()
            
            # Find XBRL contexts
            self._extract_contexts()
            
            # Find XBRL units
            self._extract_units()
            
            # Extract XBRL facts
            self._extract_inline_facts()
            
            logger.info(f"Found {len(self.xbrl_facts)} inline XBRL facts")
            
        except Exception as e:
            logger.error(f"Error parsing inline XBRL: {e}")
    
    def _find_xbrl_namespaces(self):
        """Find XBRL namespace declarations in the HTML"""
        # Look for xmlns declarations in HTML tag or elsewhere
        html_tag = self.soup.find('html')
        if html_tag:
            # Check for XBRL-related namespace declarations
            for attr_name, attr_value in html_tag.attrs.items():
                if attr_name.startswith('xmlns:') and 'xbrl' in attr_value.lower():
                    logger.info(f"Found XBRL namespace: {attr_name}={attr_value}")
    
    def _extract_contexts(self):
        """Extract XBRL contexts from HTML"""
        # Look for context elements (can be in various formats)
        context_elements = self.soup.find_all(attrs={'contextref': True})
        
        # Also look for explicit context definitions
        for element in self.soup.find_all():
            if element.name and 'context' in element.name.lower():
                context_id = element.get('id')
                if context_id:
                    self.contexts[context_id] = {
                        'id': context_id,
                        'element': element
                    }
    
    def _extract_units(self):
        """Extract XBRL units from HTML"""
        # Look for unit elements
        for element in self.soup.find_all():
            if element.name and 'unit' in element.name.lower():
                unit_id = element.get('id')
                if unit_id:
                    self.units[unit_id] = {
                        'id': unit_id,
                        'element': element
                    }
    
    def _extract_inline_facts(self):
        """Extract inline XBRL facts from HTML"""
        # Look for elements with XBRL attributes
        xbrl_attributes = [
            'contextref',
            'unitref',
            'name',
            'format',
            'scale',
            'decimals'
        ]
        
        # Find all elements with XBRL attributes
        for element in self.soup.find_all():
            if not element.name:
                continue
            
            # Check if element has XBRL attributes
            has_xbrl_attrs = any(attr in element.attrs for attr in xbrl_attributes)
            
            # Also check for elements with XBRL-like names
            is_xbrl_element = (
                ':' in element.name or  # Namespaced elements
                any(keyword in element.name.lower() for keyword in ['us-gaap', 'dei', 'ifrs'])
            )
            
            if has_xbrl_attrs or is_xbrl_element:
                fact = self._parse_inline_fact(element)
                if fact:
                    self.xbrl_facts.append(fact)
    
    def _parse_inline_fact(self, element):
        """Parse a single inline XBRL fact"""
        try:
            # Extract basic information
            concept_name = element.name
            value = element.get_text(strip=True)
            
            # Extract XBRL attributes
            context_ref = element.get('contextref')
            unit_ref = element.get('unitref')
            scale = element.get('scale')
            decimals = element.get('decimals')
            format_attr = element.get('format')
            
            # Determine data type
            data_type = self._determine_data_type(value, unit_ref, format_attr)
            
            # Clean up concept name
            if ':' in concept_name:
                concept_name = concept_name.split(':')[-1]
            
            fact = {
                'concept_name': concept_name,
                'value': value,
                'context_ref': context_ref,
                'unit_ref': unit_ref,
                'scale': scale,
                'decimals': decimals,
                'format': format_attr,
                'data_type': data_type,
                'is_monetary': data_type == 'monetary'
            }
            
            return fact
            
        except Exception as e:
            logger.warning(f"Error parsing inline fact: {e}")
            return None
    
    def _determine_data_type(self, value: str, unit_ref: str, format_attr: str) -> str:
        """Determine the data type of a fact"""
        if not value:
            return 'text'
        
        # Check unit reference
        if unit_ref:
            unit_lower = unit_ref.lower()
            if 'usd' in unit_lower or 'dollar' in unit_lower:
                return 'monetary'
            elif 'shares' in unit_lower or 'share' in unit_lower:
                return 'shares'
        
        # Check format attribute
        if format_attr:
            format_lower = format_attr.lower()
            if 'num' in format_lower or 'decimal' in format_lower:
                return 'numeric'
            elif 'date' in format_lower:
                return 'date'
        
        # Try to determine from value
        try:
            # Remove common formatting
            clean_value = re.sub(r'[,$\s]', '', value)
            float(clean_value)
            return 'numeric'
        except ValueError:
            pass
        
        # Check for date patterns
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            return 'date'
        
        return 'text'
    
    def get_key_metrics(self) -> Dict[str, Any]:
        """Extract key financial metrics from inline XBRL facts"""
        metrics = {}
        
        # Key concepts we're looking for
        key_concepts = {
            'revenue': ['Revenues', 'Revenue', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax'],
            'net_income': ['NetIncome', 'NetIncomeLoss', 'ProfitLoss'],
            'total_assets': ['Assets', 'AssetsCurrent', 'AssetsNoncurrent'],
            'cash': ['Cash', 'CashAndCashEquivalents', 'CashAndCashEquivalentsAtCarryingValue'],
            'stockholders_equity': ['StockholdersEquity', 'ShareholdersEquity'],
            'total_liabilities': ['Liabilities', 'LiabilitiesAndStockholdersEquity']
        }
        
        # Find matching facts
        for metric_name, concept_variations in key_concepts.items():
            for fact in self.xbrl_facts:
                concept_name = fact['concept_name']
                
                # Check if this fact matches any of our key concepts
                for concept_variation in concept_variations:
                    if concept_variation.lower() in concept_name.lower():
                        # Convert value if it's monetary
                        value = fact['value']
                        if fact['is_monetary'] and value:
                            try:
                                # Remove formatting and convert to float
                                clean_value = re.sub(r'[,$\s]', '', value)
                                numeric_value = float(clean_value)
                                
                                # Apply scale if present
                                if fact['scale']:
                                    scale_factor = int(fact['scale'])
                                    numeric_value = numeric_value * (10 ** scale_factor)
                                
                                value = numeric_value
                            except (ValueError, TypeError):
                                pass
                        
                        metrics[metric_name] = {
                            'value': value,
                            'concept': concept_name,
                            'unit': fact['unit_ref'],
                            'context': fact['context_ref'],
                            'scale': fact['scale'],
                            'decimals': fact['decimals']
                        }
                        break
                
                if metric_name in metrics:
                    break
        
        return metrics
    
    def get_all_facts(self) -> List[Dict[str, Any]]:
        """Get all inline XBRL facts found"""
        return self.xbrl_facts
    
    def get_facts_by_concept(self, concept_name: str) -> List[Dict[str, Any]]:
        """Get facts for a specific concept"""
        return [fact for fact in self.xbrl_facts if concept_name.lower() in fact['concept_name'].lower()]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the inline XBRL data found"""
        key_metrics = self.get_key_metrics()
        
        return {
            'file_path': self.file_path,
            'total_facts': len(self.xbrl_facts),
            'key_metrics_found': len(key_metrics),
            'key_metrics': key_metrics,
            'has_revenue': 'revenue' in key_metrics,
            'has_net_income': 'net_income' in key_metrics,
            'has_assets': 'total_assets' in key_metrics,
            'data_types': list(set(fact['data_type'] for fact in self.xbrl_facts))
        }
    
    def has_xbrl_data(self) -> bool:
        """Check if the HTML file contains XBRL data"""
        return len(self.xbrl_facts) > 0

# Test function
def test_inline_xbrl_with_html(html_file_path: str):
    """Test the inline XBRL parser with an HTML file"""
    try:
        parser = InlineXBRLParser(html_file_path=html_file_path)
        summary = parser.get_summary()
        
        print(f"📊 Inline XBRL Parsing Results:")
        print(f"  Total facts: {summary['total_facts']}")
        print(f"  Key metrics found: {summary['key_metrics_found']}")
        print(f"  Data types found: {summary['data_types']}")
        
        for metric_name, metric_info in summary['key_metrics'].items():
            value = metric_info['value']
            unit = metric_info['unit'] or ''
            if isinstance(value, (int, float)):
                print(f"  {metric_name.replace('_', ' ').title()}: {value:,} {unit}")
            else:
                print(f"  {metric_name.replace('_', ' ').title()}: {value} {unit}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to parse inline XBRL: {e}")
        return False

if __name__ == "__main__":
    # Test with a sample file
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"Testing inline XBRL parser with file: {test_file}")
        test_inline_xbrl_with_html(test_file)
    else:
        print("✅ Inline XBRL Parser loaded successfully!")
        print("Usage: python inline_xbrl_parser.py /path/to/filing.html")