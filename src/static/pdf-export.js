/**
 * pdf-export.js — Self-contained PDF download for STRIDE reports
 *
 * Generates a formal, professional PDF using a white/blue/black colour palette.
 * Depends on: html2pdf.js (loaded via CDN in index.html)
 * Reads from: #report-content DOM node (no JS coupling to other modules)
 */
(function () {
    'use strict';

    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    if (!downloadPdfBtn) return;

    downloadPdfBtn.addEventListener('click', () => {
        const reportContent = document.getElementById('report-content');
        if (!reportContent) return;

        const title = reportContent.querySelector('h1')?.textContent?.trim() || 'STRIDE Threat Model Report';

        const wrapper = document.createElement('div');
        wrapper.style.padding = '20px';
        wrapper.className = 'pdf-export-container';

        const style = document.createElement('style');
        style.textContent = `
            .pdf-export-container {
                background: #ffffff !important;
                color: #111827 !important;
                font-family: 'Inter', Arial, sans-serif;
                width: 780px;
            }

            /* ── Title Banner ── */
            .pdf-export-container h1 {
                background-color: #1e40af !important;
                color: #ffffff !important;
                padding: 30px 20px;
                margin: 0 0 20px 0;
                font-size: 24pt;
                border: none;
                text-transform: capitalize;
                background-image: none !important;
                -webkit-background-clip: border-box !important;
                -webkit-text-fill-color: #ffffff !important;
                background-clip: border-box !important;
            }

            /* ── Section Headings ── */
            .pdf-export-container h2,
            .pdf-export-container h3 {
                color: #1e40af !important;
                margin: 20px;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 8px;
                -webkit-text-fill-color: #1e40af !important;
            }

            .pdf-export-container li { color: #374151 !important; }

            /* ── Tables ── */
            .pdf-export-container table {
                width: 100% !important;
                margin: 20px;
                border-collapse: collapse;
                table-layout: fixed;
                page-break-inside: auto !important;
                margin-top: 10px;
            }

            .pdf-export-container th {
                background-color: #1e40af !important;
                color: #ffffff !important;
                text-align: left;
                padding: 12px 8px;
                font-size: 10pt;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            .pdf-export-container td {
                padding: 10px 8px;
                border-bottom: 1px solid #e5e7eb;
                vertical-align: top;
                font-size: 9.5pt;
                line-height: 1.4;
                color: #374151 !important;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }

            /* Column widths */
            .pdf-export-container th:nth-child(1), .pdf-export-container td:nth-child(1) { width: 15%; }
            .pdf-export-container th:nth-child(2), .pdf-export-container td:nth-child(2) { width: 12%; }
            .pdf-export-container th:nth-child(3), .pdf-export-container td:nth-child(3) { width: 12%; }
            .pdf-export-container th:nth-child(4), .pdf-export-container td:nth-child(4) { width: 15%; }
            .pdf-export-container th:nth-child(5), .pdf-export-container td:nth-child(5) { width: 34%; }

            /* First column accent */
            .pdf-export-container td:first-child {
                font-weight: 700;
                color: #1e40af !important;
            }

            .pdf-export-container tr {
                page-break-inside: avoid !important;
                page-break-after: auto !important;
            }

            .pdf-export-container thead {
                display: table-header-group;
            }

            .pdf-export-container tr:nth-child(even) { background-color: #f8fafc; }
            .no-export { display: none; }
        `;

        const contentClone = reportContent.cloneNode(true);
        contentClone.querySelectorAll('button').forEach(b => b.remove());

        wrapper.appendChild(style);
        wrapper.appendChild(contentClone);

        const opt = {
            margin: [10, 0, 15, 0],
            filename: title.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: {
                scale: 2,
                useCORS: true,
                letterRendering: true,
                backgroundColor: '#ffffff'
            },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
            pagebreak: { mode: 'css' }
        };

        html2pdf().set(opt).from(wrapper).save();
    });
})();
