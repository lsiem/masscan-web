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
        
        pollStatus(data.scan_id);
        
    } catch (error) {
        document.getElementById('errorText').textContent = error.message;
        document.getElementById('errorText').style.display = 'block';
        document.getElementById('statusText').textContent = 'Scan failed';
        document.querySelector('.progress-bar').style.width = '0%';
    }
});

async function pollStatus(scanId) {
    try {
        const response = await fetch(`/scan_status/${scanId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get scan status');
        }
        
        updateUI(data);
        
        if (data.status === 'running' || data.status === 'starting') {
            setTimeout(() => pollStatus(scanId), 1000);
        }
        
    } catch (error) {
        document.getElementById('errorText').textContent = error.message;
        document.getElementById('errorText').style.display = 'block';
        document.getElementById('statusText').textContent = 'Status check failed';
    }
}

function updateUI(data) {
    const statusText = document.getElementById('statusText');
    const progressBar = document.querySelector('.progress-bar');
    const errorText = document.getElementById('errorText');
    const results = document.getElementById('results');
    
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
            displayResults(data.results);
            results.style.display = 'block';
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