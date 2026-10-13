(() => {
  const searchSelector = '.usl-metal-search';
  function updateClear(form) {
    const input = form.querySelector('.usl-metal-search__input');
    const clear = form.querySelector('.usl-metal-search__clear');
    if (input && clear) clear.hidden = !input.value;
  }
  document.querySelectorAll(searchSelector).forEach(updateClear);
  document.addEventListener('input', (event) => {
    const form = event.target.closest?.(searchSelector);
    if (form) updateClear(form);
  });
  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!form.matches(searchSelector)) return;
    event.preventDefault();
    const input = form.querySelector('.usl-metal-search__input');
    if (!input || input.disabled) return;
    form.dispatchEvent(new CustomEvent('usl-search', {
      bubbles: true, detail: { query: input.value.trim() }
    }));
  });
  document.addEventListener('click', (event) => {
    const clear = event.target.closest?.('.usl-metal-search__clear');
    if (clear && !clear.disabled) {
      const input = clear.closest(searchSelector).querySelector('.usl-metal-search__input');
      if (input && !input.disabled) {
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
      }
    }
    const toggle = event.target.closest?.('.usl-metal-button[data-usl-toggle]');
    if (toggle && !toggle.disabled) {
      const pressed = toggle.getAttribute('aria-pressed') !== 'true';
      toggle.setAttribute('aria-pressed', String(pressed));
      toggle.dispatchEvent(new CustomEvent('usl-button-toggle', {
        bubbles: true, detail: { pressed }
      }));
    }
  });
})();
