# SEC Filing Analysis Application - Simplified Structure (2-3 Day Build)

## Streamlined Repository Structure

```
sec-filing-analyzer/
├── README.md
├── .gitignore
├── .env.example
├── .env
├── requirements.txt
├── package.json
│
├── backend/
│   ├── config.py
│   ├── models.py
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLite for simplicity
│   │
│   ├── services/
│   │   ├── sec_client.py    # Get filings from SEC
│   │   ├── parser.py        # Parse HTML to extract data
│   │   ├── analyzer.py      # LLM analysis with Gemini
│   │   └── storage.py       # Save/retrieve data
│   │
│   └── utils/
│       ├── helpers.py
│       └── constants.py
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx      # Main dashboard
│   │   │   ├── CompanyList.jsx    # List of companies
│   │   │   ├── FilingViewer.jsx   # View single filing
│   │   │   ├── Comparison.jsx     # Compare filings
│   │   │   └── LoadingSpinner.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js        # API calls to backend
│   │   │
│   │   ├── App.jsx
│   │   ├── index.js
│   │   └── App.css
│   │
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── companies.json       # List of companies to track
│   ├── filings/            # Raw HTML files
│   └── processed/          # Parsed data
│
├── scripts/
│   ├── setup_db.py         # Initialize database
│   ├── seed_companies.py   # Add sample companies
│   └── run_analysis.py     # One-time analysis script
│
└── tests/
    ├── test_parser.py
    ├── test_analyzer.py
    └── sample_10k.html
```

## Simplified Tech Stack

**Backend (Python):**
- FastAPI - Simple, fast API
- SQLite - No database setup needed
- Requests - For SEC API calls
- BeautifulSoup - HTML parsing
- Google Gemini - LLM analysis
- Pandas - Data manipulation

**Frontend (React):**
- React 18 - Core UI framework
- Vite - Fast dev server
- Axios - API calls
- Simple CSS - No complex styling frameworks

## Key Configuration Files

### `.env.example`
```env
# AI Model
GEMINI_API_KEY=your_gemini_key_here

# SEC API
SEC_USER_AGENT=YourApp contact@youremail.com

# Database
DATABASE_URL=sqlite:///./sec_filings.db

# API
API_HOST=localhost
API_PORT=8000
```

### `backend/config.py`
```python
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FILINGS_DIR = DATA_DIR / "filings"
PROCESSED_DIR = DATA_DIR / "processed"

# API Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "SEC-Filing-Analyzer")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sec_filings.db")

# Create directories if they don't exist
FILINGS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
```

### `data/companies.json` (Starter list)
```json
[
  {
    "name": "Apple Inc.",
    "cik": "0000320193",
    "symbol": "AAPL"
  },
  {
    "name": "Microsoft Corporation", 
    "cik": "0000789019",
    "symbol": "MSFT"
  },
  {
    "name": "Amazon.com Inc.",
    "cik": "0000018542", 
    "symbol": "AMZN"
  }
]
```

## Core Functionality Focus

### Phase 1 (Day 1): Basic Data Pipeline
- SEC API client to fetch latest 10-K filings
- HTML parser to extract key sections
- SQLite database to store parsed data
- Basic FastAPI endpoints

### Phase 2 (Day 2): LLM Analysis
- Gemini integration for insight generation
- Analysis of risk factors and financial data
- Basic comparison between companies
- API endpoints for analysis results

### Phase 3 (Day 3): React Frontend
- Dashboard showing all companies
- Filing viewer with sections
- Simple comparison interface
- Basic export functionality

## Development Workflow

1. **Start with Backend Core**:
   ```bash
   pip install -r requirements.txt
   python scripts/setup_db.py
   python scripts/seed_companies.py
   uvicorn backend.main:app --reload
   ```

2. **Test Data Pipeline**:
   ```bash
   python scripts/run_analysis.py
   ```

3. **Build Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Simplified Features

**What we're building:**
- ✅ Fetch latest filings for 3-5 companies
- ✅ Parse key sections (financials, risks, MD&A)
- ✅ Basic LLM analysis and insights
- ✅ Simple React dashboard
- ✅ Company comparison view
- ✅ Basic export to JSON/CSV

**What we're skipping for now:**
- ❌ Vector databases (just use SQLite full-text search)
- ❌ Complex scheduling (manual triggers)
- ❌ User authentication
- ❌ Advanced styling
- ❌ Complex deployment

## Why This Works for Learning

1. **Manageable Scope**: Core functionality in 2-3 days
2. **Modern Stack**: FastAPI + React for real-world experience
3. **LLM Integration**: Practical AI implementation
4. **Expandable**: Easy to add features later
5. **Job-Relevant**: Similar to enterprise data analysis tools

This structure gives you hands-on experience with the full stack while keeping complexity manageable. You'll learn React, API design, data parsing, and LLM integration - all valuable skills for your future projects.

Ready to start with the core backend scripts?