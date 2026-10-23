
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  const toggle = document.getElementById('menuToggle'), overlay = document.getElementById('sidebarOverlay');
  const sidebar=document.getElementById('adminSidebar'); const mobile=matchMedia('(max-width:760px)');
  const setMenu = open => {if(sidebar)sidebar.inert=mobile.matches&&!open; document.body.classList.toggle('menu-open', open); if(toggle) toggle.setAttribute('aria-expanded',String(open)); if(overlay) overlay.hidden=!open;};
  if(sidebar)sidebar.inert=mobile.matches; mobile.addEventListener('change',()=>setMenu(false));
  toggle?.addEventListener('click', () => setMenu(!document.body.classList.contains('menu-open')));
  overlay?.addEventListener('click', () => setMenu(false));
  document.addEventListener('keydown', e => {if(e.key==='Escape')setMenu(false);});
  document.querySelectorAll('.flash-dismiss').forEach(b => b.addEventListener('click', () => b.closest('.flash-message').remove()));
  document.querySelector('[data-password-toggle]')?.addEventListener('click', e => {
    const input=document.getElementById('password'); const show=input.type==='password'; input.type=show?'text':'password'; e.currentTarget.textContent=show?'Ẩn':'Hiện'; e.currentTarget.setAttribute('aria-pressed',String(show));
  });
  const all=document.getElementById('selectAllQuotes'), boxes=[...document.querySelectorAll('[name="quote_ids"]')], count=document.getElementById('selectedCount');
  const update=()=>{const selected=boxes.filter(b=>b.checked).length; if(count) count.textContent=selected; if(all){all.checked=selected>0&&selected===boxes.length;all.indeterminate=selected>0&&selected<boxes.length;}};
  all?.addEventListener('change',()=>{boxes.forEach(b=>b.checked=all.checked);update();});boxes.forEach(b=>b.addEventListener('change',update));
  document.getElementById('bulkQuoteForm')?.addEventListener('submit', e => {if(!boxes.some(b=>b.checked)){e.preventDefault();alert('Vui lòng chọn ít nhất một báo giá.');}else if(!confirm('Cập nhật trạng thái cho các báo giá đã chọn?'))e.preventDefault();});
  document.querySelectorAll('form[method="POST"],form[method="post"]').forEach(form => form.addEventListener('submit',e=>{if(e.defaultPrevented||!form.checkValidity())return;const button=e.submitter;if(button){setTimeout(()=>{button.disabled=true;button.setAttribute('aria-busy','true');},0);}}));
  const productSearch=document.getElementById('productSearch');
  productSearch?.addEventListener('input',()=>{const term=productSearch.value.toLocaleLowerCase('vi'); document.querySelectorAll('[data-product-row]').forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase('vi').includes(term));});
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('[data-print-quote]')?.addEventListener('click', () => window.print());
  document.querySelectorAll('[data-copy-text]').forEach(button => button.addEventListener('click', async () => {
    const feedback = document.getElementById('copyFeedback');
    try { await navigator.clipboard.writeText(button.dataset.copyText); if(feedback) feedback.textContent='Đã sao chép số điện thoại.'; }
    catch { if(feedback) feedback.textContent='Không thể sao chép tự động. Bạn có thể chọn số điện thoại để sao chép.'; }
  }));
  const form=document.querySelector('[data-unsaved-form]');
  if(form){
    let dirty=false;
    form.addEventListener('input',()=>{dirty=true;});
    form.addEventListener('submit', e=>{if(!e.defaultPrevented && form.checkValidity())dirty=false;});
    window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  }
});
