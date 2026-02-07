"""
Flask Web Interface for Hotel Room Extractor
"""

from flask import Flask, render_template, request, jsonify, send_file
import asyncio
from scraper import HotelRoomExtractor
import os
import threading
from datetime import datetime

app = Flask(__name__)

# Global status
extraction_status = {
    'running': False,
    'progress': '',
    'results': [],
    'error': None
}

def run_extraction(hotels):
    """Run extraction in background"""
    global extraction_status
    
    try:
        extraction_status['running'] = True
        extraction_status['progress'] = 'Initializing...'
        extraction_status['error'] = None
        
        extractor = HotelRoomExtractor()
        
        def progress_callback(message):
            extraction_status['progress'] = message
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            extractor.process_hotels(hotels, progress_callback)
        )
        
        extraction_status['progress'] = 'Saving results...'
        filepath = extractor.save_to_csv(results)
        
        extraction_status['results'] = results
        extraction_status['progress'] = f'✓ Complete! Extracted {len(results)} room types'
        extraction_status['running'] = False
        extraction_status['filepath'] = filepath
        
    except Exception as e:
        extraction_status['error'] = str(e)
        extraction_status['running'] = False
        extraction_status['progress'] = f'Error: {str(e)}'

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    """Start extraction"""
    global extraction_status
    
    if extraction_status['running']:
        return jsonify({'error': 'Extraction already running'}), 400
    
    data = request.json
    mode = data.get('mode', 'single')
    
    hotels = []
    
    if mode == 'single':
        hotel_id = data.get('hotel_id', '')
        hotel_name = data.get('hotel_name', '')
        city = data.get('city', '')
        address = data.get('address', '')
        
        if not hotel_id or not hotel_name:
            return jsonify({'error': 'Hotel ID and Hotel Name are required'}), 400
        
        hotels = [{
            'hotel_id': hotel_id,
            'hotel_name': hotel_name,
            'city': city,
            'address': address
        }]
    else:
        csv_data = data.get('csv_data', '')
        if not csv_data:
            return jsonify({'error': 'CSV data is required'}), 400
        
        lines = csv_data.strip().split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = [p.strip().strip('"') for p in line.split(',')]
                if len(parts) >= 2:
                    hotels.append({
                        'hotel_id': parts[0],
                        'hotel_name': parts[1],
                        'city': parts[2] if len(parts) > 2 else '',
                        'address': parts[3] if len(parts) > 3 else ''
                    })
    
    if not hotels:
        return jsonify({'error': 'No hotels to process'}), 400
    
    extraction_status = {
        'running': True,
        'progress': 'Starting...',
        'results': [],
        'error': None,
        'filepath': None
    }
    
    thread = threading.Thread(target=run_extraction, args=(hotels,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Extraction started'})

@app.route('/status')
def status():
    """Get current status"""
    return jsonify(extraction_status)

@app.route('/files')
def list_files():
    """List output files"""
    output_dir = 'output'
    if not os.path.exists(output_dir):
        return jsonify([])
    
    files = []
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        files.append({
            'name': filename,
            'size': os.path.getsize(filepath),
            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(sorted(files, key=lambda x: x['modified'], reverse=True))

@app.route('/download/<filename>')
def download(filename):
    """Download a file"""
    filepath = os.path.join('output', filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return 'File not found', 404

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏨 Hotel Room Extractor - Web Interface")
    print("="*60)
    print("\n✓ Server starting...")
    print("\n👉 Open your browser and go to:")
    print("\n   http://localhost:5000")
    print("\n❌ Press CTRL+C to stop the server")
    print("\n" + "="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
