(() => {
  // Load once after the markup, or use <script defer>. No external dependencies.
  const selector = '.usl-embossed-switch[role="switch"]';
  document.addEventListener('click', (event) => {
    const button = event.target.closest?.(selector);
    if (!button || button.disabled || button.hasAttribute('data-static')) return;
    const checked = button.getAttribute('aria-checked') !== 'true';
    button.setAttribute('aria-checked', String(checked));
    button.dispatchEvent(new CustomEvent('usl-switch-change', {
      bubbles: true,
      detail: { checked }
    }));
  });
})();
