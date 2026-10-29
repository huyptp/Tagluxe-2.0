
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
  const bulkForm=document.getElementById('bulkQuoteForm');
  const bulkStatus=bulkForm?.querySelector('select[name="status"]'), bulkButton=bulkForm?.querySelector('button[type="submit"],button:not([type])');
  const update=()=>{const selected=boxes.filter(b=>b.checked).length;
    boxes.forEach(b=>b.closest('tr')?.classList.toggle('selected-row',b.checked));
    if(bulkButton){bulkButton.disabled=selected===0||!bulkStatus?.value;bulkButton.textContent=selected?'Cập nhật '+selected+' báo giá':'Chọn báo giá để cập nhật';}
 if(count) count.textContent=selected; if(all){all.checked=selected>0&&selected===boxes.length;all.indeterminate=selected>0&&selected<boxes.length;}};
  all?.addEventListener('change',()=>{boxes.forEach(b=>b.checked=all.checked);update();});boxes.forEach(b=>b.addEventListener('change',update));bulkStatus?.addEventListener('change',update);update();
  document.getElementById('bulkQuoteForm')?.addEventListener('submit', e => {if(!boxes.some(b=>b.checked)){e.preventDefault();alert('Vui lòng chọn ít nhất một báo giá.');}else if(!confirm('Cập nhật trạng thái cho các báo giá đã chọn?'))e.preventDefault();});
  document.querySelectorAll('form[method="POST"],form[method="post"]').forEach(form => form.addEventListener('submit',e=>{if(e.defaultPrevented||!form.checkValidity())return;const button=e.submitter;if(button){setTimeout(()=>{button.disabled=true;button.setAttribute('aria-busy','true');},0);}}));
  const productSearch=document.getElementById('productSearch');
  productSearch?.addEventListener('input',()=>{const term=productSearch.value.toLocaleLowerCase('vi'); document.querySelectorAll('[data-product-row]').forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase('vi').includes(term));});
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('[data-print-quote]')?.addEventListener('click', () => window.print());
  document.querySelectorAll('[data-copy-text]').forEach(button => button.addEventListener('click', async () => {
    let feedback = document.getElementById('copyFeedback');if(!feedback){feedback=document.createElement('div');feedback.id='copyFeedback';feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');document.body.append(feedback);}feedback.classList.add('feedback-toast');clearTimeout(feedback._timer);
    try { await navigator.clipboard.writeText(button.dataset.copyText); if(feedback) feedback.textContent='Đã sao chép số điện thoại.'; }
    catch { if(feedback) feedback.textContent='Không thể sao chép tự động. Bạn có thể chọn số điện thoại để sao chép.'; }
    feedback._timer=setTimeout(()=>{feedback.textContent='';},4500);
  }));
  const form=document.querySelector('[data-unsaved-form]');
  if(form){
    let dirty=false;
    const savebar=form.querySelector('.customer-savebar strong');
    const indicator=document.createElement('span');indicator.className='save-indicator';indicator.setAttribute('role','status');indicator.setAttribute('aria-live','polite');savebar?.append(indicator);
    const markDirty=()=>{dirty=true;indicator.textContent=' · Chưa lưu';};
    form.addEventListener('input',markDirty);form.addEventListener('change',markDirty);
    form.addEventListener('submit', e=>{if(!e.defaultPrevented && form.checkValidity())dirty=false;});
    window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  }
});

// Status is always readable in text; color is supplementary.
document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('.badge,.customer-state').forEach(el=>{el.dataset.status=el.textContent.trim();});
 document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!e.target.closest('input,textarea,select,[contenteditable]')){const search=document.getElementById('quickCustomerSearch');if(search&&search.getClientRects().length){e.preventDefault();search.focus();}}});
 const toggle=document.getElementById('menuToggle'),sidebar=document.getElementById('adminSidebar');
 toggle?.addEventListener('click',()=>{if(toggle.getAttribute('aria-expanded')==='true')sidebar?.querySelector('a')?.focus();});
 sidebar?.addEventListener('keydown',e=>{if(e.key==='Tab'&&document.body.classList.contains('menu-open')){const links=[...sidebar.querySelectorAll('a,button')].filter(el=>el.getClientRects().length);const first=links[0],last=links[links.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.activeElement?.closest('#adminSidebar'))toggle?.focus();},true);
 window.addEventListener('pageshow',()=>{document.querySelectorAll('button[aria-busy="true"]').forEach(b=>{b.disabled=false;b.removeAttribute('aria-busy');});});
});
