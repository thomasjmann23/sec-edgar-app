"""
Configuration settings for SEC Filing Analyzer
"""
import os
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FILINGS_DIR = DATA_DIR / "filings"
PROCESSED_DIR = DATA_DIR / "processed"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
FILINGS_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

class Settings:
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sec_filings.db")
    
    # AI Models
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # SEC API Settings
    SEC_USER_AGENT: str = os.getenv("SEC_USER_AGENT", "SEC-Filing-Analyzer Thomas Mann thomasjmann23@gmail.com")
    SEC_BASE_URL: str = "https://www.sec.gov/Archives/edgar/data"
    SEC_API_URL: str = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    SEC_REQUEST_DELAY: float = float(os.getenv("SEC_REQUEST_DELAY", "0.1"))  # Be respectful to SEC servers
    
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "localhost")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Filing settings
    MAX_FILING_AGE_DAYS: int = int(os.getenv("MAX_FILING_AGE_DAYS", "90"))  # Only process recent filings
    
    def __init__(self):
        """Initialize settings and validate required values"""
        self.validate_settings()
        self.setup_logging()
    
    def validate_settings(self):
        """Validate required configuration values"""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        if "contact@example.com" in self.SEC_USER_AGENT:
            print("⚠️  WARNING: Please update SEC_USER_AGENT with your actual contact email")
    
    def setup_logging(self):
        """Configure logging for the application"""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sec_analyzer.log'),
                logging.StreamHandler()
            ]
        )

# Global settings instance
settings = Settings()

# Common file paths
COMPANIES_FILE = DATA_DIR / "companies.json"
DATABASE_FILE = Path(settings.DATABASE_URL.replace("sqlite:///", ""))

# SEC specific constants
SEC_FORM_TYPES = {
    "10-K": "10-K",      # Annual report
    "10-Q": "10-Q",      # Quarterly report
    "8-K": "8-K"         # Current report
}

# Standard section mappings for different filing types
SECTION_MAPPINGS = {
    "10-K": {
        "business": ["Item 1", "Business"],
        "risk_factors": ["Item 1A", "Risk Factors"],
        "legal_proceedings": ["Item 3", "Legal Proceedings"],
        "controls": ["Item 9A", "Controls and Procedures"],
        "financials": ["Item 8", "Financial Statements"]
    },
    "10-Q": {
        "financials": ["Part I", "Financial Information"],
        "md_a": ["Item 2", "Management's Discussion"],
        "controls": ["Item 4", "Controls and Procedures"],
        "legal_proceedings": ["Item 1", "Legal Proceedings"]
    }
}

# Standard financial statement types to extract
FINANCIAL_STATEMENTS = [
    "balance_sheet",
    "income_statement", 
    "cash_flow_statement",
    "stockholders_equity"
]

# LLM prompt templates for different analysis types
ANALYSIS_PROMPTS = {
    "risk_summary": """
    Analyze the following risk factors from an SEC filing and provide a concise summary:
    
    Risk Factors Text:
    {risk_text}
    
    Please provide:
    1. Top 3 most significant risks
    2. Any new risks compared to previous filings
    3. Overall risk assessment (Low/Medium/High)
    """,
    
    "financial_summary": """
    Analyze the following financial data and provide insights:
    
    Financial Data:
    {financial_data}
    
    Please provide:
    1. Key financial metrics and trends
    2. Notable changes from previous periods
    3. Overall financial health assessment
    """,
    
    "technology_mentions": """
    Extract and analyze technology-related mentions from this SEC filing text:
    
    Text:
    {text}
    
    Please identify:
    1. AI/ML technology mentions
    2. Other significant technology investments
    3. Technology-related risks or opportunities
    """
}

def get_filing_url(cik: str, form_type: str) -> str:
    """Generate URL for SEC filing search"""
    # Remove leading zeros and format CIK
    cik_formatted = str(int(cik)).zfill(10)
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_formatted}&type={form_type}&dateb=&count=1"

def get_company_facts_url(cik: str) -> str:
    """Generate URL for SEC company facts API"""
    cik_formatted = str(int(cik)).zfill(10)
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_formatted}.json"