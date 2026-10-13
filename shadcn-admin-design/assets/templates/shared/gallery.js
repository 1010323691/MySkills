(() => {
  const templates=window.ADMIN_TEMPLATES.templates;
  let selected=null,timer;
  try{selected=localStorage.getItem('admin-template-selection');}catch{}
  const label={overview:'仪表盘',orders:'列表',charts:'图表',components:'小组件',settings:'表单'};
  function render(){const q=document.getElementById('search').value.trim().toLowerCase(),mode=document.getElementById('mode').value;
    const list=templates.filter(t=>(mode==='all'||t.mode===mode)&&[t.name,t.id,t.summary,...t.use_cases].join(' ').toLowerCase().includes(q));
    document.getElementById('result-count').textContent=`${list.length} 组风格 · 每组包含 5 个完整视图与常用后台组件`;
    document.getElementById('empty').hidden=list.length>0;
    document.getElementById('catalog').innerHTML=list.map(t=>`<article class="template-card"><a href="${t.id}/index.html" class="preview-link" aria-label="打开${t.name}仪表盘"><img src="previews/${t.id}.png" alt="${t.name}仪表盘实际渲染预览" width="1440" height="1050" loading="lazy"><span class="preview-number">${String(templates.indexOf(t)+1).padStart(2,'0')} / 06</span></a><div class="card-info"><div class="card-title"><div><h3>${t.name}</h3><div class="card-english">${t.english}</div></div><div class="swatches" aria-label="配色 ${t.primary}">${['primary','secondary','bg'].map(k=>`<span class="swatch" style="background:${t.tokens[k]}" title="${k}: ${t.tokens[k]}"></span>`).join('')}</div></div><p class="summary">${t.summary}</p><div class="tags"><span>${t.mode==='dark'?'深色':'浅色'}</span><span>${t.density}密度</span>${t.use_cases.map(s=>`<span>${s}</span>`).join('')}</div><nav class="view-links" aria-label="${t.name}页面">${Object.entries(label).map(([id,l])=>`<a href="${t.id}/index.html#${id}">${l} ↗</a>`).join('')}</nav><div class="card-actions"><a class="view-button" href="${t.id}/index.html">打开完整模板 →</a><button class="choose" data-id="${t.id}" aria-pressed="${selected===t.id}">${selected===t.id?'已选此风格':'选择这组风格'}</button></div></div></article>`).join('');
  }
  function selection(scroll=false){const theme=templates.find(t=>t.id===selected);const box=document.getElementById('selection');box.hidden=!theme;if(!theme)return;document.getElementById('selected-name').textContent=theme.name;document.getElementById('selection-text').value=`我选择 ${theme.name}（${theme.id}），请基于它继续了解我的需求、主色调和页面范围，生成具体效果图后等我确认再实施。`;if(scroll)box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});}
  document.getElementById('catalog').addEventListener('click',e=>{const button=e.target.closest('[data-id]');if(!button)return;selected=button.dataset.id;try{localStorage.setItem('admin-template-selection',selected);}catch{}render();selection(true);});
  document.getElementById('search').oninput=render;document.getElementById('mode').onchange=render;
  document.getElementById('copy-selection').onclick=async()=>{const input=document.getElementById('selection-text');let message;try{await navigator.clipboard.writeText(input.value);message='已复制，可粘贴到对话中';}catch{input.focus();input.select();message='已选中说明，请按 Ctrl+C 或长按复制';}const toast=document.getElementById('toast');toast.textContent=message;toast.hidden=false;clearTimeout(timer);timer=setTimeout(()=>toast.hidden=true,3500);};
  render();selection();
})();
