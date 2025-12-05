const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resultsDiv = document.getElementById('results');
const modal = document.getElementById('preview-modal');
const modalBody = document.getElementById('modal-body');
const closeButton = document.querySelector('.close-button');

dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    e.target.value = '';
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
  const preview = header.nextElementSibling.nextElementSibling;
    if (preview) {
        modalBody.innerHTML = '';
        const previewClone = preview.cloneNode(true);
        previewClone.style.display = 'block';
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
          iframe.addEventListener(
            'load',
            function() {},
            { once: true }
          );
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

// Close modal with Escape key
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.style.display === 'block') {
        modal.style.display = 'none';
    }
});

function createAddMoreRow() {
    const old = document.querySelector('.add-more-row');
    if (old) old.remove();

    const addRow = document.createElement('div');
    addRow.className = 'add-more-row';
    addRow.innerHTML = `
        <p style="margin:0; pointer-events:none; user-select:none;">
            Add more EML files
        </p>
    `;

    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = '.eml';
    input.style.display = 'none';
    addRow.appendChild(input);

    addRow.addEventListener('click', (e) => {
        e.stopPropagation();
        input.click();
    });

    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
            e.target.value = '';
        }
    });

    addRow.addEventListener('dragover', (e) => {
        e.preventDefault();
        addRow.style.border = '2px dashed #3498db';
        addRow.style.backgroundColor = '#f0f8ff';
    });

    addRow.addEventListener('dragleave', () => {
        addRow.style.border = '';
        addRow.style.backgroundColor = '';
    });

    addRow.addEventListener('drop', (e) => {
        e.preventDefault();
        addRow.style.border = '';
        addRow.style.backgroundColor = '';
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });

    resultsDiv.appendChild(addRow);
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
        resultsDiv.appendChild(placeholder);
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

            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            function escapePlainTextToHtml(text) {
                if (!text) return '';
                return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }

            const bodyHtml = result.body_html || result.body || `<pre style="white-space:pre-wrap;">${escapePlainTextToHtml(result.body || '')}</pre>`;
            const iframeSrcdoc = bodyHtml.replace(/"/g, '&quot;');

            targetDiv.innerHTML = `
      <div class="collapsible ${result.analytics.is_phishing ? 'phishing' : 'legit'}">
        <button class="collapsible-header">
            <span>${result.filename}</span>
            <div class="analytics-summary">
                <!-- <div class="analytics-item"><span>SPF</span><span class="${result.analytics.spf}">${result.analytics.spf.toUpperCase()}</span></div> -->
                <!-- <div class="analytics-item"><span>DKIM</span><span class="${result.analytics.dkim}">${result.analytics.dkim.toUpperCase()}</span></div> -->
                <!-- <div class="analytics-item"><span>DMARC</span><span class="${result.analytics.dmarc}">${result.analytics.dmarc.toUpperCase()}</span></div> -->
            </div>
        </button>

        <!-- REASONS BOX: ALWAYS VISIBLE -->
        <div class="reasons-box ${result.analytics.is_phishing ? 'phishing' : 'legit'}">
            <div class="confidence-badge ${result.analytics.confidence || 'medium'}">
                Confidence: ${result.analytics.confidence?.charAt(0).toUpperCase() + result.analytics.confidence?.slice(1) || 'Medium'}
            </div>
            <strong>
                ${result.analytics.is_phishing ? 'This email is PHISHING' : 'This email appears LEGITIMATE'}
            </strong>
            <ul>
                ${result.analytics.reasons && result.analytics.reasons.length > 0
                    ? result.analytics.reasons.map(r => `<li>${r}</li>`).join('')
                    : '<li>No red flags detected.</li>'
                }
            </ul>
        </div>

        <!-- EMAIL PREVIEW: ONLY SHOW WHEN CLICKED -->
        <div class="email-preview" style="display: none;">
            <!-- <div class="email-header"> -->
            <!--     <h3>${result.subject}</h3> -->
            <!--     <p><strong>From:</strong> ${result.from}</p> -->
            <!--     <p><strong>To:</strong> ${result.to}</p> -->
            <!--     <p><strong>Date:</strong> ${result.date}</p> -->
            <!-- </div> -->
          <div class="email-header">
              <h3>${escapeHtml(result.subject)}</h3>
              <div class="email-address-line"><strong>From:</strong> ${escapeHtml(result.from)}</div>
              <div class="email-address-line"><strong>To:</strong>   ${escapeHtml(result.to)}</div>
              <div class="email-address-line"><strong>Date:</strong> ${escapeHtml(result.date)}</div>
          </div>
            <div class="email-body">
                <iframe sandbox="allow-same-origin allow-scripts" srcdoc="${iframeSrcdoc}"></iframe>
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
