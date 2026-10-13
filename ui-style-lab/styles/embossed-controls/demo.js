(() => {
  const items = [
    { name: '立体开关', description: '灰色与橙色凹槽，金属纹理滑块。' },
    { name: '浮雕按钮', description: '银灰按钮、橙色主按钮与圆形电源按钮。' },
    { name: '凹槽搜索栏', description: '内凹输入区，配圆形提交按钮。' },
    { name: '纹理滑块', description: '细密浮雕纹理，柔和金属边缘。' }
  ];
  const feedback = document.getElementById('feedback');
  const results = document.getElementById('results');
  const list = document.getElementById('results-list');
  document.addEventListener('usl-search', (event) => {
    const query = event.detail.query;
    if (!query) {
      feedback.textContent = '请输入关键词后搜索。';
      results.hidden = true;
      list.replaceChildren();
      return;
    }
    const matches = items.filter(item => `${item.name} ${item.description}`.includes(query));
    list.replaceChildren();
    for (const item of matches) {
      const row = document.createElement('li');
      row.textContent = `${item.name} — ${item.description}`;
      list.append(row);
    }
    results.hidden = false;
    document.getElementById('empty-result').hidden = matches.length > 0;
    feedback.textContent = `“${query}” · 找到 ${matches.length} 个本地示例，下方可查看。`;
  });
  document.addEventListener('input', (event) => {
    if (event.target.matches('.usl-metal-search__input') && !event.target.value) {
      feedback.textContent = '已清空，输入关键词可重新搜索。';
      results.hidden = true;
      list.replaceChildren();
    }
  });
  document.addEventListener('usl-button-toggle', (event) => {
    feedback.textContent = event.detail.pressed ? '电源按钮：已按下。' : '电源按钮：已复位。';
  });
  document.addEventListener('click', (event) => {
    const button = event.target.closest?.('[data-demo-action]');
    if (button) feedback.textContent = `已点击“${button.dataset.demoAction}”。`;
  });
})();
