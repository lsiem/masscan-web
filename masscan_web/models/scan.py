from datetime import datetime
import json
import sqlite3
from typing import Optional, Dict, Any, List

class ScanStatus:
    STARTING = 'starting'
    RUNNING = 'running'
    COMPLETED = 'completed'
    ERROR = 'error'

class Scan:
    def __init__(self, scan_id: str, ip_range: str, ports: str, rate: int,
                 status: str = ScanStatus.STARTING, start_time: Optional[str] = None,
                 end_time: Optional[str] = None, results: Optional[List[Dict]] = None,
                 error: Optional[str] = None):
        self.scan_id = scan_id
        self.ip_range = ip_range
        self.ports = ports
        self.rate = rate
        self.status = status
        self.start_time = start_time or datetime.now().isoformat()
        self.end_time = end_time
        self.results = results
        self.error = error

    @classmethod
    def get_db_connection(cls) -> sqlite3.Connection:
        conn = sqlite3.connect('scans.db')
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls) -> None:
        with cls.get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scans (
                    scan_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    ip_range TEXT NOT NULL,
                    ports TEXT NOT NULL,
                    rate INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    results TEXT,
                    error TEXT
                )
            ''')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scan_id': self.scan_id,
            'status': self.status,
            'ip_range': self.ip_range,
            'ports': self.ports,
            'rate': self.rate,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'results': self.results,
            'error': self.error
        }

    def save(self) -> None:
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO scans 
                (scan_id, status, ip_range, ports, rate, start_time, end_time, results, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.scan_id,
                self.status,
                self.ip_range,
                self.ports,
                self.rate,
                self.start_time,
                self.end_time,
                json.dumps(self.results) if self.results else None,
                self.error
            ))

    @classmethod
    def get_by_id(cls, scan_id: str) -> Optional['Scan']:
        with cls.get_db_connection() as conn:
            row = conn.execute('SELECT * FROM scans WHERE scan_id = ?', (scan_id,)).fetchone()
            if row:
                return cls(
                    scan_id=row['scan_id'],
                    status=row['status'],
                    ip_range=row['ip_range'],
                    ports=row['ports'],
                    rate=row['rate'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    results=json.loads(row['results']) if row['results'] else None,
                    error=row['error']
                )
        return None

    @classmethod
    def get_recent(cls, limit: int = 10) -> List['Scan']:
        with cls.get_db_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM scans 
                ORDER BY start_time DESC 
                LIMIT ?
            ''', (limit,)).fetchall()
            return [cls(
                scan_id=row['scan_id'],
                status=row['status'],
                ip_range=row['ip_range'],
                ports=row['ports'],
                rate=row['rate'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                results=json.loads(row['results']) if row['results'] else None,
                error=row['error']
            ) for row in rows]

    def update_status(self, status: str, error: Optional[str] = None,
                     results: Optional[List[Dict]] = None) -> None:
        self.status = status
        if error:
            self.error = error
        if results:
            self.results = results
        if status in [ScanStatus.COMPLETED, ScanStatus.ERROR]:
            self.end_time = datetime.now().isoformat()
        self.save()