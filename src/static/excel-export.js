/**
 * excel-export.js — Self-contained Excel download for STRIDE reports
 *
 * Parses the markdown table from `window.strideRawMarkdown`, adds
 * Status and Notes tracking columns, and builds an .xlsx workbook.
 * Depends on: SheetJS (xlsx) loaded via CDN in index.html
 * Reads from: window.strideRawMarkdown (set by app.js or mock-data.js)
 */
(function () {
    'use strict';

    const downloadExcelBtn = document.getElementById('download-excel-btn');
    if (!downloadExcelBtn) return;

    downloadExcelBtn.addEventListener('click', () => {
        const rawMarkdown = window.strideRawMarkdown || '';

        // Find the markdown table block (lines starting with |)
        const lines = rawMarkdown.split('\n');
        const tableLines = lines.filter(l => l.trim().startsWith('|'));

        if (tableLines.length < 2) {
            alert('No table found in the report to export.');
            return;
        }

        // Parse a markdown table row into an array of cell strings
        const parseRow = (line) =>
            line.split('|')
                .slice(1, -1)           // drop first/last empty splits
                .map(cell => cell.trim());

        const headerRow = parseRow(tableLines[0]);
        const dataRows = tableLines
            .slice(2)                   // skip header + separator
            .map(parseRow);

        // Add tracking columns
        const trackingHeaders = ['Status', 'Notes'];
        const fullHeader = [...headerRow, ...trackingHeaders];
        const fullData = dataRows.map(row => [...row, '', '']);

        // Build worksheet
        const ws = XLSX.utils.aoa_to_sheet([fullHeader, ...fullData]);

        // Freeze header row & auto-width columns
        ws['!freeze'] = { xSplit: 0, ySplit: 1 };
        const colWidths = fullHeader.map((h, i) => ({
            wch: Math.max(
                h.length,
                ...fullData.map(r => (r[i] || '').length)
            ) + 4
        }));
        ws['!cols'] = colWidths;

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Threat Analysis');

        const title = lines.find(l => l.startsWith('# '))?.replace(/^# /, '').trim() || 'STRIDE Report';
        XLSX.writeFile(wb, title.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '_threats.xlsx');
    });
})();
