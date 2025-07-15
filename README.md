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