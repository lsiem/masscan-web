import dramatiq
import json
import logging
import os
import subprocess
from typing import Optional, Dict, Any

from ..models.scan import Scan, ScanStatus
from ..utils.exceptions import ScanError

logger = logging.getLogger(__name__)

@dramatiq.actor(max_retries=0)
def run_masscan(scan_id: str) -> None:
    """
    Execute a Masscan task with the given scan_id.
    The scan parameters are retrieved from the database.
    """
    try:
        scan = Scan.get_by_id(scan_id)
        if not scan:
            raise ScanError(f"Scan {scan_id} not found")

        logger.info(f"Starting scan {scan_id} for IP range: {scan.ip_range}, ports: {scan.ports}, rate: {scan.rate}")
        
        temp_file = f'/tmp/masscan_{scan_id}.json'
        command = [
            'sudo', 'masscan',
            scan.ip_range,
            '-p', scan.ports,
            '--rate', str(scan.rate),
            '--output-format', 'json',
            '--output', temp_file
        ]

        scan.update_status(ScanStatus.RUNNING)
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            try:
                with open(temp_file, 'r') as f:
                    results = json.load(f)
                scan.update_status(ScanStatus.COMPLETED, results=results)
                logger.info(f"Scan {scan_id} completed successfully")
            except Exception as e:
                raise ScanError(f"Error reading scan results: {str(e)}")
        else:
            raise ScanError(f"Masscan error: {stderr.decode()}")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Scan {scan_id} failed: {error_msg}")
        if scan:
            scan.update_status(ScanStatus.ERROR, error=error_msg)
    finally:
        cleanup_temp_files(scan_id)

def cleanup_temp_files(scan_id: str) -> None:
    """Clean up temporary files created during the scan."""
    try:
        temp_file = f'/tmp/masscan_{scan_id}.json'
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")

@dramatiq.actor
def cleanup_old_scans(days: int = 30) -> None:
    """
    Cleanup old scan results and temporary files.
    This can be scheduled to run periodically.
    """
    try:
        with Scan.get_db_connection() as conn:
            conn.execute('''
                DELETE FROM scans 
                WHERE datetime(start_time) < datetime('now', '-? days')
            ''', (days,))
        logger.info(f"Cleaned up scan results older than {days} days")
    except Exception as e:
        logger.error(f"Error cleaning up old scans: {str(e)}")