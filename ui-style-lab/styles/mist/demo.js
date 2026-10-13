(() => {
  const status = document.getElementById('neo-status');
  const say = text => { status.textContent = text; };
  const dial = document.querySelector('[data-mist-dial]');
  const deviceDialog = document.getElementById('device-dialog');
  const sceneDialog = document.getElementById('scene-dialog');
  const analyticsDialog = document.getElementById('analytics-dialog');
  let currentDevice = null;
  const deviceStates = new Map();
  document.addEventListener('mist-toggle', event => {
    const element = event.target;
    const checked = event.detail.checked;
    if (element.hasAttribute('data-climate-power')) {
      dial.setAttribute('aria-disabled', String(!checked));
      document.getElementById('climate-mode').textContent = checked ? 'Auto Cooling' : 'Standby';
      say(checked ? '空调已开启，可以调整温度。' : '空调已关闭，温控暂不可操作。');
    } else if (element.hasAttribute('data-scene')) {
      say(`${element.dataset.scene} ${checked ? '已激活' : '已关闭'}。`);
    } else if (element.getAttribute('aria-label') === '详情设备电源' && currentDevice) {
      deviceStates.set(currentDevice, checked);
      say(`${currentDevice} ${checked ? '已开启' : '已关闭'}（本地演示）。`);
    } else say(`${element.getAttribute('aria-label') || element.textContent.trim()}：${checked ? '已启用' : '已关闭'}。`);
  });
  document.addEventListener('mist-temperature-change', event => say(`温度已设为 ${event.detail.value}°C。`));
  document.addEventListener('click', event => {
    const target = event.target.closest?.('button');
    if (!target || target.disabled) return;
    if (target.hasAttribute('data-open-scene')) sceneDialog.showModal();
    if (target.hasAttribute('data-close-dialog')) target.closest('dialog').close();
    if (target.hasAttribute('data-open-analytics')) analyticsDialog.showModal();
    if (target.hasAttribute('data-device')) {
      currentDevice = target.dataset.device;
      document.getElementById('device-dialog-title').textContent = currentDevice;
      document.getElementById('device-dialog-description').textContent = `${target.dataset.usage} · 本地演示数据`;
      const power = deviceDialog.querySelector('.mist-switch');
      const on = deviceStates.get(currentDevice) !== false;
      power.setAttribute('aria-checked', String(on));
      power.querySelector('[data-switch-label]').textContent = on ? 'On' : 'Off';
      deviceDialog.showModal();
    }
    if (target.hasAttribute('data-see-scenes')) {
      const section = document.getElementById('extra-scenes');
      section.hidden = !section.hidden;
      target.setAttribute('aria-expanded', String(!section.hidden));
      target.textContent = section.hidden ? 'See All' : 'Hide';
    }
    if (target.matches('.neo-menu-trigger')) {
      const menu = document.getElementById('profile-options');
      menu.hidden = !menu.hidden;
      target.setAttribute('aria-expanded', String(!menu.hidden));
    }
    if (target.hasAttribute('data-profile-action')) {
      say(`${target.dataset.profileAction}：这是组件展示菜单，尚未连接账户服务。`);
      closeMenu();
    }
    if (target.hasAttribute('data-demo-action')) say(`已点击${target.dataset.demoAction}。`);
    if (target.hasAttribute('data-clear-search')) {
      const input = target.closest('form').querySelector('input');
      input.value = '';
      filterDevices('');
      input.focus();
    }
  });
  function closeMenu() {
    document.getElementById('profile-options').hidden = true;
    document.querySelector('.neo-menu-trigger').setAttribute('aria-expanded', 'false');
  }
  document.addEventListener('click', event => {
    if (!event.target.closest('.neo-greeting')) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !document.getElementById('profile-options').hidden) {
      closeMenu(); document.querySelector('.neo-menu-trigger').focus();
    }
  });
  document.getElementById('scene-form').addEventListener('submit', event => {
    event.preventDefault();
    const input = event.target.elements.sceneName;
    const name = input.value.trim();
    if (!name) { input.setCustomValidity('请输入场景名称。'); input.reportValidity(); return; }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'mist-button';
    button.dataset.toggle = '';
    button.setAttribute('aria-pressed', 'false');
    button.textContent = name;
    document.getElementById('extra-scenes').append(button);
    document.getElementById('scene-count').textContent = String(Number(document.getElementById('scene-count').textContent) + 1);
    event.target.reset();
    sceneDialog.close();
    say(`场景“${name}”已创建，可在 See All 中查看；刷新后恢复初始演示。`);
  });
  document.querySelector('[name="sceneName"]').addEventListener('input', event => event.target.setCustomValidity(''));
  const aliases = { 'Air Conditioner': '空调', 'Wi-Fi Router': '路由器 网络', 'Smart TV': '电视', 'Humidifier': '加湿器' };
  function filterDevices(query) {
    const keyword = query.trim().toLowerCase();
    let count = 0;
    document.querySelectorAll('[data-device]').forEach(row => {
      row.hidden = !`${row.dataset.device} ${aliases[row.dataset.device]}`.toLowerCase().includes(keyword);
      if (!row.hidden) count += 1;
    });
    document.getElementById('device-empty').hidden = count > 0;
    document.getElementById('device-search-count').textContent = keyword ? `匹配 ${count} 台设备，上方列表已更新。` : '搜索上方四台设备，支持中英文关键词。';
    say(keyword ? `搜索“${query}”：找到 ${count} 台设备。` : '设备筛选已清空。');
  }
  const search = document.querySelector('[data-device-search]');
  search.addEventListener('submit', event => { event.preventDefault(); filterDevices(search.elements.q.value); });
  search.elements.q.addEventListener('input', event => filterDevices(event.target.value));
  document.getElementById('volume').addEventListener('input', event => {
    document.getElementById('volume-value').value = `${event.target.value}%`;
  });
  document.addEventListener('mist-segment-change', event => {
    const values = { day: [60, '今日 · 40 kWh', 'Daily Usage'], week: [76, '本周 · 280 kWh', 'Weekly Usage'], month: [43, '本月 · 960 kWh', 'Monthly Usage'] };
    const [percent, caption, title] = values[event.detail.value];
    document.getElementById('usage-value').textContent = `${percent}%`;
    const progress = document.getElementById('usage-progress');
    progress.setAttribute('aria-valuenow', String(percent));
    progress.firstElementChild.style.setProperty('--mist-progress', `${percent}%`);
    document.getElementById('period-caption').textContent = `${caption}（演示数据）`;
    document.getElementById('analytics-period').textContent = title;
  });
})();
