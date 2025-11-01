/**
 * Chess Diagram Renderer
 *
 * Safely renders chess diagrams by parsing [DIAGRAM_ID:uuid] markers
 * and replacing them with sanitized SVG elements from the backend.
 *
 * Security: Uses DOMParser to safely parse SVGs without executing scripts
 * Accessibility: Adds ARIA labels and title elements for screen readers
 *
 * Created: 2025-10-31
 * Part of: Chess RAG System diagram rendering fix
 */

/**
 * Renders answer text with embedded chess diagrams
 * @param {string} answer - Answer text with [DIAGRAM_ID:uuid] markers
 * @param {Array} diagramPositions - Array of {id, fen, svg} objects
 * @param {HTMLElement} container - Container element to render into
 */
function renderAnswerWithDiagrams(answer, diagramPositions, container) {
  console.log('[DiagramRenderer] Starting render...');
  console.log('[DiagramRenderer] Answer length:', answer.length);
  console.log('[DiagramRenderer] Diagram positions:', diagramPositions.length);

  // Create diagram map for O(1) lookups
  const diagramMap = {};
  diagramPositions.forEach(pos => {
    diagramMap[pos.id] = pos;
  });
  console.log('[DiagramRenderer] Diagram map created with', Object.keys(diagramMap).length, 'entries');

  // Regex to find [DIAGRAM_ID:uuid] markers
  const markerRegex = /\[DIAGRAM_ID:([a-f0-9-]+)\]/ig;

  // Create DocumentFragment to avoid multiple reflows
  const frag = document.createDocumentFragment();
  let lastIndex = 0;
  let match;
  let diagramCount = 0;

  console.log('[DiagramRenderer] Parsing markers...');

  while ((match = markerRegex.exec(answer)) !== null) {
    const idx = match.index;
    const marker = match[0];
    const uuid = match[1];

    console.log('[DiagramRenderer] Found marker at position', idx, '- UUID:', uuid);

    // Append text before marker as text node
    if (idx > lastIndex) {
      const textNode = document.createTextNode(answer.slice(lastIndex, idx));
      frag.appendChild(textNode);
    }

    // Create placeholder element (safe - no SVG yet)
    const placeholder = document.createElement('div');
    placeholder.className = 'chess-diagram-placeholder';
    placeholder.setAttribute('data-diagram-id', uuid);
    placeholder.setAttribute('role', 'img');
    placeholder.setAttribute('aria-label', `Chess diagram ${uuid} - loading`);
    placeholder.textContent = 'Loading diagram...';
    frag.appendChild(placeholder);

    diagramCount++;
    lastIndex = idx + marker.length;
  }

  // Append remaining text
  if (lastIndex < answer.length) {
    frag.appendChild(document.createTextNode(answer.slice(lastIndex)));
  }

  console.log('[DiagramRenderer] Found', diagramCount, 'diagram markers');

  // Clear container and attach fragment
  container.innerHTML = '';
  container.appendChild(frag);

  // Replace placeholders with sanitized SVGs
  const placeholders = container.querySelectorAll('.chess-diagram-placeholder');
  console.log('[DiagramRenderer] Processing', placeholders.length, 'placeholders...');

  let successCount = 0;
  let errorCount = 0;

  placeholders.forEach((placeholder, index) => {
    const uuid = placeholder.getAttribute('data-diagram-id');
    const diagram = diagramMap[uuid];

    if (!diagram || !diagram.svg) {
      console.warn('[DiagramRenderer] Diagram not found for UUID:', uuid);
      placeholder.textContent = '[Diagram not available]';
      placeholder.className = 'chess-diagram-error';
      errorCount++;
      return;
    }

    console.log('[DiagramRenderer] Processing diagram', index + 1, '/', placeholders.length, '- UUID:', uuid);

    // Sanitize and parse SVG
    const sanitizedSvg = sanitizeSvgStringToElement(diagram.svg, diagram.fen || '');

    if (sanitizedSvg) {
      // Create wrapper for styling
      const wrapper = document.createElement('div');
      wrapper.className = 'chess-diagram';
      wrapper.setAttribute('role', 'img');
      wrapper.setAttribute('aria-label', `Chess diagram: ${diagram.fen || 'unknown position'}`);

      // Add SVG
      wrapper.appendChild(sanitizedSvg);

      // Add descriptive caption (or fallback to FEN)
      if (diagram.caption) {
        const caption = document.createElement('div');
        caption.className = 'diagram-caption';
        caption.textContent = diagram.caption;
        wrapper.appendChild(caption);
      } else if (diagram.fen) {
        // Fallback to FEN if no caption available
        const fenCaption = document.createElement('div');
        fenCaption.className = 'diagram-caption';
        fenCaption.textContent = diagram.fen;
        wrapper.appendChild(fenCaption);
      }

      // Replace placeholder
      placeholder.parentNode.replaceChild(wrapper, placeholder);
      successCount++;
      console.log('[DiagramRenderer] ✓ Successfully rendered diagram', index + 1);
    } else {
      console.error('[DiagramRenderer] Failed to sanitize SVG for UUID:', uuid);
      placeholder.textContent = '[Diagram failed to render]';
      placeholder.className = 'chess-diagram-error';
      errorCount++;
    }
  });

  console.log('[DiagramRenderer] Rendering complete:');
  console.log('[DiagramRenderer]   Success:', successCount);
  console.log('[DiagramRenderer]   Errors:', errorCount);
  console.log('[DiagramRenderer]   Total:', successCount + errorCount);
}

/**
 * Sanitizes SVG string and returns a safe DOM element
 * Removes: <script>, <foreignObject>, event handlers, javascript: URIs
 * @param {string} svgString - Raw SVG string from backend
 * @param {string} fallbackTitle - Title for accessibility
 * @returns {SVGElement|null} - Sanitized SVG element or null on error
 */
function sanitizeSvgStringToElement(svgString, fallbackTitle = '') {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgString, 'image/svg+xml');
    const svg = doc.documentElement;

    if (!svg || svg.nodeName.toLowerCase() !== 'svg') {
      console.error('[Sanitizer] Invalid SVG: root element is not <svg>');
      return null;
    }

    // Remove forbidden tags that could execute scripts
    const forbiddenTags = ['script', 'foreignObject', 'iframe', 'object', 'embed', 'link', 'meta'];
    forbiddenTags.forEach(tag => {
      const nodes = svg.querySelectorAll(tag);
      if (nodes.length > 0) {
        console.warn('[Sanitizer] Removed', nodes.length, tag, 'tag(s)');
      }
      nodes.forEach(n => n.remove());
    });

    // Remove dangerous attributes
    const walker = document.createTreeWalker(svg, NodeFilter.SHOW_ELEMENT, null, false);
    const attrWhitelist = new Set([
      'width', 'height', 'viewBox', 'xmlns', 'x', 'y', 'transform', 'd',
      'fill', 'stroke', 'stroke-width', 'cx', 'cy', 'r', 'rx', 'ry',
      'points', 'preserveAspectRatio', 'class', 'style', 'id', 'role', 'aria-label'
    ]);

    let node;
    let removedCount = 0;

    while ((node = walker.nextNode())) {
      const attrs = Array.from(node.attributes || []);
      attrs.forEach(attr => {
        const name = attr.name;
        const value = attr.value || '';

        // Remove event handlers (on*)
        if (name.startsWith('on')) {
          node.removeAttribute(name);
          removedCount++;
          return;
        }

        // Remove javascript: URIs
        if ((name === 'href' || name === 'xlink:href' || name === 'style') &&
            /javascript\s*:/i.test(value)) {
          node.removeAttribute(name);
          removedCount++;
          return;
        }

        // Allow data-* and aria-* attributes
        if (name.startsWith('data-') || name.startsWith('aria-')) {
          return;
        }

        // Remove non-whitelisted attributes
        if (!attrWhitelist.has(name) && !name.includes(':')) {
          node.removeAttribute(name);
          removedCount++;
        }
      });
    }

    if (removedCount > 0) {
      console.warn('[Sanitizer] Removed', removedCount, 'dangerous attribute(s)');
    }

    // Add accessibility title
    if (!svg.querySelector('title') && fallbackTitle) {
      const title = doc.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = fallbackTitle;
      svg.insertBefore(title, svg.firstChild);
    }

    // Import into main document
    return document.importNode(svg, true);

  } catch (err) {
    console.error('[Sanitizer] Error parsing/sanitizing SVG:', err);
    return null;
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { renderAnswerWithDiagrams, sanitizeSvgStringToElement };
}
