"""
Chart Standardizer Service for SEC Filing Analyzer
Maps company-specific R# chart numbers to standardized chart types
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChartMapping:
    """Data class for chart type mappings"""
    r_number: str
    original_title: str
    standard_type: str
    confidence: str  # high, medium, low
    keywords_matched: List[str]

class ChartStandardizer:
    """Service to standardize R# chart types across companies"""
    
    def __init__(self):
        # Standard chart type patterns
        self.standard_patterns = {
            'balance_sheet': [
                'balance sheet',
                'consolidated balance sheet',
                'statement of financial position',
                'consolidated statement of financial position',
                'assets and liabilities',
                'assets, liabilities and stockholders',
                'financial position'
            ],
            'income_statement': [
                'income statement',
                'consolidated income statement',
                'statement of operations',
                'consolidated statement of operations',
                'earnings',
                'consolidated earnings',
                'statement of comprehensive income',
                'operations and comprehensive income',
                'profit and loss'
            ],
            'cash_flow_statement': [
                'cash flow',
                'consolidated cash flow',
                'statement of cash flows',
                'consolidated statement of cash flows',
                'cash flows'
            ],
            'stockholders_equity': [
                'stockholders equity',
                'shareholders equity',
                'statement of equity',
                'statement of stockholders equity',
                'consolidated statement of stockholders equity',
                'changes in stockholders equity',
                'stockholders investment'
            ],
            'comprehensive_income': [
                'comprehensive income',
                'consolidated comprehensive income',
                'other comprehensive income',
                'comprehensive loss'
            ],
            'notes_to_financial_statements': [
                'notes to consolidated financial statements',
                'notes to financial statements',
                'financial statement notes',
                'notes'
            ]
        }
        
        # Additional keywords that can help with classification
        self.supporting_keywords = {
            'balance_sheet': ['assets', 'liabilities', 'equity', 'current assets', 'property plant equipment'],
            'income_statement': ['revenue', 'cost of sales', 'gross profit', 'net income', 'operating expenses'],
            'cash_flow_statement': ['operating activities', 'investing activities', 'financing activities', 'net cash'],
            'stockholders_equity': ['common stock', 'retained earnings', 'accumulated other comprehensive', 'stockholders', 'shareholders'],
            'comprehensive_income': ['foreign currency translation', 'unrealized gains', 'pension adjustments']
        }
    
    def standardize_chart_type(self, r_number: str, title: str, content: str = None) -> ChartMapping:
        """
        Standardize a chart type based on R# number, title, and optional content
        
        Args:
            r_number: R# identifier (e.g., "R1", "R2")
            title: Original chart title
            content: Optional chart content for additional context
            
        Returns:
            ChartMapping with standardized type and confidence score
        """
        title_lower = title.lower().strip()
        
        # First pass: Direct title matching
        for standard_type, patterns in self.standard_patterns.items():
            for pattern in patterns:
                if pattern in title_lower:
                    return ChartMapping(
                        r_number=r_number,
                        original_title=title,
                        standard_type=standard_type,
                        confidence='high',
                        keywords_matched=[pattern]
                    )
        
        # Second pass: Content-based matching if content is provided
        if content:
            content_lower = content.lower()
            
            # Check each standard type for matches
            best_match = None
            best_score = 0
            
            for standard_type, patterns in self.standard_patterns.items():
                matched_patterns = []
                
                # Check main patterns in content
                for pattern in patterns:
                    if pattern in content_lower:
                        matched_patterns.append(pattern)
                
                # Check supporting keywords
                supporting_matches = []
                for keyword in self.supporting_keywords.get(standard_type, []):
                    if keyword in content_lower:
                        supporting_matches.append(keyword)
                
                # Calculate score (main patterns worth more than supporting keywords)
                score = len(matched_patterns) * 3 + len(supporting_matches) * 1
                
                if score > best_score:
                    best_score = score
                    confidence = 'high' if len(matched_patterns) > 0 else 'medium'
                    best_match = ChartMapping(
                        r_number=r_number,
                        original_title=title,
                        standard_type=standard_type,
                        confidence=confidence,
                        keywords_matched=matched_patterns + supporting_matches
                    )
            
            if best_match and best_score > 0:
                return best_match
        
        # Third pass: Heuristic matching based on common R# patterns
        heuristic_type = self._apply_heuristic_rules(r_number, title_lower)
        if heuristic_type:
            return ChartMapping(
                r_number=r_number,
                original_title=title,
                standard_type=heuristic_type,
                confidence='low',
                keywords_matched=['heuristic_rule']
            )
        
        # Default: unknown type
        return ChartMapping(
            r_number=r_number,
            original_title=title,
            standard_type='unknown',
            confidence='low',
            keywords_matched=[]
        )
    
    def _apply_heuristic_rules(self, r_number: str, title_lower: str) -> Optional[str]:
        """Apply heuristic rules based on common R# patterns"""
        
        # Common patterns observed in SEC filings
        if any(keyword in title_lower for keyword in ['balance', 'assets', 'liabilities']):
            return 'balance_sheet'
        
        if any(keyword in title_lower for keyword in ['income', 'operations', 'earnings', 'revenue']):
            return 'income_statement'
        
        if any(keyword in title_lower for keyword in ['cash', 'flows']):
            return 'cash_flow_statement'
        
        if any(keyword in title_lower for keyword in ['equity', 'stockholders', 'shareholders']):
            return 'stockholders_equity'
        
        if any(keyword in title_lower for keyword in ['comprehensive']):
            return 'comprehensive_income'
        
        if any(keyword in title_lower for keyword in ['notes', 'footnotes']):
            return 'notes_to_financial_statements'
        
        return None
    
    def batch_standardize(self, chart_data: List[Dict]) -> List[ChartMapping]:
        """
        Standardize multiple charts at once
        
        Args:
            chart_data: List of dicts with 'r_number', 'title', and optional 'content'
            
        Returns:
            List of ChartMapping objects
        """
        results = []
        
        for chart in chart_data:
            r_number = chart.get('r_number', '')
            title = chart.get('title', '')
            content = chart.get('content', '')
            
            mapping = self.standardize_chart_type(r_number, title, content)
            results.append(mapping)
        
        return results
    
    def get_standardized_summary(self, chart_mappings: List[ChartMapping]) -> Dict[str, List[str]]:
        """
        Get a summary of standardized chart types
        
        Args:
            chart_mappings: List of ChartMapping objects
            
        Returns:
            Dictionary with standard types as keys and R# numbers as values
        """
        summary = {}
        
        for mapping in chart_mappings:
            standard_type = mapping.standard_type
            if standard_type not in summary:
                summary[standard_type] = []
            
            summary[standard_type].append({
                'r_number': mapping.r_number,
                'original_title': mapping.original_title,
                'confidence': mapping.confidence
            })
        
        return summary
    
    def validate_filing_completeness(self, chart_mappings: List[ChartMapping]) -> Dict[str, bool]:
        """
        Check if a filing has the expected core financial statements
        
        Args:
            chart_mappings: List of ChartMapping objects
            
        Returns:
            Dictionary showing which core statements are present
        """
        found_types = {mapping.standard_type for mapping in chart_mappings}
        
        core_statements = [
            'balance_sheet',
            'income_statement',
            'cash_flow_statement',
            'stockholders_equity'
        ]
        
        completeness = {}
        for statement in core_statements:
            completeness[statement] = statement in found_types
        
        return completeness

# Convenience functions for easy use
def standardize_single_chart(r_number: str, title: str, content: str = None) -> ChartMapping:
    """Convenience function to standardize a single chart"""
    standardizer = ChartStandardizer()
    return standardizer.standardize_chart_type(r_number, title, content)

def standardize_filing_charts(chart_data: List[Dict]) -> List[ChartMapping]:
    """Convenience function to standardize all charts in a filing"""
    standardizer = ChartStandardizer()
    return standardizer.batch_standardize(chart_data)

# Test function
def test_chart_standardizer():
    """Test the chart standardizer with sample data"""
    standardizer = ChartStandardizer()
    
    # Test cases
    test_cases = [
        {
            'r_number': 'R1',
            'title': 'CONSOLIDATED BALANCE SHEETS',
            'content': 'Assets Current assets: Cash and cash equivalents'
        },
        {
            'r_number': 'R2', 
            'title': 'CONSOLIDATED STATEMENTS OF OPERATIONS',
            'content': 'Net revenues Cost of sales Gross profit'
        },
        {
            'r_number': 'R3',
            'title': 'CONSOLIDATED STATEMENTS OF CASH FLOWS',
            'content': 'Operating activities Investing activities Financing activities'
        },
        {
            'r_number': 'R4',
            'title': 'CONSOLIDATED STATEMENTS OF STOCKHOLDERS\' EQUITY',
            'content': 'Common stock Retained earnings'
        }
    ]
    
    print("🧪 Testing Chart Standardizer")
    print("=" * 50)
    
    for test_case in test_cases:
        result = standardizer.standardize_chart_type(
            test_case['r_number'],
            test_case['title'],
            test_case['content']
        )
        
        print(f"\n📊 {test_case['r_number']}: {test_case['title']}")
        print(f"   → Standard Type: {result.standard_type}")
        print(f"   → Confidence: {result.confidence}")
        print(f"   → Keywords: {result.keywords_matched}")
    
    # Test batch processing
    batch_results = standardizer.batch_standardize(test_cases)
    summary = standardizer.get_standardized_summary(batch_results)
    
    print(f"\n📋 Batch Processing Summary:")
    for standard_type, charts in summary.items():
        print(f"   {standard_type}: {len(charts)} chart(s)")
    
    # Test completeness
    completeness = standardizer.validate_filing_completeness(batch_results)
    print(f"\n✅ Filing Completeness:")
    for statement, present in completeness.items():
        status = "✓" if present else "✗"
        print(f"   {status} {statement}")

if __name__ == "__main__":
    test_chart_standardizer()