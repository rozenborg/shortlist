# Switchable LLM Client Project Foundation

## Overview
This is a flexible foundation for building AI-powered applications that can work with different LLM providers (OpenAI, internal company APIs, Amazon Bedrock, etc.) without changing your core application code.

**Use Case**: Build open source AI projects that can be easily adapted for corporate environments with custom internal LLM APIs.

**Key Benefits**:
- Build once, deploy anywhere
- Clean separation between business logic and LLM provider details
- Easy to switch providers via environment variables
- Perfect for corporate environments with custom internal APIs

## Architecture Pattern
Uses the Adapter Pattern to create a common interface (`BaseLLMClient`) that different LLM providers can implement. Your application code only depends on this interface, never on specific provider APIs.

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd my-llm-project
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your environment:
   - Copy `env.example` to `.env`:
     ```bash
     cp env.example .env
     ```
   - Edit `.env` and add your OpenAI API key.
4. Run the application:
   ```bash
   python app.py
   ```

## Usage Examples

After setup, you can use this as a foundation for various AI applications:

```python
# Document analyzer
service.chat("Analyze this contract and identify key risks: [document text]")

# Code reviewer  
service.chat("Review this Python function for bugs and improvements: [code]")

# Content generator
service.chat("Write a technical blog post about microservices architecture")

# Data extractor
service.chat("Extract key metrics from this financial report: [report text]")
```

## Extension Points

To build specific applications on this foundation:

1. **Add specialized service methods** in `LLMService` for your use case
2. **Create prompt templates** for consistent formatting
3. **Add validation and preprocessing** for your specific data types
4. **Implement caching** for expensive operations
5. **Add streaming support** for real-time applications

## Corporate Deployment

When moving to your company environment:
1. Create a new adapter (e.g., `CompanyInternalAdapter`) that implements `BaseLLMClient`
2. Update the factory to recognize your company's provider
3. Set environment variables to use your company's LLM
4. Your application code remains unchanged 