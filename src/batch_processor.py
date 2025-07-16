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
        
        CRITICAL INSTRUCTIONS:
        1. DO NOT use generic phrases like "seasoned expert", "proven track record", "perfect fit", "strong background", or any statement that could apply to more than 30% of applicants
        2. CITE EVIDENCE: For EVERY claim you make, include the EXACT VERBATIM quote from the resume that supports it. Do NOT paraphrase, summarize, or infer - copy the exact words.
        3. START WITH DIFFERENTIATORS: Begin by identifying what makes each candidate DIFFERENT from typical applicants
        4. If you cannot find a direct quote to support a claim, do NOT make that claim
        5. SUBSTANTIVE ACHIEVEMENTS: Focus on achievements with concrete numbers, measurable impact, or significant scope (team size, budget, users affected, percentage improvements, etc.)
        6. WORK HISTORY: Extract ALL work experiences from the resume (up to 5 maximum). Do NOT arbitrarily limit to 2-3 jobs when more are available.
        
        Return a JSON array, with each object containing these exact keys:
        
        - "differentiators": An array of 3 things that make this candidate UNIQUE compared to typical applicants for this role. Each item should be an object with:
          - "claim": The unique aspect (be specific, not generic, and CONCISE - avoid filler words like "effectively", "successfully", "efficiently")
          - "evidence": The EXACT VERBATIM quote from the resume (copy word-for-word, no paraphrasing)
        
        - "nickname": A 2-3 word nickname based on their UNIQUE profile (e.g., "Quantum Researcher", "Startup Veteran", "Patent Holder"). NO generic terms like "Tech Expert"
        
        - "summary": A brief 1-2 line summary focusing on SPECIFIC experiences and achievements, not generic qualities
        
        - "reservations": An array of 2-3 SPECIFIC concerns or gaps for this specific role (focus on what's missing or lacking, no evidence quotes needed for gaps)
        
        - "relevant_achievements": An array of exactly 4 SUBSTANTIVE, QUANTIFIED achievements that directly relate to this role. Each should be an object with:
          - "achievement": A specific, impactful accomplishment with numbers/metrics that shows capability for this role
          - "evidence": The EXACT VERBATIM quote from resume (copy word-for-word)
        
        - "wildcard": An object with:
          - "fact": A unique, interesting aspect that likely wouldn't appear in other resumes
          - "evidence": The EXACT VERBATIM quote supporting this (copy word-for-word)
        
        - "work_history": An array of work experiences. IMPORTANT: Extract ALL available work experiences from the resume, up to a maximum of 5. If the resume shows 5+ jobs, include all 5. If it shows 4 jobs, include all 4. Do NOT limit to just 2-3 entries. Each should be an object with "title", "company", and "years". Order from most recent to oldest.
        
        - "experience_distribution": An object with years in different sectors: {{"corporate": X, "startup": Y, "nonprofit": Z, "government": W, "education": V, "other": U}}

        Job Description:
        {job_description if job_description else "Not provided."}

        Resumes to analyze:
        """
        
        for i, resume_data in enumerate(resumes_data):
            batch_prompt += f"\n\nRESUME {i+1} (ID: {resume_data['id']}):\n"
            batch_prompt += f"Content: {resume_data['text'][:8000]}...\n"  # Increased for full resume content
            batch_prompt += "---"
        
        return batch_prompt
    
    def process_single_resume(self, resume_data: Dict, customization_settings: Dict) -> Dict:
        """Process a single resume (fallback method)"""
        job_description = customization_settings.get('job_description', '')

        prompt = f"""
        Analyze this resume based on the job description below.
        
        CRITICAL INSTRUCTIONS:
        1. DO NOT use generic phrases like "seasoned expert", "proven track record", "perfect fit", "strong background", or any statement that could apply to more than 30% of applicants
        2. CITE EVIDENCE: For EVERY claim you make, include the EXACT VERBATIM quote from the resume that supports it. Do NOT paraphrase, summarize, or infer - copy the exact words.
        3. START WITH DIFFERENTIATORS: Begin by identifying what makes this candidate DIFFERENT from typical applicants
        4. If you cannot find a direct quote to support a claim, do NOT make that claim
        5. SUBSTANTIVE ACHIEVEMENTS: Focus on achievements with concrete numbers, measurable impact, or significant scope (team size, budget, users affected, percentage improvements, etc.)
        6. WORK HISTORY: Extract ALL work experiences from the resume (up to 5 maximum). Do NOT arbitrarily limit to 2-3 jobs when more are available.
        
        Return a JSON object with these exact keys:
        
        - "differentiators": An array of 3 things that make this candidate UNIQUE compared to typical applicants for this role. Each item should be an object with:
          - "claim": The unique aspect (be specific, not generic, and CONCISE - avoid filler words like "effectively", "successfully", "efficiently")
          - "evidence": The EXACT VERBATIM quote from the resume (copy word-for-word, no paraphrasing)
        
        - "nickname": A 2-3 word nickname based on their UNIQUE profile (e.g., "Quantum Researcher", "Startup Veteran", "Patent Holder"). NO generic terms like "Tech Expert"
        
        - "summary": A brief 2-3 line summary focusing on SPECIFIC experiences and achievements, not generic qualities
        
        - "reservations": An array of 2-3 SPECIFIC concerns or gaps for this specific role (focus on what's missing or lacking, no evidence quotes needed for gaps)
        
        - "relevant_achievements": An array of exactly 4 SUBSTANTIVE, QUANTIFIED achievements that directly relate to this role. Each should be an object with:
          - "achievement": A specific, impactful accomplishment with numbers/metrics that shows capability for this role
          - "evidence": The EXACT VERBATIM quote from resume (copy word-for-word)
        
        - "wildcard": An object with:
          - "fact": A unique, interesting aspect that likely wouldn't appear in other resumes
          - "evidence": The EXACT VERBATIM quote supporting this (copy word-for-word)
        
        - "work_history": An array of work experiences. IMPORTANT: Extract ALL available work experiences from the resume, up to a maximum of 5. If the resume shows 5+ jobs, include all 5. If it shows 4 jobs, include all 4. Do NOT limit to just 2-3 entries. Each should be an object with "title", "company", and "years". Order from most recent to oldest.
        
        - "experience_distribution": An object with years in different sectors: {{"corporate": X, "startup": Y, "nonprofit": Z, "government": W, "education": V, "other": U}}

        Job Description:
        {job_description if job_description else "Not provided."}
        
        Resume to analyze:
        {resume_data['text'][:12000]}...
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
                
                # Ensure all required fields are present with proper structure
                if 'differentiators' not in result:
                    result['differentiators'] = []
                if 'nickname' not in result:
                    result['nickname'] = 'Anonymous Pro'
                if 'wildcard' not in result or not isinstance(result['wildcard'], dict):
                    result['wildcard'] = {"fact": "Unique profile details pending analysis", "evidence": ""}
                if 'experience_distribution' not in result:
                    result['experience_distribution'] = {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
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
            "relevant_achievements": ["Manual review needed"],
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
            "relevant_achievements": ["Error in processing"],
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