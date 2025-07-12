# src/app.py
# At the top of the file, fix the import

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import json
from pathlib import Path
import threading
import queue

# Import our processing system
from core.integrated_ticket_processor import IntegratedTicketFiller

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this!
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Allowed extensions
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.mp4'}

# Create folders
for folder in ['uploads', 'outputs', 'static/previews']:
    os.makedirs(folder, exist_ok=True)

# Processing queue for async operations
processing_queue = queue.Queue()
processing_status = {}

class ProcessingThread(threading.Thread):
    """Background thread for processing tickets"""
    
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.processor = IntegratedTicketFiller(whisper_model="tiny")
        
    def run(self):
        """Process tickets from the queue"""
        while True:
            try:
                # Get job from queue
                job = processing_queue.get()
                job_id = job['id']
                
                # Update status
                processing_status[job_id] = {
                    'status': 'processing',
                    'progress': 10,
                    'message': 'Starting processing...'
                }
                
                # Process the ticket
                try:
                    result = self.processor.process_complete_ticket(
                        job['image_path'],
                        job['audio_path'],
                        job['output_path']
                    )
                    
                    # Update success status
                    processing_status[job_id] = {
                        'status': 'completed',
                        'progress': 100,
                        'message': 'Processing complete!',
                        'output_file': job['output_filename'],
                        'field_mappings': result.get('field_mappings', []),
                        'audio_data': result.get('audio_data', {})
                    }
                    
                except Exception as e:
                    # Update error status
                    processing_status[job_id] = {
                        'status': 'error',
                        'progress': 0,
                        'message': f'Error: {str(e)}'
                    }
                
            except Exception as e:
                print(f"Processing thread error: {e}")

# Start processing thread
processing_thread = ProcessingThread()
processing_thread.start()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and start processing"""
    try:
        # Check if files are present
        if 'ticket_image' not in request.files or 'audio_file' not in request.files:
            return jsonify({'error': 'Both image and audio files are required'}), 400
        
        ticket_image = request.files['ticket_image']
        audio_file = request.files['audio_file']
        
        # Validate files
        if ticket_image.filename == '' or audio_file.filename == '':
            return jsonify({'error': 'Please select both files'}), 400
        
        # Check extensions
        image_ext = Path(ticket_image.filename).suffix.lower()
        audio_ext = Path(audio_file.filename).suffix.lower()
        
        if image_ext not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({'error': f'Invalid image format. Allowed: {ALLOWED_IMAGE_EXTENSIONS}'}), 400
        
        if audio_ext not in ALLOWED_AUDIO_EXTENSIONS:
            return jsonify({'error': f'Invalid audio format. Allowed: {ALLOWED_AUDIO_EXTENSIONS}'}), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save files with unique names
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_filename = f"{job_id}_{timestamp}_ticket{image_ext}"
        audio_filename = f"{job_id}_{timestamp}_audio{audio_ext}"
        output_filename = f"{job_id}_{timestamp}_filled_ticket.docx"
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Save uploaded files
        ticket_image.save(image_path)
        audio_file.save(audio_path)
        
        # Add to processing queue
        job = {
            'id': job_id,
            'image_path': image_path,
            'audio_path': audio_path,
            'output_path': output_path,
            'output_filename': output_filename,
            'timestamp': datetime.now().isoformat()
        }
        
        processing_queue.put(job)
        
        # Initialize status
        processing_status[job_id] = {
            'status': 'queued',
            'progress': 0,
            'message': 'Waiting in queue...'
        }
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Files uploaded successfully. Processing started.'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<job_id>')
def get_status(job_id):
    """Get processing status"""
    if job_id in processing_status:
        return jsonify(processing_status[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed file"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f'processed_ticket_{datetime.now().strftime("%Y%m%d")}.docx'
            )
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def get_history():
    """Get processing history"""
    history = []
    
    # Get recent jobs from status
    for job_id, status in processing_status.items():
        if status['status'] == 'completed':
            history.append({
                'job_id': job_id,
                'timestamp': status.get('timestamp', 'Unknown'),
                'status': status['status'],
                'output_file': status.get('output_file', '')
            })
    
    # Sort by timestamp
    history.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify(history[:10])  # Last 10 jobs

if __name__ == '__main__':
    print("🚀 Starting Ticket Filler Web Application...")
    print("📍 Open your browser to: http://localhost:5000")
    app.run(debug=True, port=5000)