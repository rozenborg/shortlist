import os
import json
from datetime import datetime

class CandidateService:
    def __init__(self, llm_service, resume_parser, customization_service):
        self.llm_service = llm_service
        self.resume_parser = resume_parser
        self.customization_service = customization_service
        self.candidates_folder = 'candidates'
        self.data_folder = 'data'
        self.decisions_file = os.path.join(self.data_folder, 'decisions.json')
        self.summaries_cache = os.path.join(self.data_folder, 'summaries_cache.json')
        self.decision_history_file = os.path.join(self.data_folder, 'decision_history.json')
        self._load_data()
        self.swipe_history = []
    
    def _load_data(self):
        """Load existing decisions and summaries from files"""
        # Load decisions
        if os.path.exists(self.decisions_file):
            with open(self.decisions_file, 'r') as f:
                self.decisions = json.load(f)
        else:
            self.decisions = {'saved': [], 'passed': [], 'starred': [], 'custom_order': []}
        
        # Ensure custom_order exists
        if 'custom_order' not in self.decisions:
            self.decisions['custom_order'] = []
        
        # Load decision history
        if os.path.exists(self.decision_history_file):
            with open(self.decision_history_file, 'r') as f:
                self.decision_history = json.load(f)
        else:
            self.decision_history = []
        
        # Load summaries cache
        if os.path.exists(self.summaries_cache):
            with open(self.summaries_cache, 'r') as f:
                self.summaries = json.load(f)
        else:
            self.summaries = {}
    
    def _save_data(self):
        """Save decisions, summaries, and history to files"""
        os.makedirs(self.data_folder, exist_ok=True)
        
        with open(self.decisions_file, 'w') as f:
            json.dump(self.decisions, f, indent=2)
        
        with open(self.decision_history_file, 'w') as f:
            json.dump(self.decision_history, f, indent=2)
        
        with open(self.summaries_cache, 'w') as f:
            json.dump(self.summaries, f, indent=2)
    
    def _generate_summary(self, resume_text, candidate_name):
        """Generate a summary of the candidate using LLM"""
        settings = self.customization_service.get_settings()
        job_description = settings.get('job_description', '')

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
        {resume_text[:12000]}...
        """
        
        try:
            response = self.llm_service.chat(prompt)
            # Try to parse as JSON, handling markdown code blocks
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
                # Fallback: create structured response
                return {
                    "differentiators": [],
                    "nickname": "Review Pending",
                    "summary": response[:200] + "...",
                    "reservations": ["Manual review needed"],
                    "relevant_achievements": [],
                    "wildcard": {"fact": "Manual review needed", "evidence": ""},
                    "work_history": [],
                    "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
                }
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {
                "differentiators": [],
                "nickname": "Processing Error",
                "summary": "Error generating summary",
                "reservations": ["Error in processing"],
                "relevant_achievements": [],
                "wildcard": {"fact": "Error in processing", "evidence": ""},
                "work_history": [],
                "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
            }
    
    def get_all_candidates(self):
        """Get all candidates with their summaries"""
        resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
        candidates = []
        
        for resume in resumes:
            candidate_id = resume['id']
            
            # Check if already processed (saved, passed, or starred)
            saved_ids = [item['id'] for item in self.decisions['saved']]
            passed_ids = [item['id'] for item in self.decisions['passed']]
            starred_ids = [item['id'] for item in self.decisions.get('starred', [])]
            if candidate_id in saved_ids or candidate_id in passed_ids or candidate_id in starred_ids:
                continue
            
            # Check if summary exists in cache
            if candidate_id in self.summaries:
                summary_data = self.summaries[candidate_id]
                candidate = {
                    'id': candidate_id,
                    'name': summary_data.get('nickname', 'Anonymous Pro'),  # Use nickname instead of real name
                    'filename': resume['filename'],
                    **summary_data
                }
                candidates.append(candidate)
            else:
                # Add placeholder for unprocessed candidates
                candidate = {
                    'id': candidate_id,
                    'name': 'Processing...',
                    'nickname': 'Processing...',
                    'filename': resume['filename'],
                    'summary': 'Processing...',
                    'differentiators': [],
                    'reservations': ['Processing...'],
                    'relevant_achievements': [],
                    'wildcard': {'fact': 'Processing...', 'evidence': ''},
                    'work_history': [],
                    'experience_distribution': {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0},
                    'processing': True
                }
                candidates.append(candidate)
        
        return candidates
    
    def get_candidate(self, candidate_id):
        """Get a specific candidate by ID"""
        resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
        
        for resume in resumes:
            if resume['id'] == candidate_id:
                if candidate_id not in self.summaries:
                    resume_text = self.resume_parser.parse_resume(resume['path'])
                    summary = self._generate_summary(resume_text, resume['name'])
                    self.summaries[candidate_id] = summary
                    self._save_data()
                
                summary_data = self.summaries[candidate_id]
                return {
                    'id': candidate_id,
                    'name': summary_data.get('nickname', 'Anonymous Pro'),  # Use nickname instead of real name
                    'filename': resume['filename'],
                    **summary_data
                }
        
        return None
    
    def save_decision(self, candidate_id, decision):
        """Save swipe decision"""
        timestamp = datetime.now().isoformat()
        
        # Ensure all decision types exist
        if 'starred' not in self.decisions:
            self.decisions['starred'] = []
        
        # Check if already in saved/passed/starred lists
        saved_ids = [item['id'] for item in self.decisions['saved']]
        passed_ids = [item['id'] for item in self.decisions['passed']]
        starred_ids = [item['id'] for item in self.decisions['starred']]
        
        if decision == 'save':
            if candidate_id not in saved_ids:
                self.decisions['saved'].append({
                    'id': candidate_id,
                    'timestamp': timestamp
                })
        elif decision == 'pass':
            if candidate_id not in passed_ids:
                self.decisions['passed'].append({
                    'id': candidate_id,
                    'timestamp': timestamp
                })
        elif decision == 'star':
            if candidate_id not in starred_ids:
                self.decisions['starred'].append({
                    'id': candidate_id,
                    'timestamp': timestamp
                })
        
        self.swipe_history.append({'candidate_id': candidate_id, 'decision': decision})
        
        # Record initial decision in history
        self.decision_history.append({
            'candidate_id': candidate_id,
            'old_decision': None,
            'new_decision': decision,
            'timestamp': timestamp,
            'action': 'initial_swipe'
        })
        
        self._save_data()
        return {'success': True, 'decision': decision}
    
    def undo_last_swipe(self):
        """Undo the last swipe decision"""
        if not self.swipe_history:
            return {'success': False, 'message': 'No history to undo'}

        last_swipe = self.swipe_history.pop()
        candidate_id = last_swipe['candidate_id']
        decision = last_swipe['decision']

        if decision == 'save':
            self.decisions['saved'] = [d for d in self.decisions['saved'] if d.get('id') != candidate_id]
        elif decision == 'pass':
            self.decisions['passed'] = [d for d in self.decisions['passed'] if d.get('id') != candidate_id]
        elif decision == 'star':
            if 'starred' in self.decisions:
                self.decisions['starred'] = [d for d in self.decisions['starred'] if d.get('id') != candidate_id]

        self._save_data()
        return {'success': True, 'undone_candidate_id': candidate_id}

    def restart_session(self):
        """Clear all decisions and start over"""
        self.decisions = {'saved': [], 'passed': [], 'starred': [], 'custom_order': []}
        self.swipe_history = []
        self._save_data()
        return {'success': True}

    def get_saved_candidates(self):
        """Get all saved candidates (both regular saves and starred)"""
        saved_candidates = []
        
        # Add regular saved candidates
        for saved in self.decisions['saved']:
            candidate = self.get_candidate(saved['id'])
            if candidate:
                candidate['saved_at'] = saved['timestamp']
                candidate['is_starred'] = False
                saved_candidates.append(candidate)
        
        # Add starred candidates
        if 'starred' in self.decisions:
            for starred in self.decisions['starred']:
                candidate = self.get_candidate(starred['id'])
                if candidate:
                    candidate['saved_at'] = starred['timestamp']
                    candidate['is_starred'] = True
                    saved_candidates.append(candidate)
        
        # Apply custom ordering if it exists
        custom_order = self.decisions.get('custom_order', [])
        if custom_order:
            # Create a mapping of candidate_id to candidate
            candidate_map = {c['id']: c for c in saved_candidates}
            ordered_candidates = []
            
            # Add candidates in custom order
            for candidate_id in custom_order:
                if candidate_id in candidate_map:
                    ordered_candidates.append(candidate_map[candidate_id])
                    del candidate_map[candidate_id]
            
            # Add any remaining candidates that aren't in the custom order (new saves)
            remaining_candidates = list(candidate_map.values())
            remaining_candidates.sort(key=lambda x: x['saved_at'], reverse=True)
            ordered_candidates.extend(remaining_candidates)
            
            return ordered_candidates
        else:
            # Default: Sort by timestamp (most recent first)
            saved_candidates.sort(key=lambda x: x['saved_at'], reverse=True)
            return saved_candidates
    
    def update_candidate_order(self, ordered_ids):
        """Update the custom order of saved candidates"""
        # Validate that all IDs are actually saved/starred candidates
        saved_ids = set()
        for saved in self.decisions['saved']:
            saved_ids.add(saved['id'])
        for starred in self.decisions.get('starred', []):
            saved_ids.add(starred['id'])
        
        # Filter to only include valid saved candidate IDs
        valid_ordered_ids = [cid for cid in ordered_ids if cid in saved_ids]
        
        self.decisions['custom_order'] = valid_ordered_ids
        self._save_data()
        return {'success': True, 'order_updated': len(valid_ordered_ids)}

    def get_passed_candidates(self):
        """Get all passed candidates with their summaries"""
        passed_candidates = []
        
        for passed in self.decisions['passed']:
            candidate = self.get_candidate(passed['id'])
            if candidate:
                candidate['passed_at'] = passed['timestamp']
                passed_candidates.append(candidate)
        
        # Sort by timestamp (most recent first)
        passed_candidates.sort(key=lambda x: x['passed_at'], reverse=True)
        return passed_candidates

    def modify_decision(self, candidate_id, new_decision):
        """Modify an existing decision for a candidate"""
        timestamp = datetime.now().isoformat()
        
        # Remove from all existing decision lists
        old_decision = None
        
        # Check and remove from saved
        saved_ids = [item['id'] for item in self.decisions['saved']]
        if candidate_id in saved_ids:
            self.decisions['saved'] = [d for d in self.decisions['saved'] if d.get('id') != candidate_id]
            old_decision = 'saved'
        
        # Check and remove from passed
        passed_ids = [item['id'] for item in self.decisions['passed']]
        if candidate_id in passed_ids:
            self.decisions['passed'] = [d for d in self.decisions['passed'] if d.get('id') != candidate_id]
            old_decision = 'passed'
        
        # Check and remove from starred
        if 'starred' in self.decisions:
            starred_ids = [item['id'] for item in self.decisions['starred']]
            if candidate_id in starred_ids:
                self.decisions['starred'] = [d for d in self.decisions['starred'] if d.get('id') != candidate_id]
                old_decision = 'starred'
        
        # Add to new decision list if not 'unreviewed'
        if new_decision == 'save':
            self.decisions['saved'].append({
                'id': candidate_id,
                'timestamp': timestamp
            })
        elif new_decision == 'pass':
            self.decisions['passed'].append({
                'id': candidate_id,
                'timestamp': timestamp
            })
        elif new_decision == 'star':
            if 'starred' not in self.decisions:
                self.decisions['starred'] = []
            self.decisions['starred'].append({
                'id': candidate_id,
                'timestamp': timestamp
            })
        # If new_decision is 'unreviewed', we just remove from all lists (already done above)
        
        # Remove from custom order if exists
        if 'custom_order' in self.decisions and candidate_id in self.decisions['custom_order']:
            self.decisions['custom_order'].remove(candidate_id)
        
        # Record decision modification in history
        self.decision_history.append({
            'candidate_id': candidate_id,
            'old_decision': old_decision,
            'new_decision': new_decision,
            'timestamp': timestamp,
            'action': 'modify_decision'
        })
        
        self._save_data()
        return {
            'success': True, 
            'old_decision': old_decision,
            'new_decision': new_decision,
            'candidate_id': candidate_id
        } 