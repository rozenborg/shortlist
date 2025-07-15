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
        
        # Load summaries cache
        if os.path.exists(self.summaries_cache):
            with open(self.summaries_cache, 'r') as f:
                self.summaries = json.load(f)
        else:
            self.summaries = {}
    
    def _save_data(self):
        """Save decisions and summaries to files"""
        os.makedirs(self.data_folder, exist_ok=True)
        
        with open(self.decisions_file, 'w') as f:
            json.dump(self.decisions, f, indent=2)
        
        with open(self.summaries_cache, 'w') as f:
            json.dump(self.summaries, f, indent=2)
    
    def _generate_summary(self, resume_text, candidate_name):
        """Generate a summary of the candidate using LLM"""
        settings = self.customization_service.get_settings()
        job_description = settings.get('job_description', '')

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
        - "experience_distribution": An object with years of experience in different sectors: {{"corporate": X, "startup": Y, "nonprofit": Z, "government": W, "education": V, "other": U}} where each value is years. For this section, look through all the experience and carefully add up the years in each (can be 0)

        Job Description:
        {job_description if job_description else "Not provided."}

        Resume to analyze:
        {resume_text[:3000]}...
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
                # Ensure nickname is present
                if 'nickname' not in result:
                    result['nickname'] = 'Anonymous Pro'
                # Ensure wildcard is present
                if 'wildcard' not in result:
                    result['wildcard'] = 'Unique profile details pending analysis'
                # Ensure experience_distribution is present and properly formatted
                if 'experience_distribution' not in result:
                    result['experience_distribution'] = {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
                return result
            except json.JSONDecodeError:
                # Fallback: create structured response
                return {
                    "nickname": "Review Pending",
                    "summary": response[:200] + "...",
                    "reservations": ["Manual review needed"],
                    "fit_indicators": ["Manual review needed"],
                    "achievements": ["Achievement extraction pending"],
                    "wildcard": "Manual review needed",
                    "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
                }
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {
                "nickname": "Processing Error",
                "summary": "Error generating summary",
                "reservations": ["Error in processing"],
                "fit_indicators": ["Error in processing"],
                "achievements": [],
                "wildcard": "Error in processing",
                "experience_distribution": {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
            }
    
    def get_all_candidates(self):
        """Get all candidates with their summaries"""
        resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
        candidates = []
        
        for resume in resumes:
            candidate_id = resume['id']
            
            # Check if already processed (saved or passed)
            saved_ids = [item['id'] for item in self.decisions['saved']]
            passed_ids = [item['id'] for item in self.decisions['passed']]
            if candidate_id in saved_ids or candidate_id in passed_ids:
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
                    'reservations': ['Processing...'],
                    'fit_indicators': ['Processing...'],
                    'achievements': ['Processing...'],
                    'wildcard': 'Processing...',
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