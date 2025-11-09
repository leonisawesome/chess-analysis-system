/* diagram-renderer-fixed.js
   Emergency patch to fix SVG rendering.
   Properly injects diagram.svg into DOM instead of rendering caption text.
*/
(function(){
  console.log('🔧 diagram-renderer-fixed.js loading...');

  // Safe SVG sanitizer
  function sanitizeSvgElement(svg) {
    if (!svg || svg.nodeName.toLowerCase() !== 'svg') return null;

    // Remove dangerous elements
    const forbidden = ['script', 'foreignObject', 'iframe', 'object', 'embed'];
    forbidden.forEach(tag => {
      const nodes = svg.querySelectorAll(tag);
      nodes.forEach(n => n.parentNode && n.parentNode.removeChild(n));
    });

    // Remove dangerous attributes
    const walker = document.createTreeWalker(svg, NodeFilter.SHOW_ELEMENT);
    let node;
    while ((node = walker.nextNode())) {
      const attrs = Array.from(node.attributes || []);
      attrs.forEach(attr => {
        const name = attr.name;
        const val = attr.value || '';
        if (name.startsWith('on')) {
          node.removeAttribute(name);
        }
        if (/javascript\s*:/.test(val)) {
          node.removeAttribute(name);
        }
      });
    }

    return svg;
  }

  // Parse SVG string to DOM element
  function parseSvgString(svgString) {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(svgString, 'image/svg+xml');
      const svg = doc.documentElement;

      if (!svg || svg.nodeName.toLowerCase() !== 'svg') {
        console.error('Invalid SVG:', svgString.substring(0, 100));
        return null;
      }

      const clean = sanitizeSvgElement(svg);
      if (!clean) return null;

      return document.importNode(clean, true);
    } catch (e) {
      console.error('SVG parse error:', e);
      return null;
    }
  }

  // Render interactive chessboard from FEN
  function renderChessboard(fen, containerId) {
    try {
      const board = Chessboard(containerId, {
        position: fen,
        draggable: false,
        dropOffBoard: 'trash',
        sparePieces: false,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
      });
      return board;
    } catch (e) {
      console.error('Failed to render chessboard:', e);
      return null;
    }
  }

  // Main rendering function - replaces global
  window.renderAnswerWithDiagrams = function(answer, diagramPositions, container) {
    console.log('🎨 renderAnswerWithDiagrams called');
    console.log('  Markers in text:', (answer.match(/\[DIAGRAM_ID:[^\]]+\]/g) || []).length);
    console.log('  Diagrams available:', diagramPositions?.length || 0);

    // Find container
    if (!container) {
      container = document.querySelector('#answer') ||
                  document.querySelector('.answer') ||
                  document.querySelector('#response') ||
                  document.body;
    }

    // Build diagram map
    const diagramMap = {};
    (diagramPositions || []).forEach(d => {
      if (d && d.id) diagramMap[d.id] = d;
    });

    // Parse markers and build DOM
    const markerRegex = /\[DIAGRAM_ID:([^\]]+)\]/g;
    let lastIndex = 0;
    const frag = document.createDocumentFragment();
    let match;

    while ((match = markerRegex.exec(answer)) !== null) {
      const idx = match.index;
      const uuid = match[1];

      // Add text before marker
      if (idx > lastIndex) {
        const textNode = document.createTextNode(answer.slice(lastIndex, idx));
        frag.appendChild(textNode);
      }

      // Create diagram placeholder
      const placeholder = document.createElement('div');
      placeholder.className = 'diagram-placeholder';
      placeholder.setAttribute('data-diagram-id', uuid);

      const diagram = diagramMap[uuid];
      if (diagram && diagram.caption) {
        placeholder.textContent = diagram.caption; // Temporary
      } else {
        placeholder.textContent = 'Loading diagram...';
      }

      frag.appendChild(placeholder);
      lastIndex = idx + match[0].length;
    }

    // Add remaining text
    if (lastIndex < answer.length) {
      frag.appendChild(document.createTextNode(answer.slice(lastIndex)));
    }

    // Replace container content
    container.innerHTML = '';
    container.appendChild(frag);

    // Now replace placeholders with actual diagrams (chessboards or SVGs)
    const placeholders = container.querySelectorAll('.diagram-placeholder');
    console.log('  Replacing', placeholders.length, 'placeholders with diagrams...');

    let successCount = 0;
    placeholders.forEach(ph => {
      const id = ph.getAttribute('data-diagram-id');
      const diagram = diagramMap[id];

      if (!diagram) {
        console.warn('  ⚠️ No diagram data for ID:', id);
        ph.classList.add('diagram-missing');
        return;
      }

      // Create wrapper with caption
      const wrapper = document.createElement('div');
      wrapper.className = 'chess-diagram-container';
      wrapper.style.margin = '20px 0';
      wrapper.style.textAlign = 'center';

      // Check if we have FEN - render interactive chessboard
      if (diagram.fen) {
        console.log('  ♟️ Rendering interactive chessboard for:', id);

        const boardDiv = document.createElement('div');
        const boardId = 'board-' + id;
        boardDiv.id = boardId;
        boardDiv.style.width = '400px';
        boardDiv.style.margin = '0 auto';
        wrapper.appendChild(boardDiv);

        // Add caption below
        if (diagram.caption) {
          const caption = document.createElement('p');
          caption.className = 'diagram-caption';
          caption.style.fontStyle = 'italic';
          caption.style.marginTop = '10px';
          caption.style.color = '#666';
          caption.textContent = diagram.caption;
          wrapper.appendChild(caption);
        }

        // Replace placeholder first, then render board
        ph.parentNode.replaceChild(wrapper, ph);

        // Render chessboard after DOM insertion
        renderChessboard(diagram.fen, boardId);
        successCount++;
        console.log('  ✅ Rendered interactive board for:', id);
      }
      // Fallback to SVG if no FEN
      else {
        const svgString = diagram.svg || diagram.svg_string || diagram.image;
        if (!svgString) {
          console.warn('  ⚠️ No FEN or SVG for ID:', id);
          return;
        }

        const svgEl = parseSvgString(svgString);
        if (svgEl) {
          const diagramDiv = document.createElement('div');
          diagramDiv.className = 'chess-diagram';
          diagramDiv.appendChild(svgEl);
          wrapper.appendChild(diagramDiv);

          // Add caption below
          if (diagram.caption) {
            const caption = document.createElement('p');
            caption.className = 'diagram-caption';
            caption.style.fontStyle = 'italic';
            caption.style.marginTop = '10px';
            caption.textContent = diagram.caption;
            wrapper.appendChild(caption);
          }

          // Replace placeholder
          ph.parentNode.replaceChild(wrapper, ph);
          successCount++;
          console.log('  ✅ Rendered SVG for:', id);
        } else {
          console.error('  ❌ Failed to parse SVG for ID:', id);
          ph.classList.add('diagram-parse-failed');
        }
      }
    });

    console.log('✅ Rendered', successCount, 'of', placeholders.length, 'diagrams');
  };

  console.log('✅ diagram-renderer-fixed.js loaded successfully');
})();
