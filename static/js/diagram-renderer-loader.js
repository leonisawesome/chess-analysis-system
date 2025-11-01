/* diagram-renderer-loader.js
   Ensures fixed renderer loads after page scripts.
*/
(function(){
  function loadPatch(){
    const script = document.createElement('script');
    script.src = '/static/js/diagram-renderer-fixed.js';
    script.async = false;
    document.head.appendChild(script);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadPatch);
  } else {
    loadPatch();
  }
})();
