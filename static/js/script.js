const socket = io();

socket.on('scan_update', (data) => {
    if (data.scan_id === currentScanId) {
        updateUI({
            status: data.status,
            error: data.error
        });
        
        if (data.status === 'completed' || data.status === 'error') {
            fetchScanDetails(currentScanId);
            loadRecentScans();
        }
    }
});

let currentScanId = null;

async function loadRecentScans() {
    try {
        const response = await fetch('/recent_scans');
        const scans = await response.json();
        
        const tbody = document.getElementById('recentScansBody');
        tbody.innerHTML = '';
        
        scans.forEach(scan => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${scan.scan_id}</td>
                <td>${scan.ip_range}</td>
                <td>${scan.status}</td>
                <td>${new Date(scan.start_time).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="viewScan('${scan.scan_id}')">
                        View Results
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading recent scans:', error);
    }
}

async function viewScan(scanId) {
    try {
        const response = await fetch(`/scan_status/${scanId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get scan details');
        }
        
        document.getElementById('results').style.display = 'none';
        document.getElementById('errorText').style.display = 'none';
        document.getElementById('scanStatus').style.display = 'block';
        
        updateUI(data);
        
    } catch (error) {
        console.error('Error viewing scan:', error);
    }
}

async function fetchScanDetails(scanId) {
    try {
        const response = await fetch(`/scan_status/${scanId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get scan details');
        }
        
        if (data.results) {
            displayResults(data.results);
            document.getElementById('results').style.display = 'block';
        }
        
    } catch (error) {
        console.error('Error fetching scan details:', error);
    }
}

document.getElementById('scanForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const ipRange = document.getElementById('ipRange').value;
    const ports = document.getElementById('ports').value;
    const rate = document.getElementById('rate').value;
    
    // Reset UI
    document.getElementById('results').style.display = 'none';
    document.getElementById('errorText').style.display = 'none';
    document.getElementById('scanStatus').style.display = 'block';
    document.getElementById('statusText').textContent = 'Starting scan...';
    document.querySelector('.progress-bar').style.width = '0%';
    document.querySelector('.progress-bar').classList.remove('bg-danger');
    document.querySelector('.progress-bar').classList.add('bg-primary');
    
    try {
        const response = await fetch('/start_scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ip_range: ipRange,
                ports: ports,
                rate: parseInt(rate)
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to start scan');
        }
        
        currentScanId = data.scan_id;
        loadRecentScans();
        
    } catch (error) {
        document.getElementById('errorText').textContent = error.message;
        document.getElementById('errorText').style.display = 'block';
        document.getElementById('statusText').textContent = 'Scan failed';
        document.querySelector('.progress-bar').style.width = '0%';
    }
});

function updateUI(data) {
    const statusText = document.getElementById('statusText');
    const progressBar = document.querySelector('.progress-bar');
    const errorText = document.getElementById('errorText');
    
    statusText.textContent = `Status: ${data.status}`;
    
    switch (data.status) {
        case 'starting':
            progressBar.style.width = '10%';
            break;
        case 'running':
            progressBar.style.width = '50%';
            break;
        case 'completed':
            progressBar.style.width = '100%';
            break;
        case 'error':
            progressBar.style.width = '100%';
            progressBar.classList.remove('bg-primary');
            progressBar.classList.add('bg-danger');
            errorText.textContent = data.error;
            errorText.style.display = 'block';
            break;
    }
}

function displayResults(results) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';
    
    if (!results || !Array.isArray(results)) {
        return;
    }
    
    results.forEach(result => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${result.ip}</td>
            <td>${result.ports[0].port}</td>
            <td>${result.ports[0].proto}</td>
            <td>open</td>
            <td>${new Date(result.timestamp).toLocaleString()}</td>
        `;
        tbody.appendChild(row);
    });
}

// Load recent scans when the page loads
document.addEventListener('DOMContentLoaded', loadRecentScans);