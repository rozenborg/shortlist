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
- AI-powered resume parsing and analysis with enhanced error handling
- Generates candidate summaries, skill assessments, and fit scores
- Extracts key achievements and experience levels with wildcard insights
- Provides reasoning for candidate fit with detailed reservations

### 📱 **Intuitive Swipe Interface** 
- **Three-tier decision system**: Swipe left to pass, right to save, or star for favorites
- Keyboard shortcuts for desktop users (arrow keys, undo, restart)
- Modern, responsive web interface with real-time updates
- Live statistics and progress tracking with completion percentages

### ⚙️ **Customizable Screening**
- Input your specific job description with instant re-analysis
- Provide custom instructions for AI analysis
- Tailored summaries based on your requirements
- Decision modification system - change your mind after review

### ⚡ **Enterprise-Grade Processing**
- **Smart background processing** with real-time status updates
- **Intelligent retry logic** with exponential backoff strategies
- **Configurable timeouts** with auto-detection for reasoning models (GPT-o3, etc.)
- **Batch processing** for multiple resumes with progress tracking
- **Failed candidate management** with manual retry capabilities

### 🔧 **Advanced Candidate Management**
- **Custom ordering** with drag-and-drop reordering of saved candidates
- **Decision history tracking** with full audit trail
- **Excel export** with formatted candidate data and rankings
- **Real-time processing indicators** showing queue status and completion

### 🏢 **Enterprise-Ready Architecture**
- Extensible LLM adapter pattern with timeout optimization
- Easy integration with different AI providers (OpenAI, internal APIs, etc.)
- Clean separation between business logic and AI provider
- Built for scalability with sophisticated error handling

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
   # Edit .env and add your OpenAI API key and processing configuration
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
   Navigate to `http://localhost:5001`

## Enhanced Configuration

### Environment Variables

```bash
# LLM Provider Configuration
OPENAI_API_KEY=your-openai-key
OPENAI_DEFAULT_MODEL=gpt-4o
LLM_PROVIDER=openai

# Advanced Processing Configuration
RESUME_QUICK_TIMEOUT=60        # Timeout for standard models (seconds)
RESUME_LONG_TIMEOUT=180        # Timeout for reasoning models (seconds)
RESUME_MAX_RETRIES=3           # Maximum retry attempts before failure
RESUME_BATCH_SIZE=1            # Candidates per batch (1 = sequential processing)
```

### Smart Timeout Detection
The system automatically detects reasoning models (GPT-o3, etc.) and applies appropriate timeouts:
- **Standard models** (GPT-4, GPT-4o): Use `RESUME_QUICK_TIMEOUT` (60s default)
- **Reasoning models** (o3-mini, o3): Use `RESUME_LONG_TIMEOUT` (180s default)
- **Batch processing**: Scales timeout based on batch size and resume length

## Enhanced Usage Guide

### Setting Up Your Screening Process

1. **Customize for Your Job:**
   - Enter or update job description on startup
   - System automatically clears cache and re-analyzes all candidates
   - Real-time processing status shows progress

2. **Review Candidates with Enhanced Controls:**
   - **Swipe right (→)** or press right arrow to **SAVE** promising candidates
   - **Swipe left (←)** or press left arrow to **PASS** on candidates
   - **Click the star (⭐)** to mark as **STARRED** favorites
   - **Undo button** to reverse your last decision
   - **Restart session** to clear all decisions and start over

3. **Advanced Candidate Management:**
   - **Modify decisions** after review (save → pass, pass → star, etc.)
   - **Reorder saved candidates** with drag-and-drop
   - **Export to Excel** with formatted candidate data
   - **View processing statistics** and queue status

4. **Real-time Processing Monitoring:**
   - Live processing indicators show current status
   - Queue visualization (processing, retry, failed)
   - Completion percentages and estimated time remaining
   - Failed candidate management with manual retry options

### File Organization

```
candidates/          # Place resume files here
├── John Doe 12345abc RESUME.pdf
├── Jane Smith 67890def RESUME.docx
└── Mike Johnson 11111xyz RESUME.txt

data/                # Application data (auto-generated)
├── decisions.json   # Your swipe decisions with timestamps
├── decision_history.json  # Full audit trail of decision changes
├── summaries_cache.json  # AI analysis cache with retry tracking
└── customization_settings.json  # Job description & instructions
```

## Comprehensive API Reference

### Core Candidate Endpoints

- `GET /api/candidates` - Get all candidates with processing status
- `GET /api/candidates/ready` - Get only candidates ready for review
- `GET /api/candidates/processing` - Get candidates currently being processed
- `GET /api/candidates/newly-processed` - Get recently completed candidates
- `GET /api/candidate/<id>` - Get specific candidate details
- `POST /api/swipe` - Record swipe decision (save/pass/star)

### Enhanced Decision Management

- `GET /api/saved` - Get all saved and starred candidates
- `POST /api/saved/reorder` - Update custom order of saved candidates
- `GET /api/passed` - Get all passed candidates
- `POST /api/modify-decision` - Change existing decision (save/pass/star/unreviewed)
- `POST /api/undo` - Undo last swipe decision
- `POST /api/restart` - Clear all decisions and restart session

### Advanced Processing Control

- `POST /api/process/start` - Start background processing
- `GET /api/process/status` - Get detailed processing status
- `GET /api/process/stats` - Get processing statistics and completion rates
- `GET /api/process/config` - Get current processing configuration
- `POST /api/process/config` - Update processing timeouts and batch size
- `POST /api/process/batch` - Force process specific candidates immediately

### Error Handling & Recovery

- `GET /api/process/failed` - Get candidates that failed after max retries
- `POST /api/process/retry/<id>` - Manually retry a failed candidate

### Export & Reporting

- `POST /api/export` - Export saved candidates to formatted Excel file

### Job Description Management

- `GET /api/job-description` - Check if job description exists
- `POST /api/job-description` - Set/update job description (triggers re-analysis)

### Example API Usage

```python
import requests

# Get processing status
response = requests.get('http://localhost:5001/api/process/status')
status = response.json()
print(f"Processing: {status['is_processing']}, Progress: {status['progress']:.1f}%")

# Star a candidate
requests.post('http://localhost:5001/api/swipe', json={
    'candidate_id': 'john_doe_12345abc',
    'decision': 'star'
})

# Modify a decision
requests.post('http://localhost:5001/api/modify-decision', json={
    'candidate_id': 'jane_smith_67890def',
    'new_decision': 'save'  # Change from pass to save
})

# Export saved candidates
response = requests.post('http://localhost:5001/api/export')
with open('candidates.xlsx', 'wb') as f:
    f.write(response.content)
```

## Advanced Processing Architecture

### Smart Retry Logic

The system implements sophisticated error handling with multiple retry queues:

- **Quick Retry Queue**: Network errors, API rate limits (30s - 2min backoff)
- **Long Retry Queue**: Timeout errors, reasoning model delays (5min - 20min backoff)
- **Failed Queue**: Max retries reached, requires manual intervention
- **Processing Queue**: Currently active processing tasks

### Intelligent Timeout Management

- **Model Detection**: Automatically identifies reasoning models (o3, o3-mini)
- **Dynamic Scaling**: Adjusts timeouts based on resume length and batch size
- **Backoff Strategies**: Exponential backoff with jitter to prevent thundering herd

### Real-time Processing Features

- **Live Status Updates**: WebSocket-like polling for real-time UI updates
- **Progress Tracking**: Detailed completion percentages and ETA calculations
- **Queue Visualization**: See exactly what's processing, retrying, or failed
- **Batch Optimization**: Configurable batch sizes for throughput optimization

## Enterprise Features

### Processing Configuration Management

```python
# Update processing configuration via API
import requests

requests.post('http://localhost:5001/api/process/config', json={
    'quick_timeout': 90,      # Increase for slower networks
    'long_timeout': 300,      # Increase for complex reasoning
    'max_retries': 5,         # More retry attempts
    'batch_size': 3           # Process 3 resumes at once
})
```

### Failed Candidate Recovery

```python
# Get failed candidates and retry them
failed = requests.get('http://localhost:5001/api/process/failed').json()
for candidate in failed:
    print(f"Retrying {candidate['filename']}: {candidate['error']}")
    requests.post(f'http://localhost:5001/api/process/retry/{candidate["id"]}')
```

### Audit Trail and Analytics

- **Decision History**: Full audit trail of all decision changes
- **Processing Metrics**: Success rates, retry statistics, timing data
- **Session Analytics**: Review patterns, completion rates, decision distributions

## Technical Architecture

- **Backend:** Flask web framework with enhanced error handling
- **Processing:** Multi-threaded background processing with intelligent retry logic
- **AI Integration:** Pluggable LLM adapter pattern with timeout optimization
- **Resume Parsing:** PyPDF2, python-docx with error recovery
- **Data Storage:** JSON files with atomic writes and backup strategies
- **Frontend:** Modern JavaScript with real-time updates and responsive design
- **Export:** Excel generation with professional formatting and candidate rankings

## Enhanced UI Features

### Real-time Processing Indicators
- **Live status updates** showing processing progress
- **Queue visualization** with retry and failure states
- **Completion percentages** with estimated time remaining
- **New candidate notifications** when processing completes

### Advanced Candidate Management
- **Three-tier decisions**: Save, Pass, Star with visual indicators
- **Drag-and-drop reordering** of saved candidates
- **Decision modification** with change history
- **Search and filtering** (coming soon)

### Keyboard Shortcuts
- **Arrow keys**: Left/Right for Pass/Save decisions
- **Spacebar**: Star current candidate
- **Escape**: Undo last decision
- **R**: Restart session (with confirmation)

## Troubleshooting

### Common Processing Issues

**Timeouts with Reasoning Models:**
```bash
# Increase timeout for o3 models
RESUME_LONG_TIMEOUT=300
OPENAI_DEFAULT_MODEL=o3-mini
```

**High Failure Rates:**
```bash
# Increase retry attempts and use smaller batches
RESUME_MAX_RETRIES=5
RESUME_BATCH_SIZE=1
```

**Slow Processing:**
```bash
# Enable batch processing for faster throughput
RESUME_BATCH_SIZE=3
RESUME_QUICK_TIMEOUT=120
```

### Debugging Failed Candidates

1. Check `/api/process/failed` for error details
2. Review logs for specific error patterns
3. Use `/api/process/retry/<id>` for manual retries
4. Adjust timeout settings based on error types

### Performance Optimization

- **Batch Size**: Increase for faster processing, decrease for stability
- **Timeouts**: Balance between speed and success rates
- **Retry Logic**: Configure based on your LLM provider's reliability

## Custom LLM Integration

### Overview

This application is designed for enterprise environments where organizations may need to integrate with their own LLM infrastructure instead of external services like OpenAI. The system uses a pluggable adapter pattern that makes it easy to connect to any LLM API.

**Perfect for:**
- Companies with internal LLM services
- Organizations requiring on-premises AI solutions
- Enterprises with custom model fine-tuning
- Teams using alternative LLM providers (Azure OpenAI, Anthropic, local models, etc.)
- Corporations with specific security/compliance requirements

### Architecture Overview

The LLM integration follows a clean separation pattern:

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ CandidateService│ ──►│   LLMService     │ ──►│  Your LLM Adapter  │
│                 │    │   (Wrapper)      │    │   (Custom Code)    │
└─────────────────┘    └──────────────────┘    └────────────────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────────┐
                                                │   Your LLM API     │
                                                │ (Internal/External) │
                                                └─────────────────────┘
```

### Step 1: Understanding the Interface

All LLM adapters must implement the `BaseLLMClient` interface:

```python
# src/llm_client.py
import abc

class BaseLLMClient(abc.ABC):
    @abc.abstractmethod
    def chat(self, prompt: str, **kwargs) -> str:
        pass
```

**Key Requirements:**
- Accept a string prompt as input
- Return a string response from your LLM
- Handle any connection/authentication logic internally
- Support additional kwargs for flexibility

### Step 2: Create Your Custom Adapter

Create a new file `src/your_company_adapter.py`:

```python
import os
import requests
from dotenv import load_dotenv
from .llm_client import BaseLLMClient

load_dotenv()

class YourCompanyAdapter(BaseLLMClient):
    def __init__(self):
        # Configure your LLM connection
        self.api_url = os.getenv("YOUR_LLM_API_URL")
        self.api_key = os.getenv("YOUR_LLM_API_KEY")
        self.model_name = os.getenv("YOUR_LLM_MODEL", "your-default-model")
        
        # Validate required configuration
        if not self.api_url or not self.api_key:
            raise ValueError("YOUR_LLM_API_URL and YOUR_LLM_API_KEY must be set")

    def chat(self, prompt, **kwargs):
        """Send prompt to your LLM API and return response"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Adapt this payload to your API's format
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.7)
            }
            
            response = requests.post(
                f"{self.api_url}/generate",  # Adjust endpoint
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract text from your API's response format
            return result.get("text", "")  # Adjust field name
            
        except requests.exceptions.RequestException as e:
            print(f"LLM API error: {e}")
            raise Exception(f"Failed to get LLM response: {e}")
```

### Step 3: Register Your Adapter

Update `src/factory.py` to include your adapter:

```python
import os
from .openai_adapter import OpenAIAdapter
from .your_company_adapter import YourCompanyAdapter

# Add more adapters as needed
try:
    from .azure_openai_adapter import AzureOpenAIAdapter
except ImportError:
    AzureOpenAIAdapter = None

def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "your_company":
        return YourCompanyAdapter()
    elif provider == "azure" and AzureOpenAIAdapter is not None:
        return AzureOpenAIAdapter()
    # Add more providers here
    else:
        return OpenAIAdapter()  # Default fallback
```

### Step 4: Environment Configuration

Update your `.env` file:

```bash
# Choose your LLM provider
LLM_PROVIDER=your_company

# Your custom LLM configuration
YOUR_LLM_API_URL=https://your-internal-llm.company.com/api/v1
YOUR_LLM_API_KEY=your-secret-api-key
YOUR_LLM_MODEL=your-fine-tuned-model-v2

# Additional custom settings (optional)
YOUR_LLM_TIMEOUT=30
YOUR_LLM_MAX_RETRIES=3
YOUR_LLM_BATCH_SIZE=5
```

### Step 5: Testing Your Integration

Create a simple test to verify your adapter works:

```python
# test_custom_llm.py
import os
from dotenv import load_dotenv
from src.factory import get_llm_client

load_dotenv()

def test_custom_llm():
    # Set your provider
    os.environ["LLM_PROVIDER"] = "your_company"
    
    client = get_llm_client()
    
    # Test with a simple prompt
    test_prompt = "Summarize this resume: John Doe, Software Engineer with 5 years Python experience."
    
    try:
        response = client.chat(test_prompt)
        print("✅ LLM Integration Successful!")
        print(f"Response: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ LLM Integration Failed: {e}")
        return False

if __name__ == "__main__":
    test_custom_llm()
```

### Common Enterprise Scenarios

#### 1. Azure OpenAI Integration

```python
# src/azure_openai_adapter.py
import os
from openai import AzureOpenAI
from .llm_client import BaseLLMClient

class AzureOpenAIAdapter(BaseLLMClient):
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    def chat(self, prompt, **kwargs):
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
```

#### 2. Anthropic Claude Integration

```python
# src/anthropic_adapter.py
import os
from anthropic import Anthropic
from .llm_client import BaseLLMClient

class AnthropicAdapter(BaseLLMClient):
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

    def chat(self, prompt, **kwargs):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 2000),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
```

#### 3. Local Model Integration (Ollama)

```python
# src/ollama_adapter.py
import requests
import os
from .llm_client import BaseLLMClient

class OllamaAdapter(BaseLLMClient):
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")

    def chat(self, prompt, **kwargs):
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json()["response"]
```

#### 4. Internal REST API Integration

```python
# src/internal_api_adapter.py
import os
import requests
from .llm_client import BaseLLMClient

class InternalAPIAdapter(BaseLLMClient):
    def __init__(self):
        self.api_url = os.getenv("INTERNAL_LLM_URL")
        self.auth_token = os.getenv("INTERNAL_LLM_TOKEN")
        
        # Support for internal auth systems
        self.cert_path = os.getenv("INTERNAL_LLM_CERT_PATH")
        self.verify_ssl = os.getenv("INTERNAL_LLM_VERIFY_SSL", "true").lower() == "true"

    def chat(self, prompt, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "X-Request-Source": "swipe-app"
        }
        
        session = requests.Session()
        if self.cert_path:
            session.cert = self.cert_path
        
        response = session.post(
            f"{self.api_url}/chat",
            headers=headers,
            json={
                "message": prompt,
                "user_id": "swipe-system",
                "parameters": kwargs
            },
            verify=self.verify_ssl,
            timeout=60
        )
        
        response.raise_for_status()
        return response.json()["response"]["text"]
```

### Advanced Configuration

#### 1. Connection Pooling and Retries

```python
# Enhanced adapter with connection pooling
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class EnterpriseAdapter(BaseLLMClient):
    def __init__(self):
        self.session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Your configuration...
```

#### 2. Async Processing Support

For high-volume processing, consider implementing async support:

```python
# src/async_llm_adapter.py
import asyncio
import aiohttp
from .llm_client import BaseLLMClient

class AsyncLLMAdapter(BaseLLMClient):
    def __init__(self):
        self.api_url = os.getenv("ASYNC_LLM_URL")
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    async def async_chat(self, prompt, **kwargs):
        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/generate",
                    json={"prompt": prompt}
                ) as response:
                    result = await response.json()
                    return result["text"]

    def chat(self, prompt, **kwargs):
        # Sync wrapper for async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_chat(prompt, **kwargs))
        finally:
            loop.close()
```

### Troubleshooting

#### Common Issues:

1. **Import Errors**: Ensure your adapter file is in the `src/` directory and properly imported in `factory.py`

2. **Authentication Failures**: Verify your API keys and endpoints are correctly set in the `.env` file

3. **Network Issues**: Check firewall rules, VPN connections, and internal network policies

4. **Response Format Errors**: Ensure your adapter correctly parses your API's response format

5. **Timeout Issues**: Adjust timeout values for slower internal APIs

#### Debugging:

Add logging to your adapter for better debugging:

```python
import logging

class DebugAdapter(BaseLLMClient):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        # Your initialization...

    def chat(self, prompt, **kwargs):
        self.logger.debug(f"Sending prompt: {prompt[:100]}...")
        try:
            response = # your API call
            self.logger.debug(f"Received response: {response[:100]}...")
            return response
        except Exception as e:
            self.logger.error(f"LLM API error: {e}")
            raise
```

### Security Considerations

For enterprise deployments:

1. **Environment Variables**: Never hardcode API keys or sensitive URLs
2. **Certificate Validation**: Use proper SSL/TLS verification for internal APIs
3. **Rate Limiting**: Implement proper rate limiting to avoid overwhelming your LLM service
4. **Error Handling**: Avoid leaking sensitive information in error messages
5. **Audit Logging**: Log API usage for compliance and monitoring

## Contributing

This project is designed to be extended and customized. Key areas for contribution:

- Additional resume parsers (e.g., Word formats, OCR)
- New LLM provider adapters
- Enhanced UI components with real-time features
- Database backend options
- Advanced export/import functionality
- Analytics and reporting dashboards
- Mobile app development

## License

[Add your license here]

## Support

For questions, issues, or customization requests:
- Open an issue on GitHub
- Check the documentation in `/docs` (if available)
- Review example configurations in `/examples` (if available) 