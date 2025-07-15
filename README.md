# Swipe - AI-Powered Resume Screening Application

## Overview
Swipe is a modern, AI-powered resume screening and review application that makes hiring faster and more efficient. With an intuitive swipe interface (like Tinder, but for resumes), recruiters and hiring managers can quickly review candidates with AI-generated insights and make informed decisions.

**Perfect for:**
- Startups looking to streamline their hiring process
- HR departments handling high-volume recruitment
- Recruiting agencies needing efficient candidate screening
- Companies wanting to integrate AI into their hiring workflow

## Key Features

### 🎯 **Smart Resume Analysis**
- AI-powered resume parsing and analysis
- Generates candidate summaries, skill assessments, and fit scores
- Extracts key achievements and experience levels
- Provides reasoning for candidate fit

### 📱 **Intuitive Swipe Interface** 
- Swipe left to pass, right to save candidates
- Keyboard shortcuts for desktop users
- Modern, responsive web interface
- Real-time statistics and progress tracking

### ⚙️ **Customizable Screening**
- Input your specific job description
- Provide custom instructions for AI analysis
- Tailored summaries based on your requirements
- Re-analyze candidates when criteria change

### ⚡ **Efficient Processing**
- Batch processing for multiple resumes
- Background processing to avoid delays
- Caching system for faster subsequent reviews
- Supports PDF, DOCX, and TXT resume formats

### 🔧 **Enterprise-Ready Architecture**
- Extensible LLM adapter pattern
- Easy integration with different AI providers (OpenAI, internal APIs, etc.)
- Clean separation between business logic and AI provider
- Built for scalability and customization

## Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key (or access to another LLM provider)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rozenborg/swipe.git
   cd swipe
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. **Add resume files:**
   ```bash
   # Place resume files in the candidates/ folder
   # Format: "FirstName LastName ID RESUME.pdf"
   # Example: "John Doe 12345abc RESUME.pdf"
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Open your browser:**
   Navigate to `http://localhost:5000`

## Usage Guide

### Setting Up Your Screening Process

1. **Customize for Your Job:**
   - Click "Customize" in the header
   - Paste your job description
   - Add specific instructions for AI analysis
   - Save and let the system re-analyze candidates

2. **Review Candidates:**
   - Swipe right (→) or press right arrow to SAVE promising candidates
   - Swipe left (←) or press left arrow to PASS on candidates
   - View AI-generated summaries, skills, and fit scores
   - Use the undo button if you make a mistake

3. **Track Your Progress:**
   - Monitor session statistics in the left panel
   - View saved candidates in a separate list
   - Export decisions for further review

### File Organization

```
candidates/          # Place resume files here
├── John Doe 12345abc RESUME.pdf
├── Jane Smith 67890def RESUME.docx
└── Mike Johnson 11111xyz RESUME.txt

data/                # Application data (auto-generated)
├── decisions.json   # Your swipe decisions
├── summaries_cache.json  # AI analysis cache
└── customization_settings.json  # Job description & instructions
```

## Customization & Extension

### For Different Companies

The application is designed to be easily customizable for different organizations:

1. **Custom LLM Providers:**
   - Implement the `BaseLLMClient` interface
   - Add your adapter to the factory
   - Update environment variables

2. **Custom Analysis Criteria:**
   - Modify prompts in the candidate service
   - Add new fields to the analysis output
   - Customize the scoring algorithm

3. **Integration Options:**
   - REST API endpoints for external systems
   - Webhook support for decision notifications
   - Export capabilities for ATS integration

### Development Setup

```bash
# Development mode with auto-reload
export FLASK_DEBUG=1
python app.py

# Run tests (if available)
python -m pytest tests/

# Process resumes in background
curl -X POST http://localhost:5000/api/process/start
```

## API Reference

### Main Endpoints

- `GET /api/candidates` - Get all unreviewed candidates
- `POST /api/swipe` - Record swipe decision
- `GET /api/saved` - Get saved candidates
- `POST /api/customize` - Update job description and instructions
- `POST /api/process/start` - Start background processing

### Example API Usage

```python
import requests

# Get candidates
response = requests.get('http://localhost:5000/api/candidates')
candidates = response.json()

# Save a candidate
requests.post('http://localhost:5000/api/swipe', json={
    'candidate_id': 'john_doe_12345abc',
    'decision': 'save'
})
```

## Technical Architecture

- **Backend:** Flask web framework
- **AI Integration:** Pluggable LLM adapter pattern
- **Resume Parsing:** PyPDF2, python-docx for multiple formats
- **Data Storage:** JSON files (easily replaceable with databases)
- **Frontend:** Modern JavaScript with CSS Grid/Flexbox
- **Processing:** Background threading for batch operations

## Contributing

This project is designed to be extended and customized. Key areas for contribution:

- Additional resume parsers (e.g., Word formats, OCR)
- New LLM provider adapters
- Enhanced UI components
- Database backend options
- Export/import functionality
- Analytics and reporting features

## License

[Add your license here]

## Support

For questions, issues, or customization requests:
- Open an issue on GitHub
- Check the documentation in `/docs` (if available)
- Review example configurations in `/examples` (if available) 