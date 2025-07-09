# SEC Filing Analyzer

A web application for analyzing SEC filings with AI-powered insights. Built with FastAPI, React, and Google Gemini.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for React frontend)
- Google Gemini API key

### 1. Setup Backend

```bash
# Clone or create project directory
mkdir sec-filing-analyzer
cd sec-filing-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys (especially GEMINI_API_KEY)
```

### 2. Initialize Database

```bash
# Create database and sample companies
python scripts/setup_db.py

# Seed with sample companies and fetch filings
python scripts/seed_companies.py --all
```

### 3. Start API Server

```bash
# Start FastAPI server
uvicorn backend.main:app --reload

# API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 4. Test the System

```bash
# Run system tests
python scripts/test_system.py
```

## 🏗️ Project Structure

```
sec-filing-analyzer/
├── backend/
│   ├── config.py              # Configuration management
│   ├── database.py            # Database models and operations
│   ├── main.py                # FastAPI application
│   └── services/
│       ├── sec_client.py      # SEC API client
│       └── parser.py          # HTML filing parser
├── scripts/
│   ├── setup_db.py           # Database initialization
│   ├── seed_companies.py     # Data seeding
│   └── test_system.py        # System testing
├── data/
│   ├── companies.json        # Company definitions
│   ├── filings/             # Downloaded HTML files
│   └── processed/           # Processed data
└── frontend/                 # React app (next step)
```

## 📊 Features

### Core Functionality
- **SEC Filing Retrieval**: Fetch latest 10-K, 10-Q filings from SEC EDGAR
- **HTML Parsing**: Extract structured sections from filing documents
- **Database Storage**: Store companies, filings, and parsed sections
- **REST API**: Full API for accessing and managing data
- **Background Processing**: Parse and analyze filings asynchronously

### API Endpoints
- `GET /companies` - List all companies
- `GET /companies/{id}/filings` - Get filings for a company
- `GET /filings/{id}` - Get specific filing with sections
- `POST /companies/{id}/sync` - Sync latest filings
- `GET /analysis` - Get analysis results (with AI integration)

### Data Pipeline
1. **Fetch** → SEC API retrieval of filing metadata
2. **Download** → HTML document download
3. **Parse** → Section extraction and standardization
4. **Store** → Database storage with relationships
5. **Analyze** → AI-powered insights (next step)

## 🔧 Configuration

### Environment Variables (.env)
```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here
SEC_USER_AGENT=YourApp your-email@example.com

# Optional
DATABASE_URL=sqlite:///./sec_filings.db
API_HOST=localhost
API_PORT=8000
DEBUG=true
LOG_LEVEL=INFO
```

### Sample Companies
The system includes sample companies (Apple, Microsoft, Amazon, Google, Tesla). You can modify `data/companies.json` to add more companies.

## 🧪 Testing

```bash
# Run all tests
python scripts/test_system.py

# Test specific components
python -m pytest tests/  # (if you add pytest tests)

# Manual API testing
curl http://localhost:8000/health
curl http://localhost:8000/companies
```

## 🔍 Usage Examples

### Add a New Company
```bash
# Add via API
curl -X POST http://localhost:8000/companies \
  -H "Content-Type: application/json" \
  -d '{"name": "Netflix Inc.", "cik": "0001065280", "symbol": "NFLX"}'
```

### Sync Latest Filings
```bash
# Sync filings for a company
curl -X POST http://localhost:8000/companies/1/sync?form_type=10-K&download_html=true
```

### Search Filings
```bash
# Search for filings
curl "http://localhost:8000/search?query=Apple&form_type=10-K"
```

## 🔄 Next Steps

1. **Add AI Analysis** - Integrate Gemini for insight generation
2. **Build React Frontend** - Create user interface
3. **Add More Filing Types** - Support 10-Q, 8-K forms
4. **Implement Comparison** - Compare filings across companies
5. **Add Export Features** - CSV, PDF export functionality

## 🛠️ Development

### Adding New Companies
Edit `data/companies.json` and run:
```bash
python scripts/seed_companies.py --companies
```

### Adding New Parsing Rules
Modify `backend/services/parser.py` to add new section extraction patterns.

### Custom Analysis
Extend `backend/services/analyzer.py` (next step) to add custom analysis functions.

## 📚 API Documentation

Full API documentation is available at `/docs` when running the server:
- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

## 🐛 Troubleshooting

### Common Issues
1. **SEC Rate Limiting**: Add delays between requests (already implemented)
2. **Database Errors**: Run `python scripts/setup_db.py` again
3. **Parsing Failures**: Check HTML file format and parsing rules
4. **API Errors**: Check logs in console and `sec_analyzer.log`

### Debug Mode
Set `DEBUG=true` in `.env` for detailed logging.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is for educational purposes. Please respect SEC usage guidelines and rate limits.

---

**Ready to analyze some SEC filings?** 🚀

Start with: `python scripts/test_system.py`