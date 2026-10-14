(() => {
  const status = document.getElementById('white-status');
  document.addEventListener('mist-toggle', event => {
    status.textContent = `${event.target.getAttribute('aria-label')}：${event.detail.checked ? '已按下，保持内凹' : '已恢复凸起'}。`;
  });
  document.querySelectorAll('.white-control-card form').forEach(form => {
    form.addEventListener('submit', event => {
      event.preventDefault();
      const query = form.elements.q.value.trim();
      status.textContent = `${form.getAttribute('aria-label')}：${query ? `输入了“${query}”` : '请输入关键词'}（材质预览，未连接业务搜索）。`;
    });
  });
})();
