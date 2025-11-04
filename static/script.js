const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resultsDiv = document.getElementById('results');

dropZone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    const files = e.target.files;
    handleFiles(files);
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    handleFiles(files);
});

resultsDiv.addEventListener('click', function(e) {
    const header = e.target.closest('.collapsible-header');
    if (header) {
        const content = header.nextElementSibling;
        const isActive = header.classList.contains('active');
        const allHeaders = resultsDiv.querySelectorAll('.collapsible-header');

        allHeaders.forEach(otherHeader => {
            otherHeader.classList.remove('active');
            otherHeader.nextElementSibling.style.display = 'none';
            const toggleIcon = otherHeader.querySelector('.toggle-icon');
            if (toggleIcon) {
                toggleIcon.textContent = '▼';
            }
        });

        if (!isActive) {
            header.classList.add('active');
            content.style.display = 'block';
            const toggleIcon = header.querySelector('.toggle-icon');
            if (toggleIcon) {
                toggleIcon.textContent = '▲';
            }
        }
        return;
    }

    const addRow = e.target.closest('.add-more-row');
    if (addRow) {
        fileInput.click();
    }
});

function createAddMoreRow() {
    const existingAddRow = document.querySelector('.add-more-row');
    if (existingAddRow) {
        existingAddRow.remove();
    }

    const addRow = document.createElement('div');
    addRow.className = 'add-more-row';
    addRow.textContent = 'Add More Files';
    resultsDiv.appendChild(addRow);
}

function handleFiles(files) {
    const formData = new FormData();
    const fileMap = new Map();

    for (const file of files) {
        if (file.name.endsWith('.eml')) {
            const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            formData.append('eml_files', file);
            fileMap.set(file.name, fileId);

            const resultDiv = document.createElement('div');
            resultDiv.id = fileId;
            resultDiv.innerHTML = `
                <div class="collapsible">
                    <button class="collapsible-header">
                        <span>${file.name}</span>
                        <span class="loading-spinner"></span>
                    </button>
                    <div class="collapsible-content">
                        <p>Loading email content and analytics...</p>
                    </div>
                </div>
            `;
            resultsDiv.appendChild(resultDiv);
        }
    }

    if (formData.has('eml_files')) {
        dropZone.style.display = 'none';
        createAddMoreRow();
    }

    fetch('/analyze', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        data.forEach(result => {
            const fileId = fileMap.get(result.filename);
            const targetDiv = document.getElementById(fileId);
            if (targetDiv) {
                if (result.error) {
                    targetDiv.innerHTML = `<p>Error processing ${result.filename}: ${result.error}</p>`;
                } else {
                    targetDiv.innerHTML = `
                        <div class="collapsible">
                            <button class="collapsible-header">
                                <span>${result.filename}</span>
                                <span class="toggle-icon">▼</span>
                            </button>
                            <div class="collapsible-content">
                                <div class="email-preview">
                                    <div class="email-header">
                                        <h3>${result.subject}</h3>
                                        <p><strong>From:</strong> ${result.from}</p>
                                        <p><strong>To:</strong> ${result.to}</p>
                                        <p><strong>Date:</strong> ${result.date}</p>
                                    </div>
                                    <div class="email-body">
                                        <iframe srcdoc="${result.body.replace(/"/g, '&quot;')}"></iframe>
                                    </div>
                                    <div class="analytics">
                                        <h4>Analytics</h4>
                                        <div class="analytics-item">
                                            <span>SPF</span>
                                            <span class="${result.analytics.spf}">${result.analytics.spf}</span>
                                        </div>
                                        <div class="analytics-item">
                                            <span>DKIM</span>
                                            <span class="${result.analytics.dkim}">${result.analytics.dkim}</span>
                                        </div>
                                        <div class="analytics-item">
                                            <span>DMARC</span>
                                            <span class="${result.analytics.dmarc}">${result.analytics.dmarc}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
            }
        });
        createAddMoreRow(); // Re-add it at the end
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
