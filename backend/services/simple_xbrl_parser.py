"""
Simple XBRL parser for beginners
This is a simplified version that focuses on getting basic financial data
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from datetime import datetime
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleXBRLParser:
    """Simple XBRL parser that extracts basic financial facts"""
    
    def __init__(self, xbrl_file_path: str):
        """
        Initialize with path to XBRL file
        
        Args:
            xbrl_file_path: Path to the XBRL instance document
        """
        self.xbrl_file_path = xbrl_file_path
        self.facts = []
        self.contexts = {}
        self.units = {}
        
        # Try to parse the file
        try:
            self._parse_file()
            logger.info(f"Parsed {len(self.facts)} facts from XBRL file")
        except Exception as e:
            logger.error(f"Failed to parse XBRL file: {e}")
            raise
    
    def _parse_file(self):
        """Parse the XBRL file and extract facts"""
        # Parse the XML file
        tree = ET.parse(self.xbrl_file_path)
        root = tree.getroot()
        
        # First, get all the contexts (time periods)
        self._extract_contexts(root)
        
        # Then get all the units (currencies, etc.)
        self._extract_units(root)
        
        # Finally, extract all the facts
        self._extract_facts(root)
    
    def _extract_contexts(self, root):
        """Extract context information (time periods)"""
        # Find all context elements
        contexts = root.findall('.//{http://www.xbrl.org/2003/instance}context')
        
        for context in contexts:
            context_id = context.get('id')
            
            # Get the period information
            period_info = {}
            period = context.find('.//{http://www.xbrl.org/2003/instance}period')
            
            if period is not None:
                # Check if it's an instant or duration
                instant = period.find('.//{http://www.xbrl.org/2003/instance}instant')
                if instant is not None:
                    period_info = {
                        'type': 'instant',
                        'date': instant.text
                    }
                else:
                    start_date = period.find('.//{http://www.xbrl.org/2003/instance}startDate')
                    end_date = period.find('.//{http://www.xbrl.org/2003/instance}endDate')
                    if start_date is not None and end_date is not None:
                        period_info = {
                            'type': 'duration',
                            'start': start_date.text,
                            'end': end_date.text
                        }
            
            self.contexts[context_id] = period_info
    
    def _extract_units(self, root):
        """Extract unit information (currencies, etc.)"""
        units = root.findall('.//{http://www.xbrl.org/2003/instance}unit')
        
        for unit in units:
            unit_id = unit.get('id')
            
            # Get the measure (usually currency like USD)
            measure = unit.find('.//{http://www.xbrl.org/2003/instance}measure')
            if measure is not None:
                self.units[unit_id] = measure.text
    
    def _extract_facts(self, root):
        """Extract all the financial facts"""
        # Look for all elements that are not structural elements
        skip_elements = ['context', 'unit', 'schemaRef', 'linkbaseRef']
        
        for element in root:
            # Skip namespace declarations and structural elements
            if element.tag.startswith('{http://www.xbrl.org/2003/instance}'):
                continue
            
            # Get the concept name (remove namespace)
            concept_name = element.tag.split('}')[-1]
            
            # Skip structural elements
            if concept_name.lower() in skip_elements:
                continue
            
            # This is a fact - extract its information
            fact = self._extract_fact_info(element, concept_name)
            if fact:
                self.facts.append(fact)
    
    def _extract_fact_info(self, element, concept_name):
        """Extract information from a single fact element"""
        # Get the basic information
        value = element.text
        context_ref = element.get('contextRef')
        unit_ref = element.get('unitRef')
        
        # Get context information
        context_info = self.contexts.get(context_ref, {})
        
        # Get unit information
        unit_info = self.units.get(unit_ref, '')
        
        # Determine if this is a monetary value
        is_monetary = 'USD' in unit_info or 'usd' in unit_info.lower() if unit_info else False
        
        # Create the fact dictionary
        fact = {
            'concept_name': concept_name,
            'value': value,
            'context_ref': context_ref,
            'unit_ref': unit_ref,
            'unit': unit_info,
            'is_monetary': is_monetary,
            'period_type': context_info.get('type', ''),
            'period_start': context_info.get('start', ''),
            'period_end': context_info.get('end', ''),
            'period_date': context_info.get('date', '')
        }
        
        return fact
    
    def get_key_metrics(self):
        """Get key financial metrics from the facts"""
        metrics = {}
        
        # Define key concepts we're looking for
        key_concepts = {
            'revenue': ['Revenues', 'Revenue', 'SalesRevenueNet'],
            'net_income': ['NetIncome', 'NetIncomeLoss'],
            'total_assets': ['Assets'],
            'cash': ['Cash', 'CashAndCashEquivalents'],
            'stockholders_equity': ['StockholdersEquity']
        }
        
        # Find facts that match these concepts
        for metric_name, concept_variations in key_concepts.items():
            for fact in self.facts:
                concept_name = fact['concept_name']
                
                # Check if this fact matches any of our key concepts
                for concept_variation in concept_variations:
                    if concept_variation in concept_name:
                        # Convert value to float if it's monetary
                        try:
                            if fact['is_monetary'] and fact['value']:
                                value = float(fact['value'])
                            else:
                                value = fact['value']
                            
                            metrics[metric_name] = {
                                'value': value,
                                'concept': concept_name,
                                'unit': fact['unit'],
                                'period_type': fact['period_type'],
                                'period_start': fact['period_start'],
                                'period_end': fact['period_end'],
                                'period_date': fact['period_date']
                            }
                            break
                        except (ValueError, TypeError):
                            continue
                
                if metric_name in metrics:
                    break
        
        return metrics
    
    def get_all_facts(self):
        """Get all facts found in the XBRL file"""
        return self.facts
    
    def get_facts_by_concept(self, concept_name):
        """Get all facts for a specific concept"""
        return [fact for fact in self.facts if concept_name in fact['concept_name']]
    
    def get_summary(self):
        """Get a summary of what was found in the XBRL file"""
        key_metrics = self.get_key_metrics()
        
        return {
            'file_path': self.xbrl_file_path,
            'total_facts': len(self.facts),
            'key_metrics_found': len(key_metrics),
            'key_metrics': key_metrics,
            'has_revenue': 'revenue' in key_metrics,
            'has_net_income': 'net_income' in key_metrics,
            'has_assets': 'total_assets' in key_metrics
        }

# Simple function to test the parser
def test_xbrl_parser(file_path):
    """Test the XBRL parser with a file"""
    try:
        parser = SimpleXBRLParser(file_path)
        summary = parser.get_summary()
        
        print(f"📊 XBRL Parsing Results:")
        print(f"  Total facts: {summary['total_facts']}")
        print(f"  Key metrics found: {summary['key_metrics_found']}")
        
        for metric_name, metric_info in summary['key_metrics'].items():
            print(f"  {metric_name}: {metric_info['value']} {metric_info['unit']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to parse XBRL file: {e}")
        return False

if __name__ == "__main__":
    # Test with a sample file (only if one is provided)
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"Testing XBRL parser with file: {test_file}")
        
        if not Path(test_file).exists():
            print(f"❌ File not found: {test_file}")
            sys.exit(1)
        
        test_xbrl_parser(test_file)
    else:
        print("✅ Simple XBRL Parser loaded successfully!")
        print("Usage: python simple_xbrl_parser.py /path/to/xbrl/file.xml")
        print("Or import this module to use the SimpleXBRLParser class.")
