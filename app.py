from flask import Flask, render_template, request, jsonify
import subprocess
import json
import re
from threading import Thread
import time
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store scan results and status
scans = {}

def validate_ip_range(ip_range):
    # Basic validation for IP ranges
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
    if ',' in ip_range:
        ranges = ip_range.split(',')
        return all(re.match(ip_pattern, r.strip()) for r in ranges)
    return bool(re.match(ip_pattern, ip_range))

def validate_ports(ports):
    # Validate port ranges and lists
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

def run_masscan(scan_id, ip_range, ports, rate):
    try:
        command = [
            'sudo', 'masscan',
            ip_range,
            '-p', ports,
            '--rate', str(rate),
            '--output-format', 'json',
            '--output', f'/tmp/masscan_{scan_id}.json'
        ]
        
        scans[scan_id]['status'] = 'running'
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            try:
                with open(f'/tmp/masscan_{scan_id}.json', 'r') as f:
                    results = json.load(f)
                scans[scan_id]['results'] = results
                scans[scan_id]['status'] = 'completed'
            except Exception as e:
                scans[scan_id]['status'] = 'error'
                scans[scan_id]['error'] = str(e)
        else:
            scans[scan_id]['status'] = 'error'
            scans[scan_id]['error'] = stderr.decode()
            
    except Exception as e:
        scans[scan_id]['status'] = 'error'
        scans[scan_id]['error'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scan', methods=['POST'])
def start_scan():
    data = request.get_json()
    ip_range = data.get('ip_range', '').strip()
    ports = data.get('ports', '').strip()
    rate = int(data.get('rate', 1000))
    
    if not ip_range or not ports:
        return jsonify({'error': 'IP range and ports are required'}), 400
    
    if not validate_ip_range(ip_range):
        return jsonify({'error': 'Invalid IP range format'}), 400
    
    if not validate_ports(ports):
        return jsonify({'error': 'Invalid ports format'}), 400
    
    if not (100 <= rate <= 100000):
        return jsonify({'error': 'Rate must be between 100 and 100000'}), 400
    
    scan_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    scans[scan_id] = {
        'status': 'starting',
        'ip_range': ip_range,
        'ports': ports,
        'rate': rate,
        'start_time': datetime.now().isoformat(),
        'results': None,
        'error': None
    }
    
    Thread(target=run_masscan, args=(scan_id, ip_range, ports, rate)).start()
    return jsonify({'scan_id': scan_id})

@app.route('/scan_status/<scan_id>')
def scan_status(scan_id):
    if scan_id not in scans:
        return jsonify({'error': 'Scan not found'}), 404
    return jsonify(scans[scan_id])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12000)