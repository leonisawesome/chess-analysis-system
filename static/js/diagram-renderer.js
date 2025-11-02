// Diagram Renderer - Client-side JS for rendering chess SVG diagrams
// Supports backend contract: { answer: string with [DIAGRAM_ID:uuid], diagram_positions: [{id, svg, caption}, ...] }
// Provides renderAnswerWithDiagrams(answer, diagramPositions, container) as the primary API.

function renderAnswerWithDiagrams(answer, diagramPositions, container) {
    try {
        if (!container) {
            container = document.getElementById('answer-content-container') || document.body;
        }

        // Build id -> { svg, caption }
        const byId = {};
        (diagramPositions || []).forEach(d => {
            if (d && d.id) byId[d.id] = { svg: d.svg || '', caption: d.caption || '' };
        });

        // Escape helper for captions
        const escHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text == null ? '' : String(text);
            return div.innerHTML;
        };

        // Replace placeholders with diagram blocks
        const replaced = String(answer || '').replace(/\[DIAGRAM_ID:([a-f0-9\-]+)\]/gi, (m, id) => {
            const entry = byId[id];
            if (!entry || !entry.svg) return '<div class="chess-diagram-error">Diagram not available</div>';
            const captionHtml = entry.caption ? `<div class="diagram-caption">${escHtml(entry.caption)}</div>` : '';
            return `
<div class="chess-diagram-container" style="margin:25px auto;max-width:400px;text-align:center;">
  <div class="chess-diagram" style="display:inline-block;">${entry.svg}</div>
  ${captionHtml}
</div>`;
        });

        container.innerHTML = replaced;
    } catch (err) {
        console.error('renderAnswerWithDiagrams failed:', err);
        if (container) container.innerHTML = '<p class="chess-diagram-error">Error rendering diagrams</p>';
    }
}

// Legacy helper retained for potential uses
function renderSvgToDiv(divId, svgString) {
    const container = document.getElementById(divId);
    if (!container) {
        console.error(`Diagram div not found: ${divId}`);
        return;
    }

    try {
        // Use DOMParser for safe SVG parsing
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(svgString, 'image/svg+xml');
        const svgElement = svgDoc.documentElement;

        // Check for parse errors
        if (svgElement.nodeName === 'parsererror') {
            throw new Error('SVG parse error: ' + svgElement.textContent);
        }

        // Set attributes if needed (e.g., width/height for responsiveness)
        svgElement.setAttribute('width', '100%');
        svgElement.setAttribute('height', 'auto');

        // Clear container and append the SVG
        container.innerHTML = '';
        container.appendChild(svgElement);
    } catch (error) {
        console.error(`Failed to render SVG for ${divId}:`, error);
        container.innerHTML = '<p>Error rendering diagram</p>';
    }
}

// Expose as global for page inline scripts
window.renderAnswerWithDiagrams = renderAnswerWithDiagrams;
