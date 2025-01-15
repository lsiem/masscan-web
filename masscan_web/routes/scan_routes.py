from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from flask_limiter.util import get_remote_address
from typing import Dict, Any, Tuple, Union

from ..models.scan import Scan, ScanStatus
from ..tasks.scan_tasks import run_masscan
from ..utils.exceptions import ValidationError, ResourceNotFoundError
from ..utils.validators import validate_scan_input

bp = Blueprint('scans', __name__)

def handle_error(error: Exception) -> Tuple[Dict[str, str], int]:
    """Convert exceptions to JSON responses with appropriate status codes."""
    status_code = getattr(error, 'status_code', 500)
    return jsonify({'error': str(error)}), status_code

@bp.route('/')
def index() -> str:
    """Render the main application page."""
    return render_template('index.html')

@bp.route('/start_scan', methods=['POST'])
def start_scan() -> Union[Tuple[Dict[str, Any], int], Tuple[Dict[str, str], int]]:
    """
    Start a new scan with the provided parameters.
    Returns scan_id on success.
    """
    try:
        data = request.get_json()
        if not data:
            raise ValidationError("No JSON data received")
        
        ip_range = data.get('ip_range', '').strip()
        ports = data.get('ports', '').strip()
        rate = int(data.get('rate', 1000))
        
        validate_scan_input(ip_range, ports, rate)
        
        scan_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        scan = Scan(
            scan_id=scan_id,
            ip_range=ip_range,
            ports=ports,
            rate=rate
        )
        scan.save()
        
        # Enqueue the scan task
        run_masscan.send(scan_id)
        
        return jsonify({
            'scan_id': scan_id,
            'message': 'Scan started successfully'
        }), 202
        
    except Exception as e:
        return handle_error(e)

@bp.route('/scan_status/<scan_id>')
def scan_status(scan_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, str], int]]:
    """Get the current status of a scan."""
    try:
        scan = Scan.get_by_id(scan_id)
        if not scan:
            raise ResourceNotFoundError(f"Scan {scan_id} not found")
        return jsonify(scan.to_dict())
    except Exception as e:
        return handle_error(e)

@bp.route('/recent_scans')
def recent_scans() -> Union[Dict[str, Any], Tuple[Dict[str, str], int]]:
    """Get a list of recent scans."""
    try:
        scans = Scan.get_recent(limit=10)
        return jsonify([scan.to_dict() for scan in scans])
    except Exception as e:
        return handle_error(e)