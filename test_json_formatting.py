#!/usr/bin/env python3
"""
JSON Formatting Test for Custom LLM Adapters

This script tests whether your custom LLM adapter is returning properly formatted JSON
that the Swipe application can parse successfully.
"""

import os
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_json_formatting():
    """Test JSON formatting with your custom LLM adapter"""
    print("🧪 Testing JSON Formatting with Custom LLM Adapter")
    print("=" * 60)
    
    try:
        # Import your LLM client
        from src.factory import get_llm_client
        from src.batch_processor import BatchProcessor
        
        client = get_llm_client()
        processor = BatchProcessor(client)
        
        print(f"✅ LLM Client: {type(client).__name__}")
        print(f"✅ Using Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
        print()
        
        # Test 1: Simple JSON Structure Test
        print("🔍 Test 1: Basic JSON Response")
        print("-" * 40)
        
        simple_prompt = '''Return a valid JSON object with these exact keys:
{
  "nickname": "Test Candidate",
  "summary": "Software engineer with 5 years experience",
  "reservations": ["No leadership experience", "Limited domain knowledge"]
}

Return ONLY the JSON object, no other text.'''
        
        try:
            start_time = time.time()
            response = client.chat(simple_prompt)
            response_time = time.time() - start_time
            
            print(f"⏱️  Response time: {response_time:.2f}s")
            print(f"📝 Raw response (first 200 chars): {response[:200]}...")
            print()
            
            # Try to parse with enhanced parsing
            try:
                result = processor._parse_json_response(response)
                print("✅ JSON parsing successful!")
                print(f"📊 Parsed keys: {list(result.keys())}")
                print(f"📝 Nickname: {result.get('nickname', 'N/A')}")
                print(f"📝 Summary: {result.get('summary', 'N/A')[:100]}...")
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
                print("🔧 Trying fallback parsing...")
                fallback = processor._parse_fallback_response(response)
                print(f"📝 Fallback summary: {fallback['summary'][:100]}...")
                
        except Exception as e:
            print(f"❌ LLM request failed: {e}")
        
        print("\n" + "=" * 60)
        
        # Test 2: Full Resume Analysis Format
        print("🔍 Test 2: Full Resume Analysis Format")
        print("-" * 40)
        
        # Create a mock resume data for testing
        mock_resume = {
            'id': 'test_candidate_001',
            'name': 'Test Candidate',
            'text': '''John Smith
Software Engineer
Email: john@email.com

EXPERIENCE:
Senior Software Engineer at TechCorp (2020-2024)
- Led team of 5 engineers developing web applications
- Improved system performance by 40%
- Managed $2M budget for cloud infrastructure

Software Engineer at StartupXYZ (2018-2020)
- Built microservices architecture serving 1M+ users
- Reduced deployment time from 2 hours to 15 minutes

EDUCATION:
BS Computer Science, State University (2014-2018)

SKILLS:
Python, JavaScript, AWS, Docker, Kubernetes'''
        }
        
        mock_settings = {'job_description': 'Senior Software Engineer position requiring team leadership and cloud architecture experience.'}
        
        try:
            start_time = time.time()
            result = processor.process_single_resume(mock_resume, mock_settings)
            process_time = time.time() - start_time
            
            print(f"⏱️  Processing time: {process_time:.2f}s")
            print(f"✅ Processing completed successfully!")
            print()
            
            # Check result structure
            required_keys = ['nickname', 'summary', 'reservations', 'relevant_achievements', 'wildcard', 'work_history', 'differentiators']
            missing_keys = [k for k in required_keys if k not in result]
            
            if not missing_keys:
                print("✅ All required keys present!")
                print(f"📝 Nickname: {result['nickname']}")
                print(f"📝 Summary: {result['summary'][:150]}...")
                print(f"📊 Differentiators: {len(result['differentiators'])} found")
                print(f"📊 Achievements: {len(result['relevant_achievements'])} found")
                print(f"📊 Work History: {len(result['work_history'])} positions")
                print(f"🎯 Reservations: {result['reservations']}")
            else:
                print(f"⚠️  Missing keys: {missing_keys}")
                print(f"📊 Present keys: {list(result.keys())}")
                
        except Exception as e:
            print(f"❌ Full processing failed: {e}")
        
        print("\n" + "=" * 60)
        
        # Test 3: Malformed Response Handling
        print("🔍 Test 3: Malformed Response Recovery")
        print("-" * 40)
        
        # Simulate various malformed responses
        test_responses = [
            '```json\n{"nickname": "Test", "summary": "Engineer"}\n```',  # Markdown blocks
            '{"nickname": "Test", "summary": "Engineer",}',  # Trailing comma
            'Here is the analysis: {"nickname": "Test"}',  # Extra text
            '```\n{"nickname": "Test"}\n```',  # Generic code blocks
        ]
        
        for i, malformed_response in enumerate(test_responses, 1):
            print(f"  Testing malformed response {i}:")
            try:
                parsed = processor._parse_json_response(malformed_response)
                print(f"    ✅ Recovered successfully: {list(parsed.keys())}")
            except Exception as e:
                print(f"    ❌ Recovery failed: {e}")
        
        print("\n" + "=" * 60)
        print("🎯 RECOMMENDATIONS FOR YOUR CUSTOM ADAPTER:")
        print("-" * 40)
        print("1. Ensure your LLM returns ONLY JSON without markdown blocks")
        print("2. Test with various resume lengths and complexity")
        print("3. Monitor response times - aim for under 30 seconds")
        print("4. Check for consistent field structure in responses")
        print("5. Consider adjusting temperature/parameters for more consistent formatting")
        print("\n✨ The enhanced JSON parsing should handle most formatting issues!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure your custom adapter is properly configured in src/factory.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_json_formatting() 