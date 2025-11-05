const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resultsDiv = document.getElementById('results');
const modal = document.getElementById('preview-modal');
const modalBody = document.getElementById('modal-body');
const closeButton = document.querySelector('.close-button');

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
        openPreviewModal(header);
        return;
    }

    if (addRow) {
        fileInput.click();
    }
});

function openPreviewModal(header) {
    const preview = header.nextElementSibling;
    if (preview) {
        modalBody.innerHTML = ''; // Clear previous content
        const previewClone = preview.cloneNode(true);
        previewClone.style.display = 'block'; // Make it visible
        modalBody.appendChild(previewClone);
        modal.style.display = 'block';

        // Check if the original collapsible had the phishing flag
        const collapsibleParent = header.closest('.collapsible');
        if (collapsibleParent && collapsibleParent.classList.contains('phishing-flag')) {
            modal.querySelector('.modal-content').classList.add('modal-phishing-flag');
        } else {
            modal.querySelector('.modal-content').classList.remove('modal-phishing-flag');
        }

        const iframe = modalBody.querySelector('iframe');
        if (iframe) {
             // Height is now controlled by CSS to prevent scroll conflicts.
            iframe.addEventListener('load', function() {
                // No-op, height is handled by CSS max-height and overflow.
            }, { once: true });
        }
    }
}

closeButton.addEventListener('click', () => {
    modal.style.display = 'none';
});

window.addEventListener('click', (e) => {
    if (e.target == modal) {
        modal.style.display = 'none';
    }
});

function createAddMoreRow() {
    let addRow = document.querySelector('.add-more-row');
    if (addRow) {
        addRow.remove(); // Remove if it exists to re-append at the end
    } else {
        addRow = document.createElement('div');
        addRow.className = 'add-more-row';
        addRow.textContent = 'Add More Files';
    }
    resultsDiv.appendChild(addRow); // Always append to ensure it's at the bottom
}

function handleFiles(files) {
    const formData = new FormData();
    const fileMap = new Map();
    const addRow = resultsDiv.querySelector('.add-more-row');

    // Reverse the file list to handle browser's reverse selection order
    for (const file of [...files].reverse()) {
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
                <div class="collapsible-content" style="display: none;">
                    <p style="padding: 15px;">Loading email content and analytics...</p>
                </div>
            </div>
        `;
        resultsDiv.appendChild(placeholder); // Always append for FIFO
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

            const phishingClass = result.analytics.is_phishing ? 'phishing-flag' : '';

            targetDiv.innerHTML = `
                <div class="collapsible ${phishingClass}">
                    <button class="collapsible-header">
                        <span>${result.filename}</span>
                        <div class="analytics-summary">
                            <div class="analytics-item"><span>SPF</span><span class="${result.analytics.spf}">${result.analytics.spf}</span></div>
                            <div class="analytics-item"><span>DKIM</span><span class="${result.analytics.dkim}">${result.analytics.dkim}</span></div>
                            <div class="analytics-item"><span>DMARC</span><span class="${result.analytics.dmarc}">${result.analytics.dmarc}</span></div>
                        </div>
                    </button>
                    <div class="email-preview" style="display: none;">
                        <div class="email-header">
                            <h3>${result.subject}</h3>
                            <p><strong>From:</strong> ${result.from}</p>
                            <p><strong>To:</strong> ${result.to}</p>
                            <p><strong>Date:</strong> ${result.date}</p>
                        </div>
                        <div class="email-body">
                            <iframe srcdoc="${result.body.replace(/"/g, '&quot;')}"></iframe>
                        </div>
                    </div>
                </div>
            `;
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
