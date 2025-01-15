from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit
import subprocess
import json
import re
import os
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
from datetime import datetime
import sqlite3
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "masscan_web.log"

logger = logging.getLogger("masscan_web")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Initialize Flask app with security headers
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per day", "10 per hour"]
)

# Initialize database
def init_db():
    with sqlite3.connect('scans.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                scan_id TEXT PRIMARY KEY,
                status TEXT,
                ip_range TEXT,
                ports TEXT,
                rate INTEGER,
                start_time TEXT,
                end_time TEXT,
                results TEXT,
                error TEXT
            )
        ''')

init_db()

class ScanError(Exception):
    pass

def save_scan_to_db(scan_data):
    try:
        with sqlite3.connect('scans.db') as conn:
            conn.execute('''
                INSERT OR REPLACE INTO scans 
                (scan_id, status, ip_range, ports, rate, start_time, end_time, results, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                scan_data['scan_id'],
                scan_data['status'],
                scan_data['ip_range'],
                scan_data['ports'],
                scan_data['rate'],
                scan_data['start_time'],
                scan_data.get('end_time'),
                json.dumps(scan_data.get('results')),
                scan_data.get('error')
            ))
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise

def get_scan_from_db(scan_id):
    try:
        with sqlite3.connect('scans.db') as conn:
            cursor = conn.execute('SELECT * FROM scans WHERE scan_id = ?', (scan_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'scan_id': row[0],
                    'status': row[1],
                    'ip_range': row[2],
                    'ports': row[3],
                    'rate': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'results': json.loads(row[7]) if row[7] else None,
                    'error': row[8]
                }
            return None
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        raise

def validate_ip_range(ip_range):
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
    if ',' in ip_range:
        ranges = ip_range.split(',')
        return all(re.match(ip_pattern, r.strip()) for r in ranges)
    return bool(re.match(ip_pattern, ip_range))

def validate_ports(ports):
    try:
        for port in ports.split(','):
            port = port.strip()
            if '-' in port:
                start, end = map(int, port.split('-'))
                if not (0 <= start <= 65535 and 0 <= end <= 65535 and start <= end):
                    return False
            else:
                port_num = int(port)
                if not (0 <= port_num <= 65535):
                    return False
        return True
    except ValueError:
        return False

def cleanup_temp_files(scan_id):
    try:
        temp_file = f'/tmp/masscan_{scan_id}.json'
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")

def run_masscan(scan_id, ip_range, ports, rate):
    logger.info(f"Starting scan {scan_id} for IP range: {ip_range}, ports: {ports}, rate: {rate}")
    scan_data = {
        'scan_id': scan_id,
        'status': 'running',
        'ip_range': ip_range,
        'ports': ports,
        'rate': rate,
        'start_time': datetime.now().isoformat()
    }
    
    try:
        command = [
            'sudo', 'masscan',
            ip_range,
            '-p', ports,
            '--rate', str(rate),
            '--output-format', 'json',
            '--output', f'/tmp/masscan_{scan_id}.json'
        ]
        
        save_scan_to_db(scan_data)
        socketio.emit('scan_update', {'scan_id': scan_id, 'status': 'running'})
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Monitor progress
        while True:
            if process.poll() is not None:
                break
            time.sleep(1)
            socketio.emit('scan_update', {
                'scan_id': scan_id,
                'status': 'running'
            })
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            try:
                with open(f'/tmp/masscan_{scan_id}.json', 'r') as f:
                    results = json.load(f)
                scan_data.update({
                    'status': 'completed',
                    'results': results,
                    'end_time': datetime.now().isoformat()
                })
            except Exception as e:
                raise ScanError(f"Error reading scan results: {str(e)}")
        else:
            raise ScanError(f"Masscan error: {stderr.decode()}")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Scan {scan_id} failed: {error_msg}")
        scan_data.update({
            'status': 'error',
            'error': error_msg,
            'end_time': datetime.now().isoformat()
        })
    finally:
        save_scan_to_db(scan_data)
        socketio.emit('scan_update', {
            'scan_id': scan_id,
            'status': scan_data['status'],
            'error': scan_data.get('error')
        })
        cleanup_temp_files(scan_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scan', methods=['POST'])
@limiter.limit("10 per hour")
def start_scan():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received")
        
        ip_range = data.get('ip_range', '').strip()
        ports = data.get('ports', '').strip()
        rate = int(data.get('rate', 1000))
        
        if not ip_range or not ports:
            raise ValueError("IP range and ports are required")
        
        if not validate_ip_range(ip_range):
            raise ValueError("Invalid IP range format")
        
        if not validate_ports(ports):
            raise ValueError("Invalid ports format")
        
        if not (100 <= rate <= 100000):
            raise ValueError("Rate must be between 100 and 100000")
        
        scan_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        threading.Thread(target=run_masscan, args=(scan_id, ip_range, ports, rate)).start()
        logger.info(f"Scan {scan_id} initiated successfully")
        
        return jsonify({
            'scan_id': scan_id,
            'message': 'Scan started successfully'
        })
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/scan_status/<scan_id>')
def scan_status(scan_id):
    try:
        scan_data = get_scan_from_db(scan_id)
        if not scan_data:
            return jsonify({'error': 'Scan not found'}), 404
        return jsonify(scan_data)
    except Exception as e:
        logger.error(f"Error retrieving scan status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/recent_scans')
def recent_scans():
    try:
        with sqlite3.connect('scans.db') as conn:
            cursor = conn.execute('''
                SELECT scan_id, status, ip_range, start_time 
                FROM scans 
                ORDER BY start_time DESC 
                LIMIT 10
            ''')
            scans = [{
                'scan_id': row[0],
                'status': row[1],
                'ip_range': row[2],
                'start_time': row[3]
            } for row in cursor.fetchall()]
            return jsonify(scans)
    except Exception as e:
        logger.error(f"Error retrieving recent scans: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=12000, allow_unsafe_werkzeug=True)