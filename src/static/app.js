/**
 * app.js — Core page UI logic for STRIDE Threat Analyzer
 *
 * Handles: drag-and-drop upload, image preview, form submission,
 * section toggling (upload → loading → report/error), copy-markdown,
 * and new-analysis/retry buttons.
 *
 * Exposes `window.strideRawMarkdown` for other modules (e.g. excel-export.js).
 */
(function () {
    'use strict';

    // --- DOM Elements ---
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const previewFilename = document.getElementById('preview-filename');
    const removeBtn = document.getElementById('remove-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const uploadForm = document.getElementById('upload-form');
    const uploadSection = document.getElementById('upload-section');
    const loadingSection = document.getElementById('loading-section');
    const errorSection = document.getElementById('error-section');
    const reportSection = document.getElementById('report-section');
    const errorMessage = document.getElementById('error-message');
    const errorTitle = document.getElementById('error-title');
    const errorIcon = document.getElementById('error-icon');
    const reportContent = document.getElementById('report-content');
    const copyMdBtn = document.getElementById('copy-md-btn');
    const newAnalysisBtn = document.getElementById('new-analysis-btn');
    const retryBtn = document.getElementById('retry-btn');

    let selectedFile = null;

    // Shared raw-markdown string other modules can read
    window.strideRawMarkdown = '';

    // --- Drag & Drop ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        selectedFile = file;
        previewFilename.textContent = file.name;

        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            previewContainer.classList.remove('hidden');
            dropZone.classList.add('hidden');
            analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    removeBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        previewContainer.classList.add('hidden');
        dropZone.classList.remove('hidden');
        analyzeBtn.disabled = true;
    });

    // --- Form Submission ---
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        // Show loading, hide others
        uploadSection.classList.add('hidden');
        errorSection.classList.add('hidden');
        reportSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');

        const formData = new FormData();
        formData.append('image', selectedFile);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                const err = new Error(data.error || 'Analysis failed');
                err.isQuota = data.quota_exceeded || false;
                err.isDaily = data.is_daily || false;
                throw err;
            }

            // Show report
            window.strideRawMarkdown = data.report_md;
            reportContent.innerHTML = data.report_html;
            loadingSection.classList.add('hidden');
            reportSection.classList.remove('hidden');

        } catch (err) {
            loadingSection.classList.add('hidden');

            // Render **bold** markdown in error messages
            const rendered = (err.message || 'An unexpected error occurred.')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            errorMessage.innerHTML = rendered;

            // Customise title/icon for quota vs generic errors
            if (err.isQuota && err.isDaily) {
                errorIcon.textContent = '⏳';
                errorTitle.textContent = 'Daily Quota Reached';
            } else if (err.isQuota) {
                errorIcon.textContent = '⚡';
                errorTitle.textContent = 'Rate Limit Hit';
            } else {
                errorIcon.textContent = '⚠️';
                errorTitle.textContent = 'Analysis Failed';
            }

            errorSection.classList.remove('hidden');
        }
    });

    // --- Copy Markdown ---
    copyMdBtn.addEventListener('click', async () => {
        try {
            await navigator.clipboard.writeText(window.strideRawMarkdown);
            const orig = copyMdBtn.innerHTML;
            copyMdBtn.innerHTML = '✅ Copied!';
            setTimeout(() => { copyMdBtn.innerHTML = orig; }, 2000);
        } catch {
            // fallback
            const ta = document.createElement('textarea');
            ta.value = window.strideRawMarkdown;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
    });

    // --- New Analysis / Retry ---
    function resetToUpload() {
        errorSection.classList.add('hidden');
        reportSection.classList.add('hidden');
        loadingSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
    }

    newAnalysisBtn.addEventListener('click', resetToUpload);
    retryBtn.addEventListener('click', resetToUpload);
})();
