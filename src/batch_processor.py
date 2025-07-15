import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

class BatchProcessor:
    def __init__(self, llm_service, max_workers=5):
        self.llm_service = llm_service
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def create_batch_prompt(self, resumes_data: List[Dict], customization_settings: Dict) -> str:
        """Create a single prompt for multiple resumes"""
        job_description = customization_settings.get('job_description', '')
        instructions = customization_settings.get('instructions', '')
        
        batch_prompt = f"""
        Analyze the resumes below based on the following job description and instructions.
        Return a JSON array, with each object containing keys: "summary", "skills", "experience_level", "achievements", "fit_score", and "fit_reasoning".

        Job Description:
        {job_description if job_description else "Not provided."}

        Your summary for each candidate should follow these instructions:
        ---
        {instructions if instructions else "Provide a general summary highlighting key qualifications."}
        ---

        Resumes to analyze:
        """
        
        for i, resume_data in enumerate(resumes_data):
            batch_prompt += f"\n\nRESUME {i+1} (ID: {resume_data['id']}):\n"
            batch_prompt += f"Candidate: {resume_data['name']}\n"
            batch_prompt += f"Content: {resume_data['text'][:2000]}...\n"  # Limit text length
            batch_prompt += "---"
        
        return batch_prompt
    
    def process_single_resume(self, resume_data: Dict, customization_settings: Dict) -> Dict:
        """Process a single resume (fallback method)"""
        job_description = customization_settings.get('job_description', '')
        instructions = customization_settings.get('instructions', '')

        prompt = f"""
        Analyze the resume for {resume_data['name']} based on the job description below.
        Return a JSON object with keys: "summary", "skills", "experience_level", "achievements", "fit_score", and "fit_reasoning".

        Job Description:
        {job_description if job_description else "Not provided."}

        Your summary should follow these instructions:
        ---
        {instructions if instructions else "Provide a general summary highlighting key qualifications."}
        ---
        """
        
        try:
            response = self.llm_service.chat(prompt)
            # Try to parse JSON response
            try:
                # Remove markdown code blocks if present
                clean_response = response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]
                if clean_response.startswith('```'):
                    clean_response = clean_response[3:]
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]
                
                return json.loads(clean_response.strip())
            except json.JSONDecodeError:
                # Fallback parsing
                return self._parse_fallback_response(response)
        except Exception as e:
            print(f"Error processing resume for {resume_data['name']}: {e}")
            return self._create_error_response()
    
    def _parse_fallback_response(self, response: str) -> Dict:
        """Parse non-JSON response as fallback"""
        return {
            "summary": response[:200] + "...",
            "skills": ["Analysis pending"],
            "experience_level": "To be determined",
            "achievements": ["Manual review needed"],
            "fit_score": 5,
            "fit_reasoning": "Automated analysis incomplete"
        }
    
    def _create_error_response(self) -> Dict:
        """Create error response"""
        return {
            "summary": "Error processing resume",
            "skills": ["Error"],
            "experience_level": "Unknown",
            "achievements": ["Error in processing"],
            "fit_score": 0,
            "fit_reasoning": "Processing error occurred"
        }
    
    def process_batch(self, resumes_data: List[Dict], customization_settings: Dict, batch_size: int = 3) -> Dict[str, Dict]:
        """Process resumes in batches"""
        results = {}
        
        # Process in smaller batches to avoid token limits
        for i in range(0, len(resumes_data), batch_size):
            batch = resumes_data[i:i + batch_size]
            
            if len(batch) == 1:
                # Single resume - process directly
                result = self.process_single_resume(batch[0], customization_settings)
                results[batch[0]['id']] = result
            else:
                # Batch processing
                try:
                    batch_prompt = self.create_batch_prompt(batch, customization_settings)
                    response = self.llm_service.chat(batch_prompt)
                    
                    # Parse batch response
                    try:
                        # Remove markdown code blocks if present
                        clean_response = response.strip()
                        if clean_response.startswith('```json'):
                            clean_response = clean_response[7:]
                        if clean_response.startswith('```'):
                            clean_response = clean_response[3:]
                        if clean_response.endswith('```'):
                            clean_response = clean_response[:-3]
                        
                        batch_results = json.loads(clean_response.strip())
                        
                        # Map results back to candidate IDs
                        for j, result in enumerate(batch_results):
                            if j < len(batch):
                                candidate_id = batch[j]['id']
                                # Remove candidate_id from result if it exists
                                if 'candidate_id' in result:
                                    del result['candidate_id']
                                results[candidate_id] = result
                    except json.JSONDecodeError:
                        # Fallback to individual processing
                        for resume_data in batch:
                            result = self.process_single_resume(resume_data, customization_settings)
                            results[resume_data['id']] = result
                            
                except Exception as e:
                    print(f"Batch processing error: {e}")
                    # Fallback to individual processing
                    for resume_data in batch:
                        result = self.process_single_resume(resume_data, customization_settings)
                        results[resume_data['id']] = result
        
        return results
    
    async def process_batch_async(self, resumes_data: List[Dict], customization_settings: Dict) -> Dict[str, Dict]:
        """Process resumes asynchronously"""
        loop = asyncio.get_event_loop()
        
        # Split into smaller batches for parallel processing
        batch_size = 2  # Smaller batches for better parallelization
        batches = [resumes_data[i:i + batch_size] for i in range(0, len(resumes_data), batch_size)]
        
        # Process batches concurrently
        tasks = []
        for batch in batches:
            task = loop.run_in_executor(self.executor, self.process_batch, batch, customization_settings, len(batch))
            tasks.append(task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks)
        
        # Combine results
        combined_results = {}
        for batch_result in batch_results:
            combined_results.update(batch_result)
        
        return combined_results
    
    def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True) 