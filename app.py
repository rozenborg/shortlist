from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from src.factory import get_llm_client
from src.manager import LLMService
from src.resume_parser import ResumeParser
from src.candidate_service import CandidateService
from src.background_processor import BackgroundProcessor
from src.customization_service import CustomizationService

app = Flask(__name__)
CORS(app)

# Initialize services
client = get_llm_client()
llm_service = LLMService(client)
resume_parser = ResumeParser()
customization_service = CustomizationService()
candidate_service = CandidateService(llm_service, resume_parser, customization_service)
background_processor = BackgroundProcessor(candidate_service, resume_parser, llm_service)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    """Get all candidates from the candidates folder"""
    candidates = candidate_service.get_all_candidates()
    return jsonify(candidates)

@app.route('/api/candidate/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """Get a specific candidate by ID"""
    candidate = candidate_service.get_candidate(candidate_id)
    if candidate:
        return jsonify(candidate)
    return jsonify({'error': 'Candidate not found'}), 404

@app.route('/api/swipe', methods=['POST'])
def handle_swipe():
    """Handle swipe decision (left/right)"""
    data = request.json
    candidate_id = data.get('candidate_id')
    decision = data.get('decision')  # 'pass' or 'save'
    
    result = candidate_service.save_decision(candidate_id, decision)
    return jsonify(result)

@app.route('/api/saved', methods=['GET'])
def get_saved_candidates():
    """Get all saved candidates"""
    saved = candidate_service.get_saved_candidates()
    return jsonify(saved)

@app.route('/api/process/start', methods=['POST'])
def start_background_processing():
    """Start background processing of all resumes"""
    background_processor.start_background_processing()
    return jsonify({'status': 'started'})

@app.route('/api/process/status', methods=['GET'])
def get_processing_status():
    """Get current processing status"""
    status = background_processor.get_status()
    return jsonify(status)

@app.route('/api/process/batch', methods=['POST'])
def process_batch():
    """Process a specific batch of candidates immediately"""
    data = request.json
    candidate_ids = data.get('candidate_ids', [])
    
    if not candidate_ids:
        return jsonify({'error': 'No candidate IDs provided'}), 400
    
    results = background_processor.force_process_batch(candidate_ids)
    return jsonify({
        'processed_count': len(results),
        'results': results
    })

@app.route('/api/customize', methods=['GET', 'POST'])
def customize():
    if request.method == 'POST':
        data = request.json
        job_description = data.get('job_description', '')
        instructions = data.get('instructions', '')
        result = customization_service.update_settings(job_description, instructions)
        # Invalidate cache to force re-summarization
        if os.path.exists(candidate_service.summaries_cache):
            os.remove(candidate_service.summaries_cache)
        background_processor.start_background_processing()
        return jsonify(result)
    else:
        settings = customization_service.get_settings()
        return jsonify(settings)

@app.route('/api/undo', methods=['POST'])
def undo_swipe():
    """Undo the last swipe"""
    result = candidate_service.undo_last_swipe()
    return jsonify(result)

@app.route('/api/restart', methods=['POST'])
def restart_session():
    """Restart the session"""
    result = candidate_service.restart_session()
    # Also, clear the cache for a full restart
    if os.path.exists(candidate_service.summaries_cache):
        os.remove(candidate_service.summaries_cache)
    background_processor.start_background_processing()
    return jsonify(result)

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('candidates', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Start background processing automatically
    print("Starting background processing...")
    background_processor.start_background_processing()
    
    app.run(debug=True) 