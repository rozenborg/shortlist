import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import re # Added for regex-based JSON cleaning

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
        
        🚨 CRITICAL ANONYMITY REQUIREMENTS 🚨
        - NEVER mention the candidate's real name, first name, last name, or any personal identifiers
        - NEVER use pronouns that reveal gender (he/him, she/her) - use "they/them" or avoid pronouns entirely
        - NEVER start summaries with names like "John is..." or "Sarah has..." 
        - Use role-based descriptions: "This candidate...", "The applicant...", "This professional..."
        - Keep the focus on skills, experience, and achievements - NOT personal identity
        - Examples of GOOD openings: "Experienced software engineer with...", "Seasoned marketing professional who...", "Technical leader specializing in..."
        - Examples of BAD openings: "John is a software engineer...", "Sarah brings 5 years...", "Michael has experience..."
        
        ⚠️  CRITICAL JSON FORMATTING REQUIREMENTS ⚠️
        - You MUST return ONLY a valid JSON array
        - Do NOT include any text before or after the JSON
        - Do NOT wrap in markdown code blocks (no ```json or ```)
        - Do NOT include any explanatory text
        - Ensure all strings are properly escaped with double quotes
        - Ensure all arrays and objects have proper comma separation
        - Test your JSON mentally before responding to ensure it's valid
        
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
        
        - "experience_distribution": An object with years in different sectors: {{"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}}

        EXAMPLE JSON STRUCTURE (adapt to actual resume content):
        [
          {{
            "differentiators": [
              {{"claim": "Holder of 15 AI patents", "evidence": "Invented and patented 15 machine learning algorithms"}},
              {{"claim": "Led 200-person engineering org", "evidence": "VP Engineering managing 200+ engineers across 12 teams"}},
              {{"claim": "Scaled systems to 50M users", "evidence": "Architected platform serving 50 million daily active users"}}
            ],
            "nickname": "AI Patent Holder",
            "summary": "VP Engineering with 15 AI patents who scaled platforms to 50M users and managed 200+ person teams.",
            "reservations": ["No direct fintech experience", "May be overqualified for IC role"],
            "relevant_achievements": [
              {{"achievement": "Reduced infrastructure costs by 40%", "evidence": "Led cloud migration saving $2M annually"}},
              {{"achievement": "Improved system uptime to 99.9%", "evidence": "Achieved 99.9% uptime across all services"}},
              {{"achievement": "Launched product used by 10M users", "evidence": "Shipped recommendation engine to 10M+ users"}},
              {{"achievement": "Built team from 20 to 200 engineers", "evidence": "Grew engineering org from 20 to 200 in 2 years"}}
            ],
            "wildcard": {{"fact": "Published research in Nature", "evidence": "Co-authored paper on quantum computing in Nature journal"}},
            "work_history": [
              {{"title": "VP Engineering", "company": "TechCorp", "years": "2020-2024"}},
              {{"title": "Senior Director", "company": "StartupXYZ", "years": "2018-2020"}},
              {{"title": "Engineering Manager", "company": "BigTech", "years": "2015-2018"}}
            ],
            "experience_distribution": {{"corporate": 6, "startup": 3, "nonprofit": 0, "government": 0, "education": 0, "other": 0}}
          }}
        ]

        Job Description:
        {job_description if job_description else "Not provided."}

        Resumes to analyze:
        """
        
        for i, resume_data in enumerate(resumes_data):
            batch_prompt += f"\n\nRESUME {i+1} (ID: {resume_data['id']}):\n"
            batch_prompt += f"Content: {resume_data['text'][:8000]}...\n"  # Increased for full resume content
            batch_prompt += "---"
        
        batch_prompt += "\n\nRemember: Return ONLY the JSON array, no other text. Ensure valid JSON syntax."
        
        return batch_prompt
    
    def process_single_resume(self, resume_data: Dict, customization_settings: Dict) -> Dict:
        """Process a single resume (fallback method)"""
        job_description = customization_settings.get('job_description', '')
        
        # Check if this is a formatting retry
        is_formatting_retry = '_last_response' in resume_data
        
        if is_formatting_retry:
            # Use enhanced formatting instructions for retry
            return self._process_with_enhanced_formatting(resume_data, customization_settings)
        
        # Regular processing
        prompt = f"""
        Analyze this resume based on the job description below.
        
        CRITICAL INSTRUCTIONS:
        1. DO NOT use generic phrases like "seasoned expert", "proven track record", "perfect fit", "strong background", or any statement that could apply to more than 30% of applicants
        2. CITE EVIDENCE: For EVERY claim you make, include the EXACT VERBATIM quote from the resume that supports it. Do NOT paraphrase, summarize, or infer - copy the exact words.
        3. START WITH DIFFERENTIATORS: Begin by identifying what makes this candidate DIFFERENT from typical applicants
        4. If you cannot find a direct quote to support a claim, do NOT make that claim
        5. SUBSTANTIVE ACHIEVEMENTS: Focus on achievements with concrete numbers, measurable impact, or significant scope (team size, budget, users affected, percentage improvements, etc.)
        6. WORK HISTORY: Extract ALL work experiences from the resume (up to 5 maximum). Do NOT arbitrarily limit to 2-3 jobs when more are available.
        
        🚨 CRITICAL ANONYMITY REQUIREMENTS 🚨
        - NEVER mention the candidate's real name, first name, last name, or any personal identifiers
        - NEVER use pronouns that reveal gender (he/him, she/her) - use "they/them" or avoid pronouns entirely
        - NEVER start summaries with names like "John is..." or "Sarah has..." 
        - Use role-based descriptions: "This candidate...", "The applicant...", "This professional..."
        - Keep the focus on skills, experience, and achievements - NOT personal identity
        - Examples of GOOD openings: "Experienced software engineer with...", "Seasoned marketing professional who...", "Technical leader specializing in..."
        - Examples of BAD openings: "John is a software engineer...", "Sarah brings 5 years...", "Michael has experience..."
        
        ⚠️  CRITICAL JSON FORMATTING REQUIREMENTS ⚠️
        - You MUST return ONLY a valid JSON object
        - Do NOT include any text before or after the JSON
        - Do NOT wrap in markdown code blocks (no ```json or ```)
        - Do NOT include any explanatory text
        - Ensure all strings are properly escaped with double quotes
        - Ensure all arrays and objects have proper comma separation
        - Test your JSON mentally before responding to ensure it's valid
        
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
        
        - "experience_distribution": An object with years in different sectors: {{"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}}

        EXAMPLE JSON STRUCTURE (adapt to actual resume content):
        {{
          "differentiators": [
            {{"claim": "Holder of 15 AI patents", "evidence": "Invented and patented 15 machine learning algorithms"}},
            {{"claim": "Led 200-person engineering org", "evidence": "VP Engineering managing 200+ engineers across 12 teams"}},
            {{"claim": "Scaled systems to 50M users", "evidence": "Architected platform serving 50 million daily active users"}}
          ],
          "nickname": "AI Patent Holder",
          "summary": "VP Engineering with 15 AI patents who scaled platforms to 50M users and managed 200+ person teams.",
          "reservations": ["No direct fintech experience", "May be overqualified for IC role"],
          "relevant_achievements": [
            {{"achievement": "Reduced infrastructure costs by 40%", "evidence": "Led cloud migration saving $2M annually"}},
            {{"achievement": "Improved system uptime to 99.9%", "evidence": "Achieved 99.9% uptime across all services"}},
            {{"achievement": "Launched product used by 10M users", "evidence": "Shipped recommendation engine to 10M+ users"}},
            {{"achievement": "Built team from 20 to 200 engineers", "evidence": "Grew engineering org from 20 to 200 in 2 years"}}
          ],
          "wildcard": {{"fact": "Published research in Nature", "evidence": "Co-authored paper on quantum computing in Nature journal"}},
          "work_history": [
            {{"title": "VP Engineering", "company": "TechCorp", "years": "2020-2024"}},
            {{"title": "Senior Director", "company": "StartupXYZ", "years": "2018-2020"}},
            {{"title": "Engineering Manager", "company": "BigTech", "years": "2015-2018"}}
          ],
          "experience_distribution": {{"corporate": 6, "startup": 3, "nonprofit": 0, "government": 0, "education": 0, "other": 0}}
        }}

        Job Description:
        {job_description if job_description else "Not provided."}
        
        Resume to analyze:
        {resume_data['text'][:12000]}...
        
        Remember: Return ONLY the JSON object, no other text. Ensure valid JSON syntax.
        """
        
        try:
            response = self.llm_service.chat(prompt)
            
            # Track API success but potential formatting failure
            api_success = True
            raw_response = response
            
            # Try to parse JSON response
            try:
                # Enhanced JSON cleaning and parsing
                result = self._parse_json_response(response)
                
                # Ensure all required fields are present with proper structure
                result = self._validate_and_fix_result_structure(result)
                
                # NEW: Scrub any names that slipped through
                result = self._scrub_personal_identifiers(result, resume_data)
                
                # NEW: Check if this is a quality response or just fallback data
                response_quality = self._assess_response_quality(result, resume_data, raw_response)
                
                if response_quality['is_low_quality']:
                    print(f"⚠️ Low quality response detected for {resume_data.get('name', 'unknown')}: {response_quality['reason']}")
                    
                    # This is a formatting failure, not an API failure
                    return self._create_formatting_failure_response(resume_data, raw_response, response_quality)
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed for {resume_data.get('name', 'unknown')}: {e}")
                print(f"Raw response preview: {response[:300]}...")
                
                # Try one retry with explicit JSON formatting instructions
                retry_result = self._retry_with_json_focus(resume_data, customization_settings, response)
                if retry_result:
                    return retry_result
                
                # This is a formatting failure, not an API failure
                return self._create_formatting_failure_response(resume_data, response, {
                    'is_low_quality': True,
                    'reason': 'JSON parsing failed',
                    'details': str(e)
                })
                
        except Exception as e:
            # This is likely an API failure (connection, timeout, etc.)
            print(f"LLM API error processing resume for {resume_data['name']}: {e}")
            return self._create_error_response()
    
    def _process_with_enhanced_formatting(self, resume_data: Dict, customization_settings: Dict) -> Dict:
        """Process resume with enhanced formatting instructions for retry attempts"""
        job_description = customization_settings.get('job_description', '')
        last_response = resume_data.get('_last_response', {})
        quality_info = last_response.get('_quality_info', {})
        
        print(f"🔧 Retrying {resume_data.get('name', 'unknown')} with enhanced formatting instructions")
        print(f"   Previous issues: {quality_info.get('details', [])}")
        
        enhanced_prompt = f"""
        CRITICAL: The previous attempt failed due to formatting issues. You MUST follow these requirements exactly.
        
        🚨 MANDATORY JSON OUTPUT FORMAT 🚨
        - Your response must be ONLY a JSON object
        - Start with {{ and end with }}
        - NO text before the JSON
        - NO text after the JSON  
        - NO markdown code blocks (```json or ```)
        - NO explanations or comments
        - Use double quotes for ALL strings
        - Ensure proper comma placement
        
        Previous formatting issues detected:
        {', '.join(quality_info.get('details', []))}
        
        Task: Analyze this resume and return a properly formatted JSON object.
        
        Required JSON structure (fill with actual content from resume):
        {{
          "differentiators": [
            {{"claim": "Specific unique aspect", "evidence": "Exact quote from resume"}},
            {{"claim": "Another unique aspect", "evidence": "Another exact quote"}},
            {{"claim": "Third unique aspect", "evidence": "Third exact quote"}}
          ],
          "nickname": "Specific Role Name",
          "summary": "Brief summary with specific achievements and experience",
          "reservations": ["Specific concern 1", "Specific concern 2"],
          "relevant_achievements": [
            {{"achievement": "Quantified achievement", "evidence": "Exact quote"}},
            {{"achievement": "Another quantified achievement", "evidence": "Another quote"}},
            {{"achievement": "Third quantified achievement", "evidence": "Third quote"}},
            {{"achievement": "Fourth quantified achievement", "evidence": "Fourth quote"}}
          ],
          "wildcard": {{"fact": "Unique interesting fact", "evidence": "Exact supporting quote"}},
          "work_history": [
            {{"title": "Job Title", "company": "Company Name", "years": "2020-2024"}},
            {{"title": "Previous Title", "company": "Previous Company", "years": "2018-2020"}}
          ],
          "experience_distribution": {{"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}}
        }}
        
        Job Description: {job_description if job_description else "Not provided."}
        
        Resume Content:
        {resume_data['text'][:10000]}...
        
        Output ONLY the JSON object. No other text.
        """
        
        try:
            response = self.llm_service.chat(enhanced_prompt)
            
            # Parse with enhanced validation
            result = self._parse_json_response(response)
            result = self._validate_and_fix_result_structure(result)
            
            # Scrub any names that slipped through
            result = self._scrub_personal_identifiers(result, resume_data)
            
            # Validate quality again
            response_quality = self._assess_response_quality(result, resume_data, response)
            
            if response_quality['is_low_quality']:
                print(f"❌ Enhanced formatting retry still failed for {resume_data.get('name', 'unknown')}")
                return self._create_formatting_failure_response(resume_data, response, response_quality)
            
            print(f"✅ Enhanced formatting retry succeeded for {resume_data.get('name', 'unknown')}")
            return result
            
        except Exception as e:
            print(f"❌ Enhanced formatting retry failed for {resume_data.get('name', 'unknown')}: {e}")
            return self._create_formatting_failure_response(resume_data, str(e), {
                'is_low_quality': True,
                'reason': 'Enhanced retry failed',
                'details': [str(e)]
            })
    
    def _retry_with_json_focus(self, resume_data: Dict, customization_settings: Dict, original_response: str) -> Dict:
        """Retry with focused JSON formatting instructions"""
        try:
            job_description = customization_settings.get('job_description', '')
            
            retry_prompt = f"""
            The previous response was not valid JSON. Please analyze this resume and return ONLY a properly formatted JSON object.
            
            STRICT JSON REQUIREMENTS:
            - Return ONLY JSON - no explanations, no markdown, no extra text
            - Use proper JSON syntax with double quotes for all strings
            - Ensure proper comma placement and bracket matching
            - Do not include any text before or after the JSON object
            
            Original content that needs to be in JSON format:
            {original_response[:1000]}...
            
            Resume: {resume_data['text'][:8000]}...
            Job Description: {job_description if job_description else "Not provided."}
            
            Return a valid JSON object with these keys: differentiators, nickname, summary, reservations, relevant_achievements, wildcard, work_history, experience_distribution
            """
            
            retry_response = self.llm_service.chat(retry_prompt)
            result = self._parse_json_response(retry_response)
            result = self._validate_and_fix_result_structure(result)
            
            print(f"✅ Retry successful for {resume_data.get('name', 'unknown')}")
            return result
            
        except Exception as e:
            print(f"❌ Retry also failed for {resume_data.get('name', 'unknown')}: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Dict:
        """Enhanced JSON parsing with multiple cleaning strategies"""
        if not response or not response.strip():
            raise json.JSONDecodeError("Empty response", "", 0)
        
        # Strategy 1: Direct parsing (try first)
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Remove markdown code blocks
        clean_response = response.strip()
        
        # Remove various markdown block patterns
        patterns_to_remove = [
            r'^```json\s*',  # ```json at start
            r'^```\s*',      # ``` at start
            r'\s*```$',      # ``` at end
            r'^json\s*',     # standalone "json" at start
        ]
        
        for pattern in patterns_to_remove:
            clean_response = re.sub(pattern, '', clean_response, flags=re.MULTILINE)
        
        # Try parsing after markdown removal
        try:
            return json.loads(clean_response.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Find JSON within the response
        # Look for content between first { and last }
        start_idx = clean_response.find('{')
        end_idx = clean_response.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_content = clean_response[start_idx:end_idx + 1]
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Look for array pattern if it's a batch response
        start_idx = clean_response.find('[')
        end_idx = clean_response.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_content = clean_response[start_idx:end_idx + 1]
            try:
                return json.loads(json_content)
            except json.JSONDecodeError:
                pass
        
        # Strategy 5: Try fixing common JSON issues
        fixed_response = self._fix_common_json_issues(clean_response)
        try:
            return json.loads(fixed_response)
        except json.JSONDecodeError:
            pass
        
        # If all strategies fail, raise the original error
        raise json.JSONDecodeError(f"Could not parse JSON after multiple strategies. Response: {response[:200]}...", response, 0)
    
    def _fix_common_json_issues(self, response: str) -> str:
        """Fix common JSON formatting issues"""
        # Fix unescaped quotes in strings
        # This is a simple fix - might need more sophisticated handling
        fixed = response
        
        # Fix trailing commas before closing braces/brackets
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # Fix missing commas between array/object elements (basic patterns)
        fixed = re.sub(r'}\s*{', r'},{', fixed)  # Between objects
        fixed = re.sub(r']\s*\[', r'],[', fixed)  # Between arrays
        
        return fixed
    
    def _validate_and_fix_result_structure(self, result: Dict) -> Dict:
        """Ensure all required fields are present with proper structure"""
        if not isinstance(result, dict):
            raise ValueError("Result is not a dictionary")
        
        # Ensure all required fields are present with proper structure
        if 'differentiators' not in result:
            result['differentiators'] = []
        if 'nickname' not in result:
            result['nickname'] = 'Anonymous Pro'
        if 'summary' not in result:
            result['summary'] = 'Professional with relevant experience'
        if 'reservations' not in result:
            result['reservations'] = ['Manual review needed']
        if 'relevant_achievements' not in result:
            result['relevant_achievements'] = []
        if 'wildcard' not in result or not isinstance(result['wildcard'], dict):
            result['wildcard'] = {"fact": "Unique profile details pending analysis", "evidence": ""}
        if 'experience_distribution' not in result:
            result['experience_distribution'] = {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
        if 'work_history' not in result:
            result['work_history'] = []
        
        # Validate structure of complex fields
        if not isinstance(result['differentiators'], list):
            result['differentiators'] = []
        
        if not isinstance(result['relevant_achievements'], list):
            result['relevant_achievements'] = []
        
        if not isinstance(result['reservations'], list):
            result['reservations'] = ['Manual review needed']
        
        if not isinstance(result['work_history'], list):
            result['work_history'] = []
        
        return result
    
    def _scrub_personal_identifiers(self, result: Dict, resume_data: Dict) -> Dict:
        """Remove personal identifiers (names, gender pronouns) from LLM response to ensure anonymity"""
        # Extract candidate name from filename or resume data
        candidate_names = self._extract_candidate_names(resume_data)
        
        # Fields to scrub
        text_fields = ['summary', 'nickname']
        
        # Scrub main text fields
        for field in text_fields:
            if field in result and isinstance(result[field], str):
                result[field] = self._scrub_text(result[field], candidate_names)
        
        # Scrub differentiators
        if 'differentiators' in result and isinstance(result['differentiators'], list):
            for diff in result['differentiators']:
                if isinstance(diff, dict):
                    if 'claim' in diff:
                        diff['claim'] = self._scrub_text(diff['claim'], candidate_names)
                    if 'evidence' in diff:
                        diff['evidence'] = self._scrub_text(diff['evidence'], candidate_names)
        
        # Scrub achievements
        if 'relevant_achievements' in result and isinstance(result['relevant_achievements'], list):
            for achievement in result['relevant_achievements']:
                if isinstance(achievement, dict):
                    if 'achievement' in achievement:
                        achievement['achievement'] = self._scrub_text(achievement['achievement'], candidate_names)
                    if 'evidence' in achievement:
                        achievement['evidence'] = self._scrub_text(achievement['evidence'], candidate_names)
        
        # Scrub wildcard
        if 'wildcard' in result and isinstance(result['wildcard'], dict):
            if 'fact' in result['wildcard']:
                result['wildcard']['fact'] = self._scrub_text(result['wildcard']['fact'], candidate_names)
            if 'evidence' in result['wildcard']:
                result['wildcard']['evidence'] = self._scrub_text(result['wildcard']['evidence'], candidate_names)
        
        # Scrub reservations (might contain names in comparative statements)
        if 'reservations' in result and isinstance(result['reservations'], list):
            for i, reservation in enumerate(result['reservations']):
                if isinstance(reservation, str):
                    result['reservations'][i] = self._scrub_text(reservation, candidate_names)
        
        return result
    
    def _extract_candidate_names(self, resume_data: Dict) -> List[str]:
        """Extract potential candidate names from filename and resume data"""
        names = []
        
        # Extract from filename if available (via resume_data structure)
        if 'filename' in resume_data:
            # Use the same flexible name extraction logic as ResumeParser
            filename = resume_data['filename']
            name_without_ext = re.sub(r'\.[^.]+$', '', filename)  # Remove extension
            
            # Split by spaces, underscores, or other common separators
            parts = re.split(r'[_\s]+', name_without_ext)
            parts = [part.strip() for part in parts if part.strip()]
            
            if len(parts) >= 2:
                # Take first two parts as first and last name
                full_name = f"{parts[0]} {parts[1]}"
                names.extend(parts[:2])  # Add individual name parts
                names.append(full_name)  # Add full name
        
        # Extract from resume_data if 'name' field exists
        if 'name' in resume_data and resume_data['name'] != 'Unknown Candidate':
            candidate_name = resume_data['name']
            name_parts = candidate_name.split()
            names.extend(name_parts)
            names.append(candidate_name)
        
        # Extract common names from the beginning of resume text
        resume_text = resume_data.get('text', '')
        if resume_text:
            # Look for name patterns at the beginning of the resume
            lines = resume_text.split('\n')[:5]  # First 5 lines
            for line in lines:
                line = line.strip()
                # Skip email, phone, address patterns
                if any(pattern in line.lower() for pattern in ['@', 'phone', 'email', 'address', 'www', 'linkedin']):
                    continue
                # Look for potential names (2-3 words, capitalized, not too long)
                words = line.split()
                if 2 <= len(words) <= 3 and all(word.istitle() and word.isalpha() for word in words):
                    names.extend(words)
                    names.append(line)
        
        # Clean up and deduplicate
        cleaned_names = []
        for name in names:
            # Skip single characters, common words, etc.
            if len(name) > 1 and name.isalpha() and name not in ['Resume', 'CV', 'The', 'And', 'Or']:
                cleaned_names.append(name)
        
        return list(set(cleaned_names))  # Remove duplicates
    
    def _scrub_text(self, text: str, candidate_names: List[str]) -> str:
        """Scrub names and gender pronouns from a text string"""
        if not text:
            return text
        
        scrubbed = text
        
        # Remove candidate names (case insensitive)
        for name in candidate_names:
            if len(name) > 2:  # Only scrub names longer than 2 characters
                # Replace standalone name mentions
                pattern = r'\b' + re.escape(name) + r'\b'
                scrubbed = re.sub(pattern, '[CANDIDATE]', scrubbed, flags=re.IGNORECASE)
        
        # Remove gender pronouns and replace with neutral alternatives
        gender_replacements = {
            r'\bhe\b': 'they',
            r'\bhim\b': 'them', 
            r'\bhis\b': 'their',
            r'\bshe\b': 'they',
            r'\bher\b': 'their',
            r'\bhers\b': 'theirs',
            r'\bHe\b': 'They',
            r'\bHim\b': 'Them',
            r'\bHis\b': 'Their', 
            r'\bShe\b': 'They',
            r'\bHer\b': 'Their',
            r'\bHers\b': 'Theirs'
        }
        
        for pattern, replacement in gender_replacements.items():
            scrubbed = re.sub(pattern, replacement, scrubbed)
        
        # Clean up any leftover [CANDIDATE] references that start sentences awkwardly
        scrubbed = re.sub(r'\[CANDIDATE\]\s+is\s+', 'This candidate is ', scrubbed, flags=re.IGNORECASE)
        scrubbed = re.sub(r'\[CANDIDATE\]\s+has\s+', 'This candidate has ', scrubbed, flags=re.IGNORECASE)
        scrubbed = re.sub(r'\[CANDIDATE\]\s+', 'The candidate ', scrubbed, flags=re.IGNORECASE)
        
        return scrubbed.strip()
    
    def _parse_fallback_response(self, response: str) -> Dict:
        """Parse non-JSON response as fallback with smart text extraction"""
        # Try to extract useful information from the text response
        summary = ""
        reservations = ["Unable to analyze automatically"]
        achievements = ["Manual review needed"]
        wildcard = "Manual review needed"
        
        # Extract summary-like content (first few sentences)
        if response and len(response.strip()) > 0:
            # Remove any markdown artifacts
            clean_text = re.sub(r'```\w*|```', '', response)
            clean_text = re.sub(r'^json\s*', '', clean_text, flags=re.IGNORECASE)
            
            # Split into sentences and take first few
            sentences = [s.strip() for s in clean_text.split('.') if s.strip()]
            if sentences:
                # Take first 2-3 sentences as summary, up to 300 chars
                summary_parts = []
                char_count = 0
                for sentence in sentences[:3]:
                    if char_count + len(sentence) < 300:
                        summary_parts.append(sentence)
                        char_count += len(sentence)
                    else:
                        break
                
                if summary_parts:
                    summary = '. '.join(summary_parts) + '.'
                else:
                    summary = response[:200].strip() + "..."
            else:
                summary = response[:200].strip() + "..."
            
            # Look for potential concerns/reservations in the text
            concern_keywords = ['concern', 'gap', 'lack', 'missing', 'weakness', 'limitation', 'however', 'but']
            text_lower = response.lower()
            
            found_concerns = []
            for keyword in concern_keywords:
                if keyword in text_lower:
                    # Try to extract the sentence containing the concern
                    lines = response.split('.')
                    for line in lines:
                        if keyword in line.lower() and len(line.strip()) > 10:
                            found_concerns.append(line.strip()[:100])
                            break
            
            if found_concerns:
                reservations = found_concerns[:2]  # Take up to 2 concerns
            
            # Look for achievements or accomplishments
            achievement_keywords = ['achievement', 'accomplished', 'led', 'managed', 'increased', 'improved', 'built', 'created']
            found_achievements = []
            
            for keyword in achievement_keywords:
                if keyword in text_lower:
                    lines = response.split('.')
                    for line in lines:
                        if keyword in line.lower() and len(line.strip()) > 10:
                            found_achievements.append(line.strip()[:100])
                            break
            
            if found_achievements:
                achievements = found_achievements[:3]  # Take up to 3 achievements
        
        return {
            "nickname": "Review Pending",
            "summary": summary or "Professional candidate requiring manual review due to processing issues.",
            "reservations": reservations,
            "relevant_achievements": achievements,
            "wildcard": {"fact": wildcard, "evidence": ""},
            "work_history": [],
            "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0},
            "differentiators": []
        }
    
    def _create_error_response(self) -> Dict:
        """Create error response with helpful debugging information"""
        return {
            "nickname": "Processing Error",
            "summary": "An error occurred while processing this resume. This may indicate an issue with the LLM connection, response format, or resume content. Please check the logs for more details and consider manual review.",
            "reservations": [
                "Processing error occurred - manual review required",
                "LLM response could not be parsed or processed"
            ],
            "relevant_achievements": [
                "Error in processing - unable to extract achievements",
                "Manual review needed to assess qualifications"
            ],
            "wildcard": {
                "fact": "Processing failed - check system logs",
                "evidence": "Unable to process due to technical error"
            },
            "work_history": [],
            "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0},
            "differentiators": [
                {"claim": "Unable to determine differentiators", "evidence": "Processing error prevented analysis"},
                {"claim": "Manual review required", "evidence": "Technical issue during processing"},
                {"claim": "Check system logs for details", "evidence": "Error details available in application logs"}
            ]
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
                    
                    # Parse batch response using enhanced parsing
                    try:
                        batch_results = self._parse_json_response(response)
                        
                        # Ensure it's an array for batch processing
                        if not isinstance(batch_results, list):
                            raise ValueError("Batch response must be an array")
                        
                        # Map results back to candidate IDs
                        for j, result in enumerate(batch_results):
                            if j < len(batch):
                                candidate_id = batch[j]['id']
                                # Remove candidate_id from result if it exists
                                if 'candidate_id' in result:
                                    del result['candidate_id']
                                # Validate and fix structure
                                result = self._validate_and_fix_result_structure(result)
                                results[candidate_id] = result
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Batch JSON parsing failed: {e}")
                        print(f"Raw batch response preview: {response[:300]}...")
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

    def _assess_response_quality(self, result: Dict, resume_data: Dict, raw_response: str) -> Dict:
        """Assess if the parsed response contains meaningful content vs fallback data"""
        quality_issues = []
        
        # Check for generic/fallback content
        if result.get('nickname') in ['Anonymous Pro', 'Review Pending', 'Processing Error']:
            quality_issues.append('Generic nickname')
        
        if result.get('summary', '').startswith('Professional candidate requiring manual review'):
            quality_issues.append('Fallback summary text')
        
        # Check if differentiators are meaningful
        differentiators = result.get('differentiators', [])
        if not differentiators or len(differentiators) == 0:
            quality_issues.append('No differentiators found')
        elif all(d.get('claim', '').startswith('Unable to') for d in differentiators if isinstance(d, dict)):
            quality_issues.append('Generic differentiator content')
        
        # Check if achievements are meaningful
        achievements = result.get('relevant_achievements', [])
        if not achievements or len(achievements) == 0:
            quality_issues.append('No achievements found')
        elif isinstance(achievements, list) and len(achievements) > 0:
            if isinstance(achievements[0], str):
                # String format (fallback)
                if any(phrase in str(achievements[0]).lower() for phrase in ['manual review', 'error', 'unable']):
                    quality_issues.append('Fallback achievement content')
            elif isinstance(achievements[0], dict):
                # Proper dict format - check for meaningful content
                first_achievement = achievements[0].get('achievement', '')
                if any(phrase in first_achievement.lower() for phrase in ['error', 'unable', 'manual review']):
                    quality_issues.append('Generic achievement content')
        
        # Check work history
        work_history = result.get('work_history', [])
        if not work_history or len(work_history) == 0:
            # This could be legitimate if the resume has no work history
            # But let's check if the resume actually contains work experience
            resume_text = resume_data.get('text', '').lower()
            work_indicators = ['experience', 'employment', 'work', 'position', 'job', 'company', 'corp', 'inc', 'llc']
            
            if any(indicator in resume_text for indicator in work_indicators):
                quality_issues.append('No work history extracted despite resume containing work experience')
        
        # Check if response is too short relative to resume content
        resume_length = len(resume_data.get('text', ''))
        response_length = len(raw_response)
        
        if resume_length > 1000 and response_length < 500:
            quality_issues.append('Response too short for resume length')
        
        # Check for obvious parsing artifacts
        summary = result.get('summary', '')
        if any(artifact in summary.lower() for artifact in ['```', 'json', 'markdown', '```json']):
            quality_issues.append('Response contains formatting artifacts')
        
        is_low_quality = len(quality_issues) >= 2  # Threshold: 2+ quality issues
        
        return {
            'is_low_quality': is_low_quality,
            'reason': 'Multiple quality issues detected' if is_low_quality else 'Good quality',
            'details': quality_issues,
            'quality_score': max(0, 10 - len(quality_issues))  # Score out of 10
        }
    
    def _create_formatting_failure_response(self, resume_data: Dict, raw_response: str, quality_info: Dict) -> Dict:
        """Create a special response indicating formatting failure that needs retry"""
        return {
            "nickname": "Formatting Issue",
            "summary": f"LLM API succeeded but response format was invalid. Quality issues: {', '.join(quality_info.get('details', []))}. This will be retried with better formatting instructions.",
            "reservations": [
                "Response formatting failed - needs retry",
                f"Quality issues: {quality_info.get('reason', 'Unknown')}"
            ],
            "relevant_achievements": [
                "Formatting failure - will retry processing",
                "LLM response could not be properly parsed"
            ],
            "wildcard": {
                "fact": "Processing needs retry due to formatting",
                "evidence": f"Raw response length: {len(raw_response)} chars"
            },
            "work_history": [],
            "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0},
            "differentiators": [
                {"claim": "Formatting failure detected", "evidence": "LLM returned invalid format"},
                {"claim": "Will retry with better instructions", "evidence": "Automatic retry will be attempted"},
                {"claim": "Manual review if retries fail", "evidence": "Quality control system activated"}
            ],
            # Special marker to indicate this is a formatting failure
            "_formatting_failure": True,
            "_quality_info": quality_info,
            "_raw_response_preview": raw_response[:500]
        } 