#!/usr/bin/env python3
"""
Resume Processing Diagnostic Tool
=================================

This script tests all major failure points in the resume processing pipeline:
1. File parsing (PDF/DOCX extraction)
2. LLM adapter connectivity and functionality
3. JSON response parsing
4. File permissions and sizes
5. Resume text quality
6. API timeouts and rate limiting

Run this script to identify the root cause of "error processing resume" issues.

Usage: python diagnose_resume_issues.py
"""

import os
import sys
import json
import time
import traceback
from pathlib import Path

# Add the project root to the Python path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  WARNING: python-dotenv not installed, skipping .env loading")

class ResumeDiagnostic:
    def __init__(self):
        self.candidates_folder = 'candidates'
        self.test_results = {
            'file_parsing': [],
            'llm_connectivity': [],
            'json_parsing': [],
            'file_issues': [],
            'summary': {}
        }
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print('='*60)
        
    def print_success(self, message):
        print(f"✅ {message}")
        
    def print_warning(self, message):
        print(f"⚠️  {message}")
        
    def print_error(self, message):
        print(f"❌ {message}")
        
    def print_info(self, message):
        print(f"ℹ️  {message}")

    def test_file_parsing(self):
        """Test PDF and DOCX file parsing capabilities"""
        self.print_header("Testing File Parsing")
        
        try:
            from src.resume_parser import ResumeParser
            parser = ResumeParser()
        except ImportError as e:
            self.print_error(f"Cannot import ResumeParser: {e}")
            return
        
        if not os.path.exists(self.candidates_folder):
            self.print_error(f"Candidates folder '{self.candidates_folder}' not found")
            return
            
        resume_files = [f for f in os.listdir(self.candidates_folder) 
                       if f.upper().endswith(('RESUME.PDF', 'RESUME.DOCX', 'RESUME.TXT'))]
        
        if not resume_files:
            self.print_warning("No resume files found in candidates folder")
            return
            
        self.print_info(f"Found {len(resume_files)} resume files to test")
        
        parsing_results = {}
        for filename in resume_files[:10]:  # Test first 10 files
            file_path = os.path.join(self.candidates_folder, filename)
            
            try:
                # Check file accessibility
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    parsing_results[filename] = {"error": "Empty file", "size": file_size}
                    continue
                    
                if file_size > 20 * 1024 * 1024:  # 20MB
                    parsing_results[filename] = {"error": "File too large", "size": file_size}
                    continue
                
                # Test parsing
                start_time = time.time()
                text = parser.parse_resume(file_path)
                parse_time = time.time() - start_time
                
                parsing_results[filename] = {
                    "success": True,
                    "size": file_size,
                    "text_length": len(text),
                    "parse_time": round(parse_time, 2),
                    "text_preview": text[:200] + "..." if len(text) > 200 else text
                }
                
                if len(text) < 100:
                    parsing_results[filename]["warning"] = "Very short text extracted - possibly scanned PDF"
                    
            except Exception as e:
                parsing_results[filename] = {
                    "error": str(e),
                    "size": file_size if 'file_size' in locals() else "unknown",
                    "error_type": type(e).__name__
                }
        
        # Report results
        successful = sum(1 for r in parsing_results.values() if r.get("success"))
        failed = len(parsing_results) - successful
        
        self.print_info(f"Parsing Results: {successful} successful, {failed} failed")
        
        for filename, result in parsing_results.items():
            if result.get("success"):
                self.print_success(f"{filename}: {result['text_length']} chars in {result['parse_time']}s")
                if result.get("warning"):
                    self.print_warning(f"  {result['warning']}")
            else:
                self.print_error(f"{filename}: {result.get('error', 'Unknown error')}")
                
        self.test_results['file_parsing'] = parsing_results
        return parsing_results

    def test_llm_connectivity(self):
        """Test LLM adapter connectivity and functionality"""
        self.print_header("Testing LLM Connectivity")
        
        try:
            from src.factory import get_llm_client
            client = get_llm_client()
            self.print_success("LLM client imported successfully")
        except ImportError as e:
            self.print_error(f"Cannot import LLM client: {e}")
            return None
        except Exception as e:
            self.print_error(f"Error creating LLM client: {e}")
            return None
        
        # Test 1: Simple connectivity test
        self.print_info("Testing basic connectivity...")
        simple_tests = []
        
        try:
            start_time = time.time()
            response = client.chat("Reply with exactly 'TEST_SUCCESS' and nothing else.")
            response_time = time.time() - start_time
            
            if "TEST_SUCCESS" in response.strip():
                self.print_success(f"Basic connectivity test passed ({response_time:.2f}s)")
                simple_tests.append({"test": "basic", "success": True, "time": response_time})
            else:
                self.print_warning(f"Unexpected response: '{response.strip()}'")
                simple_tests.append({"test": "basic", "success": False, "response": response.strip()})
                
        except Exception as e:
            self.print_error(f"Basic connectivity failed: {e}")
            simple_tests.append({"test": "basic", "success": False, "error": str(e)})
        
        # Test 2: JSON response test
        self.print_info("Testing JSON response handling...")
        
        json_prompt = '''Return a valid JSON object with this exact structure:
{
  "test": "json_response",
  "status": "success",
  "number": 42
}'''
        
        try:
            start_time = time.time()
            response = client.chat(json_prompt)
            response_time = time.time() - start_time
            
            # Try to parse as JSON
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.startswith('```'):
                clean_response = clean_response[3:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
                
            parsed = json.loads(clean_response.strip())
            
            if parsed.get("test") == "json_response" and parsed.get("status") == "success":
                self.print_success(f"JSON response test passed ({response_time:.2f}s)")
                simple_tests.append({"test": "json", "success": True, "time": response_time})
            else:
                self.print_warning(f"JSON structure incorrect: {parsed}")
                simple_tests.append({"test": "json", "success": False, "parsed": parsed})
                
        except json.JSONDecodeError as e:
            self.print_error(f"JSON parsing failed: {e}")
            self.print_info(f"Raw response: '{response[:200]}...'")
            simple_tests.append({"test": "json", "success": False, "error": "JSON decode error", "response": response[:200]})
        except Exception as e:
            self.print_error(f"JSON response test failed: {e}")
            simple_tests.append({"test": "json", "success": False, "error": str(e)})
        
        # Test 3: Large payload test (similar to resume processing)
        self.print_info("Testing large payload handling...")
        
        large_text = "This is a test resume content. " * 200  # ~6KB of text
        large_prompt = f'''Analyze this resume and return a JSON object with these keys:
- "nickname": A 2-word nickname
- "summary": A brief summary
- "reservations": An array of 2 concerns

Resume content: {large_text}'''
        
        try:
            start_time = time.time()
            response = client.chat(large_prompt)
            response_time = time.time() - start_time
            
            # Try to parse the response
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.startswith('```'):
                clean_response = clean_response[3:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
                
            parsed = json.loads(clean_response.strip())
            
            required_keys = ["nickname", "summary", "reservations"]
            has_all_keys = all(key in parsed for key in required_keys)
            
            if has_all_keys:
                self.print_success(f"Large payload test passed ({response_time:.2f}s)")
                simple_tests.append({"test": "large_payload", "success": True, "time": response_time})
            else:
                missing = [k for k in required_keys if k not in parsed]
                self.print_warning(f"Large payload missing keys: {missing}")
                simple_tests.append({"test": "large_payload", "success": False, "missing_keys": missing})
                
        except Exception as e:
            self.print_error(f"Large payload test failed: {e}")
            simple_tests.append({"test": "large_payload", "success": False, "error": str(e)})
            
        self.test_results['llm_connectivity'] = simple_tests
        return simple_tests

    def test_resume_processing_pipeline(self):
        """Test the full resume processing pipeline with a real resume"""
        self.print_header("Testing Full Resume Processing Pipeline")
        
        try:
            from src.resume_parser import ResumeParser
            from src.factory import get_llm_client
            from src.batch_processor import BatchProcessor
            from src.customization_service import CustomizationService
        except ImportError as e:
            self.print_error(f"Cannot import required modules: {e}")
            return None
        
        # Get a test resume
        if not os.path.exists(self.candidates_folder):
            self.print_error(f"Candidates folder '{self.candidates_folder}' not found")
            return None
            
        resume_files = [f for f in os.listdir(self.candidates_folder) 
                       if f.upper().endswith(('RESUME.PDF', 'RESUME.DOCX'))]
        
        if not resume_files:
            self.print_error("No resume files found for pipeline test")
            return None
        
        test_file = resume_files[0]  # Use first resume file
        self.print_info(f"Testing pipeline with: {test_file}")
        
        try:
            # Step 1: Parse resume
            parser = ResumeParser()
            file_path = os.path.join(self.candidates_folder, test_file)
            resume_text = parser.parse_resume(file_path)
            self.print_success(f"Step 1: Resume parsed ({len(resume_text)} chars)")
            
            # Step 2: Prepare data
            resume_data = {
                'id': test_file.replace(' ', '_').replace('.', '_'),
                'name': test_file.split(' ')[0] if ' ' in test_file else "Test",
                'text': resume_text
            }
            
            # Step 3: Get customization settings
            customization_service = CustomizationService()
            settings = customization_service.get_settings()
            self.print_success("Step 2: Settings loaded")
            
            # Step 4: Process with batch processor
            client = get_llm_client()
            batch_processor = BatchProcessor(client)
            
            start_time = time.time()
            result = batch_processor.process_single_resume(resume_data, settings)
            process_time = time.time() - start_time
            
            # Step 5: Validate result
            required_keys = ['nickname', 'summary', 'reservations', 'relevant_achievements', 'wildcard', 'work_history']
            missing_keys = [k for k in required_keys if k not in result]
            
            if not missing_keys:
                self.print_success(f"Step 3: Pipeline completed successfully ({process_time:.2f}s)")
                self.print_info(f"Result summary: {result.get('summary', 'N/A')[:100]}...")
                return {"success": True, "result": result, "time": process_time}
            else:
                self.print_error(f"Step 3: Pipeline failed - missing keys: {missing_keys}")
                return {"success": False, "missing_keys": missing_keys, "result": result}
                
        except Exception as e:
            self.print_error(f"Pipeline test failed: {e}")
            self.print_info(f"Full error: {traceback.format_exc()}")
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    def test_environment_configuration(self):
        """Test environment and configuration issues"""
        self.print_header("Testing Environment Configuration")
        
        # Check required environment variables
        env_vars = ['LLM_PROVIDER']
        self.print_info("Checking environment variables...")
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                self.print_success(f"{var} = '{value}'")
            else:
                self.print_warning(f"{var} not set")
        
        # Check file permissions
        self.print_info("Checking file permissions...")
        
        folders_to_check = ['candidates', 'data', 'src']
        for folder in folders_to_check:
            if os.path.exists(folder):
                if os.access(folder, os.R_OK):
                    self.print_success(f"{folder}/ readable")
                else:
                    self.print_error(f"{folder}/ not readable")
            else:
                self.print_warning(f"{folder}/ does not exist")
        
        # Check Python dependencies
        self.print_info("Checking Python dependencies...")
        
        required_packages = [
            ('PyPDF2', 'PyPDF2'),
            ('python-docx', 'docx'),
            ('openai', 'openai'),
            ('flask', 'flask'),
            ('requests', 'requests')
        ]
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                self.print_success(f"{package_name} available")
            except ImportError:
                self.print_error(f"{package_name} not available")

    def generate_summary_report(self):
        """Generate a summary report of all tests"""
        self.print_header("DIAGNOSTIC SUMMARY REPORT")
        
        # File parsing summary
        parsing_results = self.test_results.get('file_parsing', {})
        if parsing_results:
            successful_parsing = sum(1 for r in parsing_results.values() if r.get('success'))
            total_files = len(parsing_results)
            self.print_info(f"File Parsing: {successful_parsing}/{total_files} files parsed successfully")
            
            failed_files = [f for f, r in parsing_results.items() if not r.get('success')]
            if failed_files:
                self.print_warning(f"Failed files: {', '.join(failed_files[:5])}")
                if len(failed_files) > 5:
                    self.print_warning(f"... and {len(failed_files) - 5} more")
        
        # LLM connectivity summary
        llm_results = self.test_results.get('llm_connectivity', [])
        if llm_results:
            successful_tests = sum(1 for r in llm_results if r.get('success'))
            total_tests = len(llm_results)
            self.print_info(f"LLM Connectivity: {successful_tests}/{total_tests} tests passed")
        
        # Recommendations
        self.print_header("RECOMMENDATIONS")
        
        if parsing_results:
            parsing_issues = [f for f, r in parsing_results.items() if not r.get('success')]
            if parsing_issues:
                self.print_warning(f"File parsing issues detected in {len(parsing_issues)} files")
                self.print_info("Consider: Check for corrupted PDFs, password-protected files, or scanned documents")
        
        if llm_results:
            llm_issues = [r for r in llm_results if not r.get('success')]
            if llm_issues:
                self.print_warning("LLM connectivity issues detected")
                self.print_info("Consider: Check API credentials, network connectivity, or timeout settings")
        
        # Export detailed results
        try:
            with open('diagnostic_results.json', 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            self.print_success("Detailed results saved to 'diagnostic_results.json'")
        except Exception as e:
            self.print_error(f"Could not save results: {e}")

    def run_full_diagnostic(self):
        """Run all diagnostic tests"""
        print("🏥 Resume Processing Diagnostic Tool")
        print("====================================")
        print("This tool will test all components of the resume processing pipeline.")
        print("Results will help identify the cause of processing errors.")
        
        start_time = time.time()
        
        # Run all tests
        self.test_environment_configuration()
        self.test_file_parsing()
        self.test_llm_connectivity()
        self.test_resume_processing_pipeline()
        
        # Generate summary
        total_time = time.time() - start_time
        self.generate_summary_report()
        
        self.print_info(f"Diagnostic completed in {total_time:.2f} seconds")
        print("\n" + "="*60)
        print("📋 Next Steps:")
        print("1. Review the diagnostic results above")
        print("2. Check 'diagnostic_results.json' for detailed data")
        print("3. Address any failed tests before resume processing")
        print("="*60)

if __name__ == "__main__":
    diagnostic = ResumeDiagnostic()
    diagnostic.run_full_diagnostic() 