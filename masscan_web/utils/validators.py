import re
from typing import Union, List
from .exceptions import ValidationError

def validate_ip_range(ip_range: str) -> bool:
    """
    Validate IP range format.
    Supports CIDR notation and comma-separated IPs.
    """
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
    if ',' in ip_range:
        ranges = ip_range.split(',')
        return all(re.match(ip_pattern, r.strip()) for r in ranges)
    return bool(re.match(ip_pattern, ip_range))

def validate_ports(ports: str) -> bool:
    """
    Validate port ranges and lists.
    Supports individual ports, ranges (e.g., 80-443), and comma-separated combinations.
    """
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

def validate_scan_rate(rate: Union[int, str]) -> bool:
    """
    Validate scan rate.
    Must be between 100 and 100000 packets per second.
    """
    try:
        rate_int = int(rate)
        return 100 <= rate_int <= 100000
    except ValueError:
        return False

def validate_scan_input(ip_range: str, ports: str, rate: Union[int, str]) -> None:
    """
    Validate all scan input parameters.
    Raises ValidationError if any parameter is invalid.
    """
    if not ip_range or not ports:
        raise ValidationError("IP range and ports are required")
    
    if not validate_ip_range(ip_range):
        raise ValidationError("Invalid IP range format")
    
    if not validate_ports(ports):
        raise ValidationError("Invalid ports format")
    
    if not validate_scan_rate(rate):
        raise ValidationError("Rate must be between 100 and 100000")