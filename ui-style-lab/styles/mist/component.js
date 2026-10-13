(() => {
  function emit(target, name, detail) {
    target.dispatchEvent(new CustomEvent(name, { bubbles: true, detail }));
  }
  document.addEventListener('click', event => {
    const toggle = event.target.closest?.('.mist-switch, [data-toggle], [data-scene]');
    if (toggle && !toggle.disabled) {
      const attribute = toggle.matches('.mist-switch') ? 'aria-checked' : 'aria-pressed';
      const checked = toggle.getAttribute(attribute) !== 'true';
      toggle.setAttribute(attribute, String(checked));
      const label = toggle.querySelector('[data-switch-label]');
      if (label) label.textContent = checked ? 'On' : 'Off';
      emit(toggle, 'mist-toggle', { checked });
    }
    const segment = event.target.closest?.('.mist-segment');
    if (segment && !segment.disabled) {
      segment.closest('.mist-segments').querySelectorAll('.mist-segment').forEach(button => {
        button.setAttribute('aria-pressed', String(button === segment));
      });
      emit(segment, 'mist-segment-change', { value: segment.dataset.period || segment.textContent.trim() });
    }
  });
  document.querySelectorAll('[data-mist-dial]').forEach(dial => {
    const min = Number(dial.getAttribute('aria-valuemin'));
    const max = Number(dial.getAttribute('aria-valuemax'));
    function render(value, notify = false) {
      const current = Math.max(min, Math.min(max, Math.round(value)));
      const fraction = (current - min) / (max - min);
      const angle = Math.PI + fraction * Math.PI;
      dial.setAttribute('aria-valuenow', String(current));
      dial.setAttribute('aria-valuetext', `${current} 摄氏度`);
      dial.querySelector('[data-dial-value]').textContent = `${current}°`;
      dial.querySelectorAll('[data-tick]').forEach(tick => tick.classList.toggle('is-active', Number(tick.dataset.tick) <= fraction));
      const needle = dial.querySelector('[data-needle]');
      for (const [key, value] of Object.entries({ x1: 190 + Math.cos(angle) * 129, y1: 201 + Math.sin(angle) * 129, x2: 190 + Math.cos(angle) * 158, y2: 201 + Math.sin(angle) * 158 })) needle.setAttribute(key, value);
      const tip = dial.querySelector('[data-tip]');
      tip.setAttribute('cx', 190 + Math.cos(angle) * 162);
      tip.setAttribute('cy', 201 + Math.sin(angle) * 162);
      if (notify) emit(dial, 'mist-temperature-change', { value: current });
    }
    render(Number(dial.getAttribute('aria-valuenow')));
    dial.addEventListener('keydown', event => {
      if (dial.getAttribute('aria-disabled') === 'true') return;
      let value = Number(dial.getAttribute('aria-valuenow'));
      if (['ArrowRight', 'ArrowUp'].includes(event.key)) value += 1;
      else if (['ArrowLeft', 'ArrowDown'].includes(event.key)) value -= 1;
      else if (event.key === 'Home') value = min;
      else if (event.key === 'End') value = max;
      else if (event.key === 'PageUp') value += 2;
      else if (event.key === 'PageDown') value -= 2;
      else return;
      event.preventDefault();
      render(value, true);
    });
    function pointerValue(event) {
      const bounds = dial.getBoundingClientRect();
      const x = (event.clientX - bounds.left) * 380 / bounds.width - 190;
      const y = (event.clientY - bounds.top) * 216 / bounds.height - 201;
      let angle = Math.atan2(Math.min(y, 0), x);
      if (x < 0 && angle === Math.PI) angle = -Math.PI;
      render(min + (angle + Math.PI) / Math.PI * (max - min), true);
    }
    dial.addEventListener('pointerdown', event => {
      if (dial.getAttribute('aria-disabled') === 'true' || event.button !== 0) return;
      dial.focus();
      dial.setPointerCapture(event.pointerId);
      pointerValue(event);
    });
    dial.addEventListener('pointermove', event => {
      if (dial.hasPointerCapture(event.pointerId) && dial.getAttribute('aria-disabled') !== 'true') pointerValue(event);
    });
    dial.addEventListener('pointerup', event => {
      if (dial.hasPointerCapture(event.pointerId)) dial.releasePointerCapture(event.pointerId);
    });
  });
})();
