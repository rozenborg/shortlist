import threading
import time
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .batch_processor import BatchProcessor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundProcessor:
    def __init__(self, candidate_service, resume_parser, llm_service):
        self.candidate_service = candidate_service
        self.resume_parser = resume_parser
        self.llm_service = llm_service
        self.batch_processor = BatchProcessor(llm_service)
        
        # Processing state
        self.processing_thread = None
        self.is_processing = False
        self.processed_count = 0
        self.total_count = 0
        self.status = "idle"
        
        # Enhanced retry and error handling
        self.retry_queues = {
            'quick_retry': [],      # Network errors, quick retry with 30s timeout
            'long_retry': [],       # Timeout errors, retry with 3min timeout  
            'format_retry': [],     # Formatting failures, retry with enhanced prompts
            'failed': [],           # Multiple failures, manual review needed
            'processing': []        # Currently being processed
        }
        
        self.retry_counts = {}      # Track retry attempts per candidate
        self.last_retry_time = {}   # Track last retry time for backoff
        
        # Configuration
        self.config = {
            'quick_timeout': 60,        # 60 seconds for fast models
            'long_timeout': 180,        # 3 minutes for reasoning models
            'max_retries': 3,           # Maximum retry attempts
            'backoff_base': 2,          # Exponential backoff base
            'batch_size': 1,            # Candidates per batch (configurable)
            'real_time_interval': 2,    # Seconds between real-time updates
        }
        
        # Load configuration from environment or file
        self._load_config()
        
        # Real-time processing tracking
        self.newly_processed = []   # Candidates processed since last UI update
        self.processing_lock = threading.Lock()
        
    def _load_config(self):
        """Load configuration from environment variables"""
        # Processing timeouts
        self.config['quick_timeout'] = int(os.getenv('RESUME_QUICK_TIMEOUT', self.config['quick_timeout']))
        self.config['long_timeout'] = int(os.getenv('RESUME_LONG_TIMEOUT', self.config['long_timeout']))
        self.config['max_retries'] = int(os.getenv('RESUME_MAX_RETRIES', self.config['max_retries']))
        
        # Check for model-specific timeout settings
        model_name = os.getenv('OPENAI_DEFAULT_MODEL', 'gpt-4o').lower()
        
        if 'o3' in model_name or 'reasoning' in model_name:
            self.config['default_timeout'] = self.config['long_timeout']
            logger.info(f"Detected reasoning model {model_name}, using long timeout: {self.config['long_timeout']}s")
        else:
            self.config['default_timeout'] = self.config['quick_timeout']
            logger.info(f"Using standard model {model_name}, using quick timeout: {self.config['quick_timeout']}s")
        
        # Batch processing configuration
        self.config['batch_size'] = int(os.getenv('RESUME_BATCH_SIZE', self.config['batch_size']))
        
        # Log the configuration
        if self.config['batch_size'] > 1:
            logger.info(f"Batch processing enabled: {self.config['batch_size']} resumes per batch")
        else:
            logger.info("Processing one resume at a time")
        
    def start_background_processing(self):
        """Start processing resumes in the background with real-time updates"""
        if self.is_processing:
            logger.info("Background processing already running")
            return
        
        logger.info("Starting background processing...")
        
        # Check if we have any resumes to process
        all_resumes = self.resume_parser.get_all_resumes(self.candidate_service.candidates_folder)
        logger.info(f"Found {len(all_resumes)} resume files in candidates folder")
        
        if len(all_resumes) == 0:
            logger.warning("No resume files found in candidates folder - nothing to process")
            self.status = "completed"
            return
            
        self.processing_thread = threading.Thread(target=self._process_all_resumes_enhanced)
        self.processing_thread.daemon = True
        self.is_processing = True
        self.status = "processing"
        
        # Clear previous state
        with self.processing_lock:
            self.newly_processed = []
            
        self.processing_thread.start()
        logger.info("Background processing thread started")
        
    def _process_all_resumes_enhanced(self):
        """Enhanced processing with real-time updates and smart retry logic"""
        try:
            customization_settings = self.candidate_service.customization_service.get_settings()
            
            # Get all resumes first for debugging
            all_resumes = self.resume_parser.get_all_resumes(self.candidate_service.candidates_folder)
            logger.info(f"Found {len(all_resumes)} total resume files")
            
            # Get all unprocessed resumes
            unprocessed_resumes = self._get_unprocessed_resumes()
            logger.info(f"Found {len(unprocessed_resumes)} unprocessed resumes")
            logger.info(f"Already processed: {len(self.candidate_service.summaries)} resumes")
            
            if not unprocessed_resumes:
                # Check retry queues
                retry_candidates = self._get_retry_candidates()
                logger.info(f"Found {len(retry_candidates)} candidates ready for retry")
                
                if not retry_candidates:
                    if len(all_resumes) == 0:
                        logger.warning("No resume files found in candidates folder")
                        self.status = "completed"
                    elif len(self.candidate_service.summaries) == len(all_resumes):
                        logger.info("All resumes already processed successfully")
                        self.status = "completed"
                    else:
                        logger.warning("No unprocessed resumes found, but not all resumes are processed. This might be a bug.")
                        self.status = "completed"
                    
                    self.is_processing = False
                    return
                unprocessed_resumes = retry_candidates
            
            self.total_count = len(unprocessed_resumes)
            self.processed_count = 0
            
            # Process resumes with real-time updates
            batch_size = self.config['batch_size']
            
            for i in range(0, len(unprocessed_resumes), batch_size):
                if not self.is_processing:
                    break
                    
                batch = unprocessed_resumes[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: {[r['name'] for r in batch]}")
                
                # Process batch with enhanced error handling
                self._process_batch_enhanced(batch, customization_settings)
                
                # Save progress and update UI
                self.candidate_service._save_data()
                
                # Small delay between batches
                time.sleep(0.5)
            
            # Process any remaining retries
            self._process_retry_queues(customization_settings)
            
            self.status = "completed"
            logger.info(f"Background processing completed. Processed {self.processed_count} out of {self.total_count} resumes successfully.")
            
        except Exception as e:
            logger.error(f"Enhanced background processing error: {e}")
            self.status = "error"
        finally:
            self.is_processing = False
    
    def _get_unprocessed_resumes(self):
        """Get resumes that haven't been processed yet"""
        resumes = self.resume_parser.get_all_resumes(self.candidate_service.candidates_folder)
        
        unprocessed_resumes = []
        processing_ids = [r['id'] for r in self.retry_queues['processing']]
        failed_ids = [r['id'] for r in self.retry_queues['failed']]
        
        for resume in resumes:
            resume_id = resume['id']
            
            # Check if already processed
            if resume_id in self.candidate_service.summaries:
                logger.debug(f"Resume {resume['filename']} already processed")
                continue
                
            # Check if currently in processing queue
            if resume_id in processing_ids:
                logger.debug(f"Resume {resume['filename']} currently being processed")
                continue
                
            # Check if in failed queue
            if resume_id in failed_ids:
                logger.debug(f"Resume {resume['filename']} in failed queue")
                continue
            
            # This resume needs processing
            logger.debug(f"Resume {resume['filename']} needs processing")
            unprocessed_resumes.append(resume)
        
        logger.info(f"Breakdown: {len(resumes)} total, {len(self.candidate_service.summaries)} processed, {len(processing_ids)} processing, {len(failed_ids)} failed, {len(unprocessed_resumes)} unprocessed")
        return unprocessed_resumes
    
    def _get_retry_candidates(self):
        """Get candidates ready for retry based on backoff timing"""
        retry_candidates = []
        current_time = datetime.now()
        
        # Check quick retry queue
        ready_quick = []
        for candidate in self.retry_queues['quick_retry']:
            candidate_id = candidate['id']
            last_retry = self.last_retry_time.get(candidate_id, datetime.min)
            retry_count = self.retry_counts.get(candidate_id, 0)
            
            # Exponential backoff: wait 2^retry_count minutes
            wait_time = timedelta(minutes=self.config['backoff_base'] ** retry_count)
            
            if current_time - last_retry >= wait_time:
                ready_quick.append(candidate)
                self.retry_queues['quick_retry'].remove(candidate)
        
        # Check long retry queue
        ready_long = []
        for candidate in self.retry_queues['long_retry']:
            candidate_id = candidate['id']
            last_retry = self.last_retry_time.get(candidate_id, datetime.min)
            retry_count = self.retry_counts.get(candidate_id, 0)
            
            # Longer backoff for reasoning model failures
            wait_time = timedelta(minutes=5 * (self.config['backoff_base'] ** retry_count))
            
            if current_time - last_retry >= wait_time:
                ready_long.append(candidate)
                self.retry_queues['long_retry'].remove(candidate)
        
        # Check format retry queue - shorter backoff since these are just formatting issues
        ready_format = []
        for candidate in self.retry_queues['format_retry']:
            candidate_id = candidate['id']
            last_retry = self.last_retry_time.get(candidate_id, datetime.min)
            retry_count = self.retry_counts.get(candidate_id, 0)
            
            # Shorter backoff for formatting failures (30 seconds to 2 minutes)
            wait_time = timedelta(seconds=30 * (self.config['backoff_base'] ** retry_count))
            
            if current_time - last_retry >= wait_time:
                ready_format.append(candidate)
                self.retry_queues['format_retry'].remove(candidate)
        
        return ready_quick + ready_long + ready_format
    
    def _process_batch_enhanced(self, batch, customization_settings):
        """Process a batch with enhanced error handling and real-time updates"""
        # Prepare resume data
        resumes_data = []
        failed_to_read = []
        
        for resume in batch:
            try:
                resume_text = self.resume_parser.parse_resume(resume['path'])
                resumes_data.append({
                    'id': resume['id'],
                    'name': resume['name'],
                    'text': resume_text,
                    'filename': resume['filename']
                })
                
                # Mark as currently processing
                self.retry_queues['processing'].append(resume)
                
            except Exception as e:
                logger.error(f"Error reading resume {resume['filename']}: {e}")
                failed_to_read.append(resume)
                self._handle_processing_error(resume, e, 'file_read_error')
        
        if not resumes_data:
            return
        
        # Process with timeout based on model type
        timeout = self._get_timeout_for_batch(resumes_data)
        
        try:
            # Process the batch with timeout
            results = self._process_with_timeout(resumes_data, customization_settings, timeout)
            
            # Handle successful results
            for candidate_id, summary in results.items():
                if self._is_valid_summary(summary):
                    self.candidate_service.summaries[candidate_id] = summary
                    self.processed_count += 1
                    
                    # Add to real-time updates
                    with self.processing_lock:
                        self.newly_processed.append(candidate_id)
                    
                    # Remove from processing queue
                    self.retry_queues['processing'] = [
                        r for r in self.retry_queues['processing'] if r['id'] != candidate_id
                    ]
                    
                    logger.info(f"✅ {candidate_id}: Successfully processed")
                else:
                    # Invalid result - detect failure type
                    failure_type = self._detect_failure_type(summary)
                    resume = next(r for r in batch if r['id'] == candidate_id)
                    
                    if failure_type == 'formatting_failure':
                        # Store the problematic response for retry with better formatting
                        resume['_last_response'] = summary
                        logger.warning(f"🔧 {candidate_id}: Formatting failure detected - will retry with enhanced formatting")
                    
                    self._handle_processing_error(resume, f"Invalid summary structure: {failure_type}", failure_type)
            
        except TimeoutError as e:
            # Handle timeout - move to appropriate retry queue
            for resume_data in resumes_data:
                resume = next(r for r in batch if r['id'] == resume_data['id'])
                self._handle_processing_error(resume, e, 'timeout')
                
        except Exception as e:
            # Handle other processing errors
            for resume_data in resumes_data:
                resume = next(r for r in batch if r['id'] == resume_data['id'])
                self._handle_processing_error(resume, e, 'processing_error')
    
    def _get_timeout_for_batch(self, resumes_data):
        """Determine appropriate timeout based on batch size and model"""
        base_timeout = self.config['default_timeout']
        batch_size = len(resumes_data)
        
        # Adjust timeout based on batch size
        if batch_size == 1:
            # Single resume processing - can use shorter timeout for faster feedback
            timeout = base_timeout
        else:
            # Batch processing - scale timeout with batch size
            timeout = base_timeout * max(1, batch_size * 0.7)  # ~70% scaling factor
        
        # Adjust timeout based on resume length
        total_length = sum(len(r['text']) for r in resumes_data)
        avg_length = total_length / batch_size if batch_size > 0 else 0
        
        # Increase timeout for longer resumes
        if avg_length > 10000:  # Very long resumes
            timeout = int(timeout * 1.5)
        elif avg_length > 5000:  # Long resumes
            timeout = int(timeout * 1.2)
        
        return int(timeout)
    
    def _process_with_timeout(self, resumes_data, customization_settings, timeout):
        """Process batch with specified timeout using threading approach"""
        import threading
        import queue
        
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def worker():
            try:
                results = self.batch_processor.process_batch(
                    resumes_data, customization_settings, len(resumes_data)
                )
                result_queue.put(results)
            except Exception as e:
                exception_queue.put(e)
        
        # Start the worker thread
        worker_thread = threading.Thread(target=worker)
        worker_thread.daemon = True
        worker_thread.start()
        
        # Wait for completion or timeout
        worker_thread.join(timeout=timeout)
        
        if worker_thread.is_alive():
            # Timeout occurred - the worker thread will continue running in background
            # but we'll move on and treat this as a timeout error
            logger.warning(f"Processing timed out after {timeout} seconds for batch of {len(resumes_data)} resumes")
            raise TimeoutError(f"Processing exceeded {timeout} seconds")
        
        # Check for exceptions
        if not exception_queue.empty():
            raise exception_queue.get()
        
        # Get the result
        if not result_queue.empty():
            return result_queue.get()
        else:
            raise Exception("Worker thread completed but no result was returned")
    
    def _is_valid_summary(self, summary):
        """Validate that the summary has required fields and is not a formatting failure"""
        if not isinstance(summary, dict):
            return False
            
        required_keys = ['nickname', 'summary', 'reservations', 'relevant_achievements', 'wildcard']
        has_required_keys = all(key in summary for key in required_keys)
        
        if not has_required_keys:
            return False
        
        # Check for formatting failure marker
        if summary.get('_formatting_failure', False):
            return False
            
        # Additional quality checks
        # Check for generic fallback content that indicates poor processing
        if summary.get('nickname') in ['Review Pending', 'Processing Error', 'Formatting Issue']:
            return False
            
        # Check if summary contains error indicators
        summary_text = summary.get('summary', '')
        if any(phrase in summary_text.lower() for phrase in [
            'error occurred',
            'processing issues',
            'manual review due to',
            'format was invalid'
        ]):
            return False
            
        return True
    
    def _detect_failure_type(self, summary):
        """Detect if this is a formatting failure vs other types of failures"""
        if not isinstance(summary, dict):
            return 'invalid_result'
            
        # Check for explicit formatting failure marker
        if summary.get('_formatting_failure', False):
            return 'formatting_failure'
            
        # Check for formatting-related indicators
        nickname = summary.get('nickname', '')
        summary_text = summary.get('summary', '')
        
        formatting_indicators = [
            'formatting issue',
            'format was invalid',
            'json parsing failed',
            'response format',
            'quality issues'
        ]
        
        if any(indicator in nickname.lower() for indicator in formatting_indicators):
            return 'formatting_failure'
            
        if any(indicator in summary_text.lower() for indicator in formatting_indicators):
            return 'formatting_failure'
            
        # Default to invalid result for other quality issues
        return 'invalid_result'
    
    def _handle_processing_error(self, resume, error, error_type):
        """Handle processing errors with smart retry logic"""
        candidate_id = resume['id']
        retry_count = self.retry_counts.get(candidate_id, 0)
        
        # Remove from processing queue
        self.retry_queues['processing'] = [
            r for r in self.retry_queues['processing'] if r['id'] != candidate_id
        ]
        
        logger.warning(f"⚠️ Processing error for {resume['filename']}: {error} (attempt {retry_count + 1})")
        
        if retry_count >= self.config['max_retries']:
            # Max retries reached, move to failed
            self.retry_queues['failed'].append({
                **resume,
                'error': str(error),
                'error_type': error_type,
                'retry_count': retry_count,
                'failed_at': datetime.now().isoformat()
            })
            logger.error(f"❌ {candidate_id}: Max retries reached, moved to failed queue")
        else:
            # Determine retry queue based on error type
            if error_type == 'timeout':
                self.retry_queues['long_retry'].append(resume)
                logger.info(f"🔄 {candidate_id}: Added to long retry queue (timeout)")
            elif error_type in ['formatting_failure', 'invalid_result']:
                self.retry_queues['format_retry'].append(resume)
                logger.info(f"🔄 {candidate_id}: Added to format retry queue ({error_type})")
            else:
                self.retry_queues['quick_retry'].append(resume)
                logger.info(f"🔄 {candidate_id}: Added to quick retry queue ({error_type})")
            
            # Update retry tracking
            self.retry_counts[candidate_id] = retry_count + 1
            self.last_retry_time[candidate_id] = datetime.now()
    
    def _process_retry_queues(self, customization_settings):
        """Process any remaining items in retry queues"""
        retry_candidates = self._get_retry_candidates()
        
        if retry_candidates:
            logger.info(f"Processing {len(retry_candidates)} retry candidates")
            
            for candidate in retry_candidates:
                if not self.is_processing:
                    break
                    
                self._process_batch_enhanced([candidate], customization_settings)
                time.sleep(1)  # Brief pause between retries
    
    def get_status(self) -> Dict:
        """Get enhanced processing status including retry queue information"""
        with self.processing_lock:
            newly_processed_count = len(self.newly_processed)
        
        return {
            "is_processing": self.is_processing,
            "status": self.status,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "progress": (self.processed_count / self.total_count * 100) if self.total_count > 0 else 0,
            "newly_processed_count": newly_processed_count,
            "retry_queues": {
                "quick_retry": len(self.retry_queues['quick_retry']),
                "long_retry": len(self.retry_queues['long_retry']),
                "format_retry": len(self.retry_queues['format_retry']),
                "failed": len(self.retry_queues['failed']),
                "processing": len(self.retry_queues['processing'])
            },
            "config": self.config
        }
    
    def get_newly_processed_candidates(self) -> List[str]:
        """Get and clear the list of newly processed candidate IDs"""
        with self.processing_lock:
            newly_processed = self.newly_processed.copy()
            self.newly_processed = []
            return newly_processed
    
    def get_failed_candidates(self) -> List[Dict]:
        """Get candidates that failed after max retries"""
        return self.retry_queues['failed'].copy()
    
    def retry_failed_candidate(self, candidate_id: str) -> bool:
        """Manually retry a failed candidate"""
        failed_candidate = None
        for candidate in self.retry_queues['failed']:
            if candidate['id'] == candidate_id:
                failed_candidate = candidate
                break
        
        if failed_candidate:
            # Reset retry count and move to quick retry
            self.retry_counts[candidate_id] = 0
            self.retry_queues['failed'].remove(failed_candidate)
            self.retry_queues['quick_retry'].append(failed_candidate)
            logger.info(f"🔄 Manually retrying {candidate_id}")
            return True
        
        return False
    
    def force_process_batch(self, candidate_ids: List[str]) -> Dict[str, Dict]:
        """Force process specific candidates immediately with long timeout"""
        customization_settings = self.candidate_service.customization_service.get_settings()
        resumes = self.resume_parser.get_all_resumes(self.candidate_service.candidates_folder)
        
        target_resumes = [r for r in resumes if r['id'] in candidate_ids]
        
        if not target_resumes:
            return {}
        
        # Use long timeout for forced processing
        original_timeout = self.config['default_timeout']
        self.config['default_timeout'] = self.config['long_timeout']
        
        try:
            self._process_batch_enhanced(target_resumes, customization_settings)
            
            # Return results for the requested candidates
            results = {}
            for candidate_id in candidate_ids:
                if candidate_id in self.candidate_service.summaries:
                    results[candidate_id] = self.candidate_service.summaries[candidate_id]
            
            return results
            
        finally:
            # Restore original timeout
            self.config['default_timeout'] = original_timeout
    
    def stop_processing(self):
        """Stop background processing"""
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=10)
        logger.info("Background processing stopped") 