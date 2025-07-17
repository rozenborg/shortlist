import os
import json
from datetime import datetime
from typing import List, Dict, Optional

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
        
        # Real-time processing tracking
        self.last_ui_update = datetime.now()
        self.processing_stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'processing_files': 0
        }
    
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

    def get_all_candidates(self, include_processing=True):
        """Get all candidates with enhanced real-time processing status"""
        resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
        candidates = []
        
        # Update processing stats
        self._update_processing_stats(resumes)
        
        for resume in resumes:
            candidate_id = resume['id']
            
            # Check if already processed (saved, passed, or starred)
            if self._is_candidate_decided(candidate_id):
                continue
            
            # Check if summary exists in cache
            if candidate_id in self.summaries:
                summary_data = self.summaries[candidate_id]
                candidate = {
                    'id': candidate_id,
                    'name': summary_data.get('nickname', 'Anonymous Pro'),
                    'filename': resume['filename'],
                    'processing_status': 'completed',
                    'ready_for_review': True,
                    **summary_data
                }
                candidates.append(candidate)
            elif include_processing:
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
                    'processing_status': 'processing',
                    'ready_for_review': False,
                    'processing': True
                }
                candidates.append(candidate)
        
        # Sort candidates: ready for review first, then processing
        candidates.sort(key=lambda x: (not x.get('ready_for_review', False), x.get('filename', '')))
        
        return candidates

    def get_ready_candidates(self):
        """Get only candidates that are ready for review (processed successfully)"""
        return [c for c in self.get_all_candidates(include_processing=False) if c.get('ready_for_review', False)]

    def get_processing_candidates(self):
        """Get candidates currently being processed"""
        return [c for c in self.get_all_candidates() if c.get('processing_status') == 'processing']

    def _is_candidate_decided(self, candidate_id):
        """Check if candidate has already been decided on"""
        saved_ids = [item['id'] for item in self.decisions['saved']]
        passed_ids = [item['id'] for item in self.decisions['passed']]
        starred_ids = [item['id'] for item in self.decisions.get('starred', [])]
        return candidate_id in saved_ids or candidate_id in passed_ids or candidate_id in starred_ids

    def _update_processing_stats(self, resumes):
        """Update processing statistics"""
        self.processing_stats = {
            'total_files': len(resumes),
            'processed_files': len([r for r in resumes if r['id'] in self.summaries]),
            'failed_files': 0,  # This will be updated by the background processor
            'processing_files': len([r for r in resumes if r['id'] not in self.summaries and not self._is_candidate_decided(r['id'])])
        }

    def get_processing_stats(self):
        """Get current processing statistics"""
        return {
            **self.processing_stats,
            'completion_percentage': (self.processing_stats['processed_files'] / self.processing_stats['total_files'] * 100) if self.processing_stats['total_files'] > 0 else 0
        }

    def get_newly_processed_candidates(self, background_processor):
        """Get candidates that were recently processed"""
        newly_processed_ids = background_processor.get_newly_processed_candidates()
        
        if not newly_processed_ids:
            return []
        
        # Get the full candidate data for newly processed candidates
        candidates = []
        for candidate_id in newly_processed_ids:
            if candidate_id in self.summaries:
                summary_data = self.summaries[candidate_id]
                
                # Find the resume info
                resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
                resume = next((r for r in resumes if r['id'] == candidate_id), None)
                
                if resume:
                    candidate = {
                        'id': candidate_id,
                        'name': summary_data.get('nickname', 'Anonymous Pro'),
                        'filename': resume['filename'],
                        'processing_status': 'completed',
                        'ready_for_review': True,
                        'newly_processed': True,
                        **summary_data
                    }
                    candidates.append(candidate)
        
        return candidates

    def get_candidate(self, candidate_id):
        """Get a specific candidate by ID with enhanced processing status"""
        resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
        
        for resume in resumes:
            if resume['id'] == candidate_id:
                if candidate_id in self.summaries:
                    summary_data = self.summaries[candidate_id]
                    return {
                        'id': candidate_id,
                        'name': summary_data.get('nickname', 'Anonymous Pro'),
                        'filename': resume['filename'],
                        'processing_status': 'completed',
                        'ready_for_review': True,
                        **summary_data
                    }
                else:
                    # Return processing placeholder
                    return {
                        'id': candidate_id,
                        'name': 'Processing...',
                        'nickname': 'Processing...',
                        'filename': resume['filename'],
                        'summary': 'This candidate is currently being processed...',
                        'processing_status': 'processing',
                        'ready_for_review': False,
                        'differentiators': [],
                        'reservations': ['Processing in progress...'],
                        'relevant_achievements': [],
                        'wildcard': {'fact': 'Processing...', 'evidence': ''},
                        'work_history': [],
                        'experience_distribution': {"corporate": 0, "startup": 0, "nonprofit": 0, "government": 0, "education": 0, "other": 0}
                    }
        
        return None

    def save_decision(self, candidate_id, decision):
        """Save swipe decision with enhanced tracking"""
        # Check if candidate is ready for review
        candidate = self.get_candidate(candidate_id)
        if not candidate or not candidate.get('ready_for_review', False):
            return {'success': False, 'message': 'Candidate not ready for review yet'}
        
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

    def get_saved_candidates(self):
        """Get all saved candidates with enhanced information (includes both saved and starred)"""
        saved_candidates = []
        
        # Get both saved and starred candidates
        saved_ids = [item['id'] for item in self.decisions['saved']]
        starred_ids = [item['id'] for item in self.decisions.get('starred', [])]
        all_saved_or_starred_ids = list(set(saved_ids + starred_ids))  # Remove duplicates
        
        custom_order = self.decisions.get('custom_order', [])
        
        # Start with custom ordered candidates (if they're saved or starred)
        ordered_ids = []
        for candidate_id in custom_order:
            if candidate_id in all_saved_or_starred_ids:
                ordered_ids.append(candidate_id)
        
        # Add any saved/starred candidates not in custom order
        for candidate_id in all_saved_or_starred_ids:
            if candidate_id not in ordered_ids:
                ordered_ids.append(candidate_id)
        
        for candidate_id in ordered_ids:
            if candidate_id in self.summaries:
                summary_data = self.summaries[candidate_id]
                
                # Find the resume info
                resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
                resume = next((r for r in resumes if r['id'] == candidate_id), None)
                
                if resume:
                    # Check status: saved, starred, or both
                    is_saved = candidate_id in saved_ids
                    is_starred = candidate_id in starred_ids
                    
                    # Add saved timestamp
                    saved_at = None
                    if is_saved:
                        saved_item = next((item for item in self.decisions['saved'] if item['id'] == candidate_id), None)
                        saved_at = saved_item['timestamp'] if saved_item else None
                    elif is_starred:
                        starred_item = next((item for item in self.decisions.get('starred', []) if item['id'] == candidate_id), None)
                        saved_at = starred_item['timestamp'] if starred_item else None
                    
                    candidate = {
                        'id': candidate_id,
                        'name': summary_data.get('nickname', 'Anonymous Pro'),
                        'filename': resume['filename'],
                        'is_starred': is_starred,
                        'is_saved': is_saved,
                        'saved_at': saved_at,
                        **summary_data
                    }
                    saved_candidates.append(candidate)
        
        return saved_candidates

    def update_candidate_order(self, ordered_ids):
        """Update the custom order of saved candidates"""
        self.decisions['custom_order'] = ordered_ids
        self._save_data()
        return {'success': True}

    def get_passed_candidates(self):
        """Get all passed candidates"""
        passed_candidates = []
        passed_ids = [item['id'] for item in self.decisions['passed']]
        
        for candidate_id in passed_ids:
            if candidate_id in self.summaries:
                summary_data = self.summaries[candidate_id]
                
                # Find the resume info
                resumes = self.resume_parser.get_all_resumes(self.candidates_folder)
                resume = next((r for r in resumes if r['id'] == candidate_id), None)
                
                if resume:
                    candidate = {
                        'id': candidate_id,
                        'name': summary_data.get('nickname', 'Anonymous Pro'),
                        'filename': resume['filename'],
                        **summary_data
                    }
                    passed_candidates.append(candidate)
        
        return passed_candidates

    def modify_decision(self, candidate_id, new_decision):
        """Modify an existing decision for a candidate"""
        timestamp = datetime.now().isoformat()
        
        # Find current decision
        current_decision = None
        saved_ids = [item['id'] for item in self.decisions['saved']]
        passed_ids = [item['id'] for item in self.decisions['passed']]
        starred_ids = [item['id'] for item in self.decisions.get('starred', [])]
        
        if candidate_id in saved_ids:
            current_decision = 'save'
        elif candidate_id in passed_ids:
            current_decision = 'pass'
        elif candidate_id in starred_ids:
            current_decision = 'star'
        
        if current_decision == new_decision:
            return {'success': True, 'message': 'No change needed'}
        
        # Remove from current lists
        self.decisions['saved'] = [d for d in self.decisions['saved'] if d.get('id') != candidate_id]
        self.decisions['passed'] = [d for d in self.decisions['passed'] if d.get('id') != candidate_id]
        if 'starred' in self.decisions:
            self.decisions['starred'] = [d for d in self.decisions['starred'] if d.get('id') != candidate_id]
        
        # Add to new list if not 'unreviewed'
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
        
        # Record decision change in history
        self.decision_history.append({
            'candidate_id': candidate_id,
            'old_decision': current_decision,
            'new_decision': new_decision,
            'timestamp': timestamp,
            'action': 'decision_modified'
        })
        
        self._save_data()
        return {'success': True, 'old_decision': current_decision, 'new_decision': new_decision}

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