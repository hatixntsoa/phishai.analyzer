const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resultsDiv = document.getElementById('results');

// --- EVENT LISTENERS ---

dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    e.target.value = ''; // Allow re-uploading the same file
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

// Use event delegation for all clicks within the results area
resultsDiv.addEventListener('click', function(e) {
    const header = e.target.closest('.collapsible-header');
    const addRow = e.target.closest('.add-more-row');

    if (header) {
        // Prevent expanding while content is loading
        if (header.querySelector('.loading-spinner')) return;
        toggleCollapsible(header);
        return;
    }

    if (addRow) {
        fileInput.click();
    }
});

// --- DOM MANIPULATION ---

function toggleCollapsible(header) {
    const content = header.nextElementSibling;
    const isActive = header.classList.contains('active');
    const allHeaders = resultsDiv.querySelectorAll('.collapsible-header');

    // Close all other sections
    allHeaders.forEach(otherHeader => {
        if (otherHeader !== header) {
            otherHeader.classList.remove('active');
            otherHeader.nextElementSibling.style.display = 'none';
            const icon = otherHeader.querySelector('.toggle-icon');
            if (icon) icon.textContent = '▼';
        }
    });

    // Toggle the clicked section
    if (!isActive) {
        header.classList.add('active');
        content.style.display = 'block';
        const icon = header.querySelector('.toggle-icon');
        if (icon) icon.textContent = '▲';
    } else {
        header.classList.remove('active');
        content.style.display = 'none';
        const icon = header.querySelector('.toggle-icon');
        if (icon) icon.textContent = '▼';
    }
}

function createAddMoreRow() {
    if (document.querySelector('.add-more-row')) return; // Already exists
    const addRow = document.createElement('div');
    addRow.className = 'add-more-row';
    addRow.textContent = 'Add More Files';
    resultsDiv.appendChild(addRow);
}

function handleFiles(files) {
    const formData = new FormData();
    const fileMap = new Map();
    const addRow = resultsDiv.querySelector('.add-more-row');

    for (const file of files) {
        if (!file.name.endsWith('.eml')) continue;

        const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        formData.append('eml_files', file);
        fileMap.set(file.name, fileId);

        const placeholder = document.createElement('div');
        placeholder.id = fileId;
        placeholder.innerHTML = `
            <div class="collapsible">
                <button class="collapsible-header">
                    <span>${file.name}</span>
                    <span class="loading-spinner"></span>
                </button>
                <div class="collapsible-content">
                    <p style="padding: 15px;">Loading email content and analytics...</p>
                </div>
            </div>
        `;
        if (addRow) {
            resultsDiv.insertBefore(placeholder, addRow);
        } else {
            resultsDiv.appendChild(placeholder);
        }
    }

    if (!formData.has('eml_files')) return;

    dropZone.style.display = 'none';
    createAddMoreRow();

    fetch('/analyze', { method: 'POST', body: formData })
    .then(response => response.json())
    .then(data => {
        data.forEach(result => {
            const fileId = fileMap.get(result.filename);
            const targetDiv = document.getElementById(fileId);
            if (!targetDiv) return;

            if (result.error) {
                targetDiv.innerHTML = `<p>Error processing ${result.filename}: ${result.error}</p>`;
                return;
            }

            targetDiv.innerHTML = `
                <div class="collapsible">
                    <button class="collapsible-header">
                        <span>${result.filename}</span>
                        <span class="toggle-icon">▼</span>
                    </button>
                    <div class="collapsible-content" style="display: none;">
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
                                <div class="analytics-item"><span>SPF</span><span class="${result.analytics.spf}">${result.analytics.spf}</span></div>
                                <div class="analytics-item"><span>DKIM</span><span class="${result.analytics.dkim}">${result.analytics.dkim}</span></div>
                                <div class="analytics-item"><span>DMARC</span><span class="${result.analytics.dmarc}">${result.analytics.dmarc}</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const iframe = targetDiv.querySelector('iframe');
            const collapsibleContent = targetDiv.querySelector('.collapsible-content');

            if (iframe && collapsibleContent) {
                iframe.addEventListener('load', function() {
                    // 1. Temporarily make it visible but off-screen to measure
                    collapsibleContent.style.position = 'absolute';
                    collapsibleContent.style.visibility = 'hidden';
                    collapsibleContent.style.display = 'block';

                    const height = this.contentWindow.document.documentElement.scrollHeight;
                    this.style.height = height + 'px';

                    // 2. Hide it again, resetting styles, now that height is set
                    collapsibleContent.style.position = '';
                    collapsibleContent.style.visibility = '';
                    collapsibleContent.style.display = 'none';

                    // 3. Swap loading spinner for toggle icon
                    const header = targetDiv.querySelector('.collapsible-header');
                    const spinner = header.querySelector('.loading-spinner');
                    if (spinner) {
                         const toggleIcon = document.createElement('span');
                         toggleIcon.className = 'toggle-icon';
                         toggleIcon.textContent = '▼';
                         spinner.replaceWith(toggleIcon);
                    }
                }, { once: true });
            }
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
