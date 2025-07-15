import threading
import time
import json
import os
from typing import Dict, List
from .batch_processor import BatchProcessor

class BackgroundProcessor:
    def __init__(self, candidate_service, resume_parser, llm_service):
        self.candidate_service = candidate_service
        self.resume_parser = resume_parser
        self.llm_service = llm_service
        self.batch_processor = BatchProcessor(llm_service)
        self.processing_thread = None
        self.is_processing = False
        self.processed_count = 0
        self.total_count = 0
        self.status = "idle"
        
    def start_background_processing(self):
        """Start processing resumes in the background"""
        if self.is_processing:
            return
            
        self.processing_thread = threading.Thread(target=self._process_all_resumes)
        self.processing_thread.daemon = True
        self.is_processing = True
        self.status = "processing"
        self.processing_thread.start()
        
    def _process_all_resumes(self):
        """Process all resumes in the background"""
        try:
            customization_settings = self.candidate_service.customization_service.get_settings()
            # Get all resume files
            resumes = self.resume_parser.get_all_resumes(self.candidate_service.candidates_folder)
            
            # Filter out already processed resumes
            unprocessed_resumes = []
            for resume in resumes:
                if resume['id'] not in self.candidate_service.summaries:
                    unprocessed_resumes.append(resume)
            
            if not unprocessed_resumes:
                self.status = "completed"
                self.is_processing = False
                return
            
            self.total_count = len(unprocessed_resumes)
            self.processed_count = 0
            
            # Prepare resume data for batch processing
            resumes_data = []
            for resume in unprocessed_resumes:
                try:
                    resume_text = self.resume_parser.parse_resume(resume['path'])
                    resumes_data.append({
                        'id': resume['id'],
                        'name': resume['name'],
                        'text': resume_text
                    })
                except Exception as e:
                    print(f"Error reading resume {resume['filename']}: {e}")
                    continue
            
            # Process in batches
            batch_size = 5  # Process 5 resumes at a time
            for i in range(0, len(resumes_data), batch_size):
                if not self.is_processing:  # Check if processing was stopped
                    break
                    
                batch = resumes_data[i:i + batch_size]
                print(f"Processing batch {i//batch_size + 1}: {[r['name'] for r in batch]}")
                
                # Process batch
                results = self.batch_processor.process_batch(batch, customization_settings, batch_size)
                print(f"Batch completed. Processed {len(results)} candidates.")
                
                # Save results
                for candidate_id, summary in results.items():
                    self.candidate_service.summaries[candidate_id] = summary
                    self.processed_count += 1
                    print(f"  ✅ {candidate_id}: {summary.get('summary', 'N/A')[:50]}...")
                
                # Save to file periodically
                self.candidate_service._save_data()
                
                # Small delay to prevent overwhelming the API
                time.sleep(0.5)
            
            self.status = "completed"
            
        except Exception as e:
            print(f"Background processing error: {e}")
            self.status = "error"
        finally:
            self.is_processing = False
    
    def get_status(self) -> Dict:
        """Get current processing status"""
        return {
            "is_processing": self.is_processing,
            "status": self.status,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "progress": (self.processed_count / self.total_count * 100) if self.total_count > 0 else 0
        }
    
    def stop_processing(self):
        """Stop background processing"""
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
    
    def force_process_batch(self, candidate_ids: List[str]) -> Dict[str, Dict]:
        """Force process a specific batch of candidates immediately"""
        customization_settings = self.candidate_service.customization_service.get_settings()
        resumes = self.resume_parser.get_all_resumes(self.candidate_service.candidates_folder)
        
        # Find the requested resumes
        target_resumes = [r for r in resumes if r['id'] in candidate_ids]
        
        if not target_resumes:
            return {}
        
        # Prepare data
        resumes_data = []
        for resume in target_resumes:
            try:
                resume_text = self.resume_parser.parse_resume(resume['path'])
                resumes_data.append({
                    'id': resume['id'],
                    'name': resume['name'],
                    'text': resume_text
                })
            except Exception as e:
                print(f"Error reading resume {resume['filename']}: {e}")
                continue
        
        # Process batch immediately
        results = self.batch_processor.process_batch(resumes_data, customization_settings, len(resumes_data))
        
        # Save results
        for candidate_id, summary in results.items():
            self.candidate_service.summaries[candidate_id] = summary
        
        self.candidate_service._save_data()
        
        return results 