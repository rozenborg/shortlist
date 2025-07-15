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
            self.decisions = {'saved': [], 'passed': []}
        
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
        instructions = settings.get('instructions', '')

        prompt = f"""
        Analyze the resume for {candidate_name} based on the job description below.
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
                
                return json.loads(clean_response.strip())
            except json.JSONDecodeError:
                # Fallback: create structured response
                return {
                    "summary": response[:200] + "...",
                    "skills": ["Skill extraction pending"],
                    "experience_level": "To be determined",
                    "achievements": ["Achievement extraction pending"],
                    "fit_score": 5,
                    "fit_reasoning": "Manual review needed"
                }
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {
                "summary": "Error generating summary",
                "skills": [],
                "experience_level": "Unknown",
                "achievements": [],
                "fit_score": 0,
                "fit_reasoning": "Error in processing"
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
                candidate = {
                    'id': candidate_id,
                    'name': resume['name'],
                    'filename': resume['filename'],
                    **self.summaries[candidate_id]
                }
                candidates.append(candidate)
            else:
                # Add placeholder for unprocessed candidates
                candidate = {
                    'id': candidate_id,
                    'name': resume['name'],
                    'filename': resume['filename'],
                    'summary': 'Processing...',
                    'skills': ['Processing...'],
                    'experience_level': 'Processing...',
                    'achievements': ['Processing...'],
                    'fit_score': 0,
                    'fit_reasoning': 'Processing...',
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
                
                return {
                    'id': candidate_id,
                    'name': resume['name'],
                    'filename': resume['filename'],
                    **self.summaries[candidate_id]
                }
        
        return None
    
    def save_decision(self, candidate_id, decision):
        """Save swipe decision"""
        timestamp = datetime.now().isoformat()
        
        # Check if already in saved/passed lists
        saved_ids = [item['id'] for item in self.decisions['saved']]
        passed_ids = [item['id'] for item in self.decisions['passed']]
        
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

        self._save_data()
        return {'success': True, 'undone_candidate_id': candidate_id}

    def restart_session(self):
        """Clear all decisions and start over"""
        self.decisions = {'saved': [], 'passed': []}
        self.swipe_history = []
        self._save_data()
        return {'success': True}

    def get_saved_candidates(self):
        """Get all saved candidates"""
        saved_candidates = []
        
        for saved in self.decisions['saved']:
            candidate = self.get_candidate(saved['id'])
            if candidate:
                candidate['saved_at'] = saved['timestamp']
                saved_candidates.append(candidate)
        
        return saved_candidates 