from flask_socketio import emit
from typing import Dict, Any

def emit_scan_update(scan_id: str, status: str, error: str = None) -> None:
    """Emit a scan update event to connected clients."""
    data = {
        'scan_id': scan_id,
        'status': status,
        'error': error
    }
    emit('scan_update', data, broadcast=True)

def emit_scan_progress(scan_id: str, progress: Dict[str, Any]) -> None:
    """Emit scan progress information to connected clients."""
    data = {
        'scan_id': scan_id,
        'progress': progress
    }
    emit('scan_progress', data, broadcast=True)