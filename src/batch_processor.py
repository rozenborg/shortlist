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
        
        batch_prompt = f"""
        Analyze the resumes below based on the following job description.
        
        IMPORTANT: 
        1. Generate a 2-3 word nickname for each candidate based on their profile (e.g., "Data Wizard", "Marketing Guru", "Full Stack Pro"). DO NOT use real names or any gender-specific terms.
        2. Never reference gender in any part of your analysis.
        
        Return a JSON array, with each object containing these exact keys:
        - "nickname": A 2-3 word nickname based on their profile (no real names, no gender terms)
        - "summary": A concise summary of the candidate's background and experience
        - "reservations": An array of 2-3 potential concerns or gaps for this specific role
        - "fit_indicators": An array of 3-4 reasons why they might be a good fit for this role
        - "achievements": An array of 3-5 notable achievements from their career
        - "wildcard": A unique, interesting aspect about this candidate that stands out and likely wouldn't appear in many other resumes (e.g., unusual hobby, unique background, interesting side project, uncommon skill combination)
        - "work_history": An array of the candidate's last 5 work experiences, each as an object with "title" (job title), "company" (company name), and "years" (approximate years worked there, e.g., "2020-2023" or "2019-Present"). Order from most recent to oldest.
        - "experience_distribution": An object with years of experience in different sectors: {{"corporate": X, "startup": Y, "nonprofit": Z, "government": W, "education": V, "other": U}} where each value is years (can be 0)

        Job Description:
        {job_description if job_description else "Not provided."}

        Resumes to analyze:
        """
        
        for i, resume_data in enumerate(resumes_data):
            batch_prompt += f"\n\nRESUME {i+1} (ID: {resume_data['id']}):\n"
            batch_prompt += f"Content: {resume_data['text'][:2000]}...\n"  # Limit text length
            batch_prompt += "---"
        
        return batch_prompt
    
    def process_single_resume(self, resume_data: Dict, customization_settings: Dict) -> Dict:
        """Process a single resume (fallback method)"""
        job_description = customization_settings.get('job_description', '')

        prompt = f"""
        Analyze this resume based on the job description below.
        
        IMPORTANT: 
        1. Generate a 2-3 word nickname for this candidate based on their profile (e.g., "Data Wizard", "Marketing Guru", "Full Stack Pro"). DO NOT use real names or any gender-specific terms.
        2. Never reference gender in any part of your analysis.
        
        Return a JSON object with these exact keys:
        - "nickname": A 2-3 word nickname based on their profile (no real names, no gender terms)
        - "summary": A concise summary of the candidate's background and experience
        - "reservations": An array of 2-3 potential concerns or gaps for this specific role
        - "fit_indicators": An array of 3-4 reasons why they might be a good fit for this role
        - "achievements": An array of 3-5 notable achievements from their career
        - "wildcard": A unique, interesting aspect about this candidate that stands out and likely wouldn't appear in many other resumes (e.g., unusual hobby, unique background, interesting side project, uncommon skill combination)
        - "work_history": An array of the candidate's last 5 work experiences, each as an object with "title" (job title), "company" (company name), and "years" (approximate years worked there, e.g., "2020-2023" or "2019-Present"). Order from most recent to oldest.
        - "experience_distribution": An object with years of experience in different sectors: {{"corporate": X, "startup": Y, "nonprofit": Z, "government": W, "education": V, "other": U}} where each value is years (can be 0)

        Job Description:
        {job_description if job_description else "Not provided."}
        
        Resume to analyze:
        {resume_data['text'][:3000]}...
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
                
                result = json.loads(clean_response.strip())
                # Ensure wildcard is present
                if 'wildcard' not in result:
                    result['wildcard'] = 'Unique profile details pending analysis'
                # Ensure work_history is present
                if 'work_history' not in result:
                    result['work_history'] = []
                return result
            except json.JSONDecodeError:
                # Fallback parsing
                return self._parse_fallback_response(response)
        except Exception as e:
            print(f"Error processing resume for {resume_data['name']}: {e}")
            return self._create_error_response()
    
    def _parse_fallback_response(self, response: str) -> Dict:
        """Parse non-JSON response as fallback"""
        return {
            "nickname": "Review Pending",
            "summary": response[:200] + "...",
            "reservations": ["Unable to analyze automatically"],
            "fit_indicators": ["Automated analysis incomplete"],
            "achievements": ["Manual review needed"],
            "wildcard": "Manual review needed",
            "work_history": [],
            "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
        }
    
    def _create_error_response(self) -> Dict:
        """Create error response"""
        return {
            "nickname": "Error Processing",
            "summary": "Error processing resume",
            "reservations": ["Processing error occurred"],
            "fit_indicators": ["Processing error occurred"],
            "achievements": ["Error in processing"],
            "wildcard": "Error in processing",
            "work_history": [],
            "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
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
                                # Ensure wildcard is present
                                if 'wildcard' not in result:
                                    result['wildcard'] = 'Unique profile details pending analysis'
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