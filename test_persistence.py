#!/usr/bin/env python3
"""
Test script to verify retry state persistence functionality
"""

import os
import sys
import json
from datetime import datetime

# Add the src directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.background_processor import BackgroundProcessor
from src.candidate_service import CandidateService
from src.resume_parser import ResumeParser
from src.factory import get_llm_client
from src.manager import LLMService
from src.customization_service import CustomizationService

def test_retry_state_persistence():
    """Test that retry state persistence works correctly"""
    print("🧪 Testing Retry State Persistence...")
    
    # Initialize services (similar to app.py)
    try:
        client = get_llm_client()
        llm_service = LLMService(client)
        resume_parser = ResumeParser()
        customization_service = CustomizationService()
        candidate_service = CandidateService(llm_service, resume_parser, customization_service)
        
        # Create BackgroundProcessor instance
        background_processor = BackgroundProcessor(candidate_service, resume_parser, llm_service)
        
        print(f"📁 Retry state file location: {background_processor.retry_state_file}")
        
        # Check initial state
        print("\n1️⃣ Initial State:")
        print(f"   Failed queue: {len(background_processor.retry_queues['failed'])}")
        print(f"   Quick retry queue: {len(background_processor.retry_queues['quick_retry'])}")
        print(f"   Long retry queue: {len(background_processor.retry_queues['long_retry'])}")
        print(f"   Format retry queue: {len(background_processor.retry_queues['format_retry'])}")
        
        # Simulate some failed candidates
        print("\n2️⃣ Simulating Failed Candidates...")
        
        # Add a mock failed candidate
        mock_failed_candidate = {
            'id': 'test_candidate_001',
            'filename': 'test_resume.pdf',
            'path': '/fake/path/test_resume.pdf',
            'name': 'Test Candidate',
            'error': 'Simulated timeout error',
            'error_type': 'timeout',
            'retry_count': 3,
            'failed_at': datetime.now().isoformat()
        }
        
        background_processor.retry_queues['failed'].append(mock_failed_candidate)
        background_processor.retry_counts['test_candidate_001'] = 3
        background_processor.last_retry_time['test_candidate_001'] = datetime.now()
        
        # Add a mock retry candidate
        mock_retry_candidate = {
            'id': 'test_candidate_002',
            'filename': 'test_resume_2.pdf',
            'path': '/fake/path/test_resume_2.pdf',
            'name': 'Test Candidate 2'
        }
        
        background_processor.retry_queues['quick_retry'].append(mock_retry_candidate)
        background_processor.retry_counts['test_candidate_002'] = 1
        background_processor.last_retry_time['test_candidate_002'] = datetime.now()
        
        print(f"   Added 1 failed candidate and 1 retry candidate")
        
        # Save state
        print("\n3️⃣ Saving State to Disk...")
        background_processor._save_retry_state()
        
        if os.path.exists(background_processor.retry_state_file):
            with open(background_processor.retry_state_file, 'r') as f:
                saved_data = json.load(f)
            print(f"   ✅ State saved successfully")
            print(f"   📊 Saved data contains:")
            print(f"      - Failed: {len(saved_data['retry_queues']['failed'])}")
            print(f"      - Quick retry: {len(saved_data['retry_queues']['quick_retry'])}")
            print(f"      - Retry counts: {len(saved_data['retry_counts'])}")
            print(f"      - Last retry times: {len(saved_data['last_retry_time'])}")
        else:
            print(f"   ❌ State file was not created")
            return False
        
        # Create a new instance to test loading
        print("\n4️⃣ Testing State Restoration...")
        new_background_processor = BackgroundProcessor(candidate_service, resume_parser, llm_service)
        
        # Check if state was restored
        restored_failed_count = len(new_background_processor.retry_queues['failed'])
        restored_retry_count = len(new_background_processor.retry_queues['quick_retry'])
        restored_retry_counts = len(new_background_processor.retry_counts)
        
        print(f"   Restored failed queue: {restored_failed_count}")
        print(f"   Restored quick retry queue: {restored_retry_count}")
        print(f"   Restored retry counts: {restored_retry_counts}")
        
        # Verify restoration
        success = (
            restored_failed_count == 1 and
            restored_retry_count == 1 and
            restored_retry_counts == 2
        )
        
        if success:
            print(f"\n✅ PERSISTENCE TEST PASSED!")
            print(f"   Failed candidates will survive application restart")
            
            # Verify specific candidate data
            restored_failed = new_background_processor.retry_queues['failed'][0]
            if restored_failed['id'] == 'test_candidate_001':
                print(f"   ✅ Failed candidate data integrity confirmed")
            
        else:
            print(f"\n❌ PERSISTENCE TEST FAILED!")
            print(f"   Expected: 1 failed, 1 retry, 2 retry counts")
            print(f"   Got: {restored_failed_count} failed, {restored_retry_count} retry, {restored_retry_counts} retry counts")
            
        # Cleanup
        print("\n5️⃣ Cleaning up test data...")
        if os.path.exists(background_processor.retry_state_file):
            os.remove(background_processor.retry_state_file)
            print(f"   🗑️  Removed test retry state file")
            
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Retry State Persistence Test\n")
    
    # Check if we're in the right directory
    if not os.path.exists('src'):
        print("❌ Please run this script from the swipe project root directory")
        sys.exit(1)
    
    success = test_retry_state_persistence()
    
    if success:
        print("\n🎉 All tests passed! Retry state persistence is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Tests failed! There may be an issue with retry state persistence.")
        sys.exit(1) 