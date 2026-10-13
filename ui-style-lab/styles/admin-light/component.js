/* Demo interactions: no network, no API dependency. */
(() => {
  const root = document.getElementById('workspace');
  if (!root) return;
  let timer;
  function toast(message) { const el=root.querySelector('#toast'); el.textContent=message; el.hidden=false; clearTimeout(timer); timer=setTimeout(()=>el.hidden=true,3500); }
  document.querySelectorAll('[data-toast]').forEach(b=>b.addEventListener('click',()=>toast(b.dataset.toast)));
  document.querySelector('[data-notes]').addEventListener('click',()=>location.href='notes.md');
  document.querySelectorAll('[data-theme-choice]').forEach(b=>b.addEventListener('click',()=>{
    document.querySelectorAll('.usl-admin').forEach(el=>el.dataset.theme=b.dataset.themeChoice);
    document.querySelectorAll('[data-theme-choice]').forEach(el=>el.setAttribute('aria-pressed',String(el===b)));
  }));
  const destinations={'数据概览':null,'销售分析':'sales-section','订单管理':'orders-section','客户管理':'customers-section','工作日程':'schedule-section'};
  root.querySelectorAll('[data-nav]').forEach(b=>b.addEventListener('click',()=>{
    root.querySelectorAll('[data-nav]').forEach(el=>el.removeAttribute('aria-current')); b.setAttribute('aria-current','page');
    root.querySelector('#breadcrumb').textContent=b.dataset.nav;
    const target=destinations[b.dataset.nav];
    const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
    (target?root.querySelector('#'+target):root).scrollIntoView({behavior:reduce?'instant':'smooth',block:'start'});
    toast(target?'已定位到'+b.dataset.nav+'组件。':'已返回数据概览。');
  }));
  const rows=[...root.querySelectorAll('tbody tr')], search=root.querySelector('#order-search'), status=root.querySelector('#status-filter'), all=root.querySelector('#select-all');
  function updateSelection(){const visible=rows.filter(r=>!r.hidden);const checked=visible.filter(r=>r.querySelector('input').checked);all.checked=visible.length>0&&checked.length===visible.length;all.indeterminate=checked.length>0&&checked.length<visible.length;all.disabled=!visible.length;root.querySelector('#selection-count').textContent='已选择 '+rows.filter(r=>r.querySelector('input').checked).length+' 笔订单';}
  function filter(){let n=0; rows.forEach(r=>{r.hidden=!(r.dataset.search.toLowerCase().includes(search.value.trim().toLowerCase())&&(!status.value||r.dataset.search.includes(status.value)));if(!r.hidden)n++;});root.querySelector('#order-count').textContent=n+' 笔';root.querySelector('#empty').hidden=n>0;updateSelection();}
  search.addEventListener('input',filter);status.addEventListener('change',filter);rows.forEach(r=>r.querySelector('input').addEventListener('change',updateSelection));all.addEventListener('change',()=>{rows.filter(r=>!r.hidden).forEach(r=>r.querySelector('input').checked=all.checked);updateSelection();});
  root.querySelectorAll('[data-day]').forEach(b=>b.addEventListener('click',()=>{root.querySelectorAll('[data-day]').forEach(el=>el.setAttribute('aria-pressed',String(el===b)));root.querySelector('#event-name').textContent=b.dataset.day==='13'?'产品与销售周会':'业务进度同步';root.querySelector('#event-time').textContent='10 月 '+b.dataset.day+' 日 · 09:30 – 10:30';}));
  root.querySelector('#period').addEventListener('change',e=>{const q=e.target.value==='quarter';root.querySelector('#income-total').textContent=q?'¥1,928,420':'¥2,846,520';root.querySelector('#page-subtitle').textContent=q?'已切换至第三季度演示数据；下方保留组件示例。':'欢迎回来，Jamie。这里是今天的业务概况。';toast('已切换演示周期。');});
  root.querySelector('#export').addEventListener('click',()=>{
    const visible=rows.filter(r=>!r.hidden), selected=visible.filter(r=>r.querySelector('input').checked), data=selected.length?selected:visible;
    const csv='\ufeff客户,订单,金额,状态,日期\r\n'+data.map(r=>[r.cells[1].querySelector('.usl-admin-customer div').childNodes[0].textContent.trim(),r.cells[1].querySelector('small').textContent,...[...r.cells].slice(2).map(c=>c.innerText)].map(c=>'"'+c.replace(/\n/g,' ').replace(/"/g,'""')+'"').join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='clearwork-orders.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('已导出 '+data.length+' 笔演示订单。');
  });
})();
