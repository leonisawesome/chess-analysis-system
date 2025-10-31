# Diagram Rendering Fix - Integration Guide

## What Was Done
Created `static/js/diagram-renderer.js` with production-ready diagram rendering logic.

## How to Integrate

### Option 1: If JavaScript is in templates/index.html (inline)

1. Add script tag in `<head>` section:
```html
<script src="{{ url_for('static', filename='js/diagram-renderer.js') }}"></script>
```

2. Find the existing fetch() call to /query endpoint and modify the response handler:

**BEFORE:**
```javascript
fetch('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: userQuery })
})
.then(response => response.json())
.then(data => {
    document.getElementById('answer').textContent = data.answer;
    // ... handle sources, etc.
});
```

**AFTER:**
```javascript
fetch('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: userQuery })
})
.then(response => response.json())
.then(data => {
    const answerContainer = document.getElementById('answer');
    renderAnswerWithDiagrams(data.answer, data.diagram_positions, answerContainer);
    // ... handle sources, etc.
});
```

### Option 2: If JavaScript is in separate static/js/ file

1. Add import at top of the file:
```javascript
// Import diagram renderer (if using modules)
// OR just include both scripts in HTML in correct order
```

2. Modify fetch() response handler as shown in Option 1

### Option 3: If structure is different

Please examine your templates/index.html and provide:
- Location of the element that displays the answer
- Current code that handles the /query response
- Any existing JavaScript file paths

## Testing

After integration:
1. Start Flask: `python3 app.py`
2. Open browser to http://127.0.0.1:5001
3. Enter query: "Explain the Italian Game"
4. Open browser console (F12)
5. Check for "[DiagramRenderer]" log messages
6. Verify chess boards appear instead of [DIAGRAM_ID:xxx] text

## Rollback

If anything breaks:
```bash
git checkout main
git reset --hard HEAD
```

Then restore from backup branch.
