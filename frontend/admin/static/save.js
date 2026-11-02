/* Save the current editor without navigating away or replacing entered fields. */
window.adminInPlaceSave = true;
window.adminSaveNotice = (message, error = false) => {
  let toast = document.getElementById('adminSaveNotice');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'adminSaveNotice';
    toast.className = 'admin-save-notice';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.append(toast);
  }
  clearTimeout(toast.timer);
  toast.classList.toggle('is-error', error);
  toast.textContent = message;
  toast.hidden = false;
  toast.timer = setTimeout(() => { toast.hidden = true; }, error ? 12000 : 5000);
};

window.refreshAdminFragment = async (selector, url = location.href) => {
  const response = await fetch(url, {headers: {'Accept': 'text/html'}, cache: 'no-store'});
  if (!response.ok || response.redirected) throw new Error('refresh');
  const documentCopy = new DOMParser().parseFromString(await response.text(), 'text/html');
  const fresh = documentCopy.querySelector(selector), current = document.querySelector(selector);
  if (!fresh || !current) throw new Error('refresh');
  current.replaceChildren(...[...fresh.childNodes].map(node => document.importNode(node, true)));
  if(selector === '#accessoryRows') {
    const stats=document.querySelector('.acc-stats-grid'), freshStats=documentCopy.querySelector('.acc-stats-grid');
    if(stats && freshStats) stats.replaceChildren(...[...freshStats.childNodes].map(node=>document.importNode(node,true)));
    const tab=document.querySelector('.pricing-page-tabs .badge'), freshTab=documentCopy.querySelector('.pricing-page-tabs .badge');
    if(tab && freshTab) tab.textContent=freshTab.textContent;
  }
  window.lucide?.createIcons();
};

document.addEventListener('DOMContentLoaded', () => {
  const savePath = /^\/admin\/(?:products\/(?:add|edit\/[^/]+|update-specs)|pricing\/update|accessories\/(?:add|edit\/[^/]+)|demo-images\/update|campaign-banner\/update|customers\/(?:new|[^/]+\/edit)|quotes\/(?:[^/]+|status\/[^/]+)|payments|staff(?:\/\d+)?|notifications(?:\/[^/]+)?|account\/password)$/;
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || event.defaultPrevented || form.method.toLowerCase() !== 'post') return;
    const url = new URL(form.action || location.href, location.href);
    if (url.origin !== location.origin || !savePath.test(url.pathname)) return;
    if (!event.submitter?.formNoValidate && !form.checkValidity()) return;
    event.preventDefault();
    if (form.dataset.saving === '1') return;
    const payload = new FormData(form);
    if (event.submitter?.name) payload.append(event.submitter.name, event.submitter.value);
    const controls = [...form.elements].filter(el => 'disabled' in el).map(el => [el, el.disabled]);
    const focus = document.activeElement;
    const button = event.submitter, buttonText = button?.innerHTML;
    form.dataset.saving = '1';
    form.dispatchEvent(new CustomEvent('admin:save-start'));
    controls.forEach(([el]) => { el.disabled = true; });
    if (button) { button.textContent = 'Đang lưu…'; button.setAttribute('aria-busy', 'true'); }
    let saved = false, result;
    try {
      const response = await fetch(url, {
        method: 'POST', body: payload, credentials: 'same-origin', redirect: 'error',
        headers: {'Accept': 'application/json', 'X-Admin-Save': '1'},
      });
      if (!response.headers.get('Content-Type')?.includes('application/json')) throw new Error('unconfirmed');
      result = await response.json();
      if (!response.ok || !result.success) {
        window.adminSaveNotice(result.message || 'Chưa lưu được thay đổi. Nội dung vẫn được giữ để bạn thử lại.', true);
        return;
      }
      saved = true;
      if(result.quote_statuses) document.querySelectorAll('[data-quote-status]').forEach(label=>{
        const status=result.quote_statuses[label.dataset.quoteStatus];
        if(status){label.textContent=status;label.dataset.status=status;}
      });
      if (result.version !== undefined && form.elements.namedItem('version')) form.elements.namedItem('version').value = result.version;
      if (result.form_action) {
        const action = new URL(result.form_action, location.origin);
        if (action.origin === location.origin && action.pathname.startsWith('/admin/')) {
          form.action = action.pathname;
          if (url.pathname === '/admin/accessories/add' && button) button.dataset.savedLabel = 'Lưu thay đổi';
          if (/^\/admin\/(customers\/new|products\/add)$/.test(location.pathname)) {
            history.replaceState(null, '', action.pathname);
            document.querySelector('.page-heading h1').textContent = result.phone ? 'Chỉnh hồ sơ khách' : 'Chỉnh sửa sản phẩm';
            if (button) buttonText && (button.dataset.savedLabel = result.phone ? 'Lưu hồ sơ' : 'Lưu thông tin');
          }
        }
      }
      if (result.phone) {
        const phone = form.elements.namedItem('phone');
        if (phone) { phone.value = result.phone; phone.readOnly = true; }
      }
      if (result.images) updateSavedProductImages(form, result);
      if (result.data && url.pathname === '/admin/demo-images/update') {
        Object.entries(result.data).forEach(([key, value]) => {
          const input = form.elements.namedItem('url_' + key);
          if (input && value.image) input.value = value.image;
        });
      }
      form.querySelectorAll('input[type=file],input[type=password]').forEach(input => { input.value = ''; });
      try {
        if (url.pathname === '/admin/pricing/update') {
          const group=document.querySelector('[data-price-group][aria-pressed="true"]')?.dataset.priceGroup;
          const scroll={top:window.scrollY,left:window.scrollX,behavior:'instant'};
          await refreshAdminFragment('#pricingMatrixForm', '/admin/accessories?tab=pricing');
          if(group) window.choosePriceGroup?.(group);
          window.scrollTo(scroll);
        } else if (url.pathname.startsWith('/admin/accessories/')) {
          await refreshAdminFragment('#accessoryRows', '/admin/accessories?tab=accessories');
          window.applyAccessoryFilters?.();
        } else if (url.pathname === '/admin/staff') {
          await refreshAdminFragment('#staffMembers');
          form.reset();
        } else if (/^\/admin\/staff\/\d+$/.test(url.pathname)) {
          const member = form.closest('details');
          const response = await fetch(location.href, {cache: 'no-store'});
          const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
          const freshForm = [...doc.forms].find(item => item.getAttribute('action') === url.pathname);
          const summary = freshForm?.closest('details')?.querySelector('summary');
          if (summary && member) member.querySelector('summary').replaceWith(document.importNode(summary, true));
          const toggle = form.querySelector('[value="toggle"]'), freshToggle = freshForm?.querySelector('[value="toggle"]');
          if(toggle && freshToggle) toggle.textContent = freshToggle.textContent;
        } else if (url.pathname.startsWith('/admin/notifications')) {
          await refreshAdminFragment('#notificationRecipients');
          if (url.pathname === '/admin/notifications') form.reset();
        }
        window.adminSaveNotice(result.message || 'Đã lưu thành công.');
      } catch {
        result.ui_refreshed = false;
        window.adminSaveNotice(url.pathname === '/admin/pricing/update' ?
          'Đã lưu bảng giá vào cơ sở dữ liệu. Hãy tải lại trang trước khi chỉnh tiếp để tránh tạo trùng bậc giá.' :
          'Đã lưu vào cơ sở dữ liệu. Một số thông tin hiển thị chưa làm mới được đầy đủ.');
      }
    } catch {
      window.adminSaveNotice(saved ? 'Đã lưu vào cơ sở dữ liệu. Màn hình chưa làm mới được đầy đủ.' :
        'Chưa xác nhận được kết quả do mất kết nối. Nội dung vẫn còn; hãy kiểm tra dữ liệu đã lưu trước khi thử lại.', !saved);
    } finally {
      controls.forEach(([el, disabled]) => { el.disabled = disabled; });
      if (button) { button.innerHTML = button.dataset.savedLabel || buttonText; button.removeAttribute('aria-busy'); }
      delete form.dataset.saving;
      form.dispatchEvent(new CustomEvent(saved ? 'admin:save-success' : 'admin:save-error', {detail: result}));
      if (focus?.isConnected) focus.focus({preventScroll: true});
    }
  });
});

function updateSavedProductImages(form, result) {
  let marker = form.elements.namedItem('kept_images_present');
  if (!marker) { marker = document.createElement('input'); marker.type = 'hidden'; marker.name = 'kept_images_present'; form.append(marker); }
  marker.value = '1';
  const grid = document.getElementById('existingImagesGrid');
  grid.replaceChildren();
  result.images.forEach(name => {
    const item = document.createElement('div'); item.className = 'existing-img-item'; item.dataset.img = name;
    const hidden = document.createElement('input'); hidden.type = 'hidden'; hidden.name = 'kept_images[]'; hidden.value = name;
    const image = document.createElement('img'); image.src = '/static/uploads/' + encodeURIComponent(name); image.alt = 'Ảnh sản phẩm đã lưu';
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '✕ Xóa ảnh';
    remove.addEventListener('click', () => window.removeExistingProductImage(remove, result.product_id, name));
    item.append(hidden, image, remove); grid.append(item);
  });
  document.getElementById('newProductImagesPreviewWrap').style.display = 'none';
}
