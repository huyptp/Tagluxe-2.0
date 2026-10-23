const pricingCSRF=document.querySelector('.pricing-admin-page').dataset.csrf;

    function openAddAccessoryModal() {
        showAccessoryDialog('addAccessoryModal');
    }
    function closeAddAccessoryModal() {
        hideAccessoryDialog('addAccessoryModal');
    }

    function previewNewImage(input) {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('new_img_preview').src = e.target.result;
                document.getElementById('new_img_preview_box').style.display = 'block';
            };
            reader.readAsDataURL(input.files[0]);
        }
    }

    function clearNewAccessoryImage(ev) {
        if (ev) ev.stopPropagation();
        const input = document.getElementById('new_acc_img_input');
        if (input) input.value = '';
        const preview = document.getElementById('new_img_preview');
        if (preview) preview.src = '';
        const box = document.getElementById('new_img_preview_box');
        if (box) box.style.display = 'none';
    }

    function previewEditAccessoryImage(input) {
        if (input.files && input.files[0]) {
            const file = input.files[0];
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('edit_new_img_preview').src = e.target.result;
                document.getElementById('edit_new_img_filename').textContent = 'Đã chọn: ' + file.name;
                document.getElementById('edit_new_img_preview_box').style.display = 'flex';
                document.getElementById('edit_remove_image_flag').value = '0';
            };
            reader.readAsDataURL(file);
        }
    }

    function clearEditAccessoryImage() {
        const input = document.getElementById('edit_acc_img_input');
        if (input) input.value = '';
        const preview = document.getElementById('edit_new_img_preview');
        if (preview) preview.src = '';
        const box = document.getElementById('edit_new_img_preview_box');
        if (box) box.style.display = 'none';
    }

    function markRemoveCurrentAccessoryImage() {
        if (!confirm('Bạn có chắc muốn xóa ảnh hiện tại của phụ kiện này không?')) {
            return;
        }
        document.getElementById('edit_remove_image_flag').value = '1';
        const wrap = document.getElementById('edit_current_img_wrap');
        if (wrap) wrap.style.display = 'none';
    }

    function deleteAccessoryImage(accId) {
        if (!confirm('Bạn có chắc muốn xóa ảnh của phụ kiện này không?')) {
            return;
        }
        const formData = new FormData();
        formData.append('csrf_token', pricingCSRF);

        fetch('/admin/accessories/delete-image/' + encodeURIComponent(accId), {
            method: 'POST',
            headers: { 'Accept': 'application/json' },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data && data.success) {
                window.location.reload();
            } else {
                alert('Lỗi: ' + (data.message || 'Không thể xóa ảnh'));
            }
        })
        .catch(() => alert('Lỗi kết nối máy chủ'));
    }

    function openEditModalFromBtn(btn) {
        const form = document.getElementById('editAccessoryForm');
        form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=false);
        const id = btn.getAttribute('data-id');
        form.action = '/admin/accessories/edit/' + id;
        document.getElementById('edit_name').value = btn.getAttribute('data-name') || '';
        document.getElementById('edit_price').value = btn.getAttribute('data-price') || 0;
        document.getElementById('edit_min_quantity').value = btn.getAttribute('data-min-qty') || 0;
        document.getElementById('edit_description').value = btn.getAttribute('data-desc') || '';
        document.getElementById('edit_visible').checked = btn.getAttribute('data-visible') === '1';
        document.getElementById('edit_remove_image_flag').value = '0';
        clearEditAccessoryImage();

        const rawImage = btn.getAttribute('data-image') || '';
        const imageUrl = btn.getAttribute('data-image-url') || '';
        const currentWrap = document.getElementById('edit_current_img_wrap');
        const currentThumb = document.getElementById('edit_current_img_thumb');
        if (rawImage && imageUrl && currentWrap && currentThumb) {
            currentThumb.src = imageUrl;
            currentWrap.style.display = 'flex';
        } else if (currentWrap) {
            currentWrap.style.display = 'none';
        }

        showAccessoryDialog('editAccessoryModal');
    }
    function closeEditModal() {
        hideAccessoryDialog('editAccessoryModal');
    }

    function triggerUpload(accId) {
        const fileInput = document.getElementById('file_' + accId);
        if (fileInput) fileInput.click();
    }
    function uploadImage(accId, input) {
        if (!input.files || !input.files[0]) return;
        const formData = new FormData();
        formData.append('image', input.files[0]);
        formData.append('csrf_token', pricingCSRF);

        fetch('/admin/accessories/upload/' + accId, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert('Lỗi: ' + (data.message || 'Không thể tải ảnh'));
            }
        })
        .catch(err => alert('Lỗi kết nối máy chủ'));
    }

    function toggleVisibility(accId, btn) {
        const formData = new FormData();
        formData.append('csrf_token', pricingCSRF);

        fetch('/admin/accessories/toggle/' + accId, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                btn.closest('.acc-row').dataset.visible = data.visible ? '1' : '0';
                applyAccessoryFilters();
                if (data.visible) {
                    btn.innerHTML = '<span style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 4px 9px; border-radius: 6px; white-space: nowrap;">● Đang bật</span>';
                    btn.style.color = '#16a34a';
                } else {
                    btn.innerHTML = '<span style="background: #f1f5f9; border: 1px solid #cbd5e1; padding: 4px 9px; border-radius: 6px; white-space: nowrap;">○ Đang ẩn</span>';
                    btn.style.color = '#94a3b8';
                }
            } else {
                alert('Lỗi: ' + (data.message || 'Không thể đổi trạng thái'));
            }
        })
        .catch(err => alert('Lỗi kết nối'));
    }

    function confirmDelete(accId, accName) {
        if (confirm('Bạn có chắc chắn muốn xóa phụ kiện "' + accName + '" không?')) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/admin/accessories/delete/' + accId;
            const csrf = document.createElement('input');
            csrf.type = 'hidden';
            csrf.name = 'csrf_token';
            csrf.value = pricingCSRF;
            form.appendChild(csrf);
            document.body.appendChild(form);
            form.submit();
        }
    }

    if (window.lucide) {
        lucide.createIcons();
    }
/* Price edits are staged in the form until a valid submit. */
let newTierCounter = 0;
const priceForm = document.getElementById('pricingMatrixForm');
const formatVND = value => new Intl.NumberFormat('vi-VN').format(value);
let pricingDirty = false;
let originalPriceTables = [];

function refreshPricingChanges() {
  if (!priceForm) return;
  let changed = 0;
  priceForm.querySelectorAll('tr[data-tier-id]').forEach(row => {
    const deleted = row.dataset.deleted === '1';
    const fresh = row.dataset.tierId.startsWith('new_');
    const dirty = fresh || [...row.querySelectorAll('input[type=number]')].some(input=>input.value !== input.dataset.original);
    if(deleted || dirty) changed++;
    row.classList.toggle('price-row-changed',dirty && !deleted);
    const price = row.querySelector('[name^=tier_price_]');
    const delta = row.querySelector('.price-delta');
    if(delta && price){
      const diff=Number(price.value)-Number(price.dataset.original || 0);
      delta.textContent=deleted ? 'Đã bỏ' : fresh ? 'Mới' : diff ? (diff>0?'+':'')+formatVND(diff)+' đ' : '—';
      delta.classList.toggle('price-increase',diff>0);
      delta.classList.toggle('price-decrease',diff<0);
    }
  });
  pricingDirty=changed>0;
  document.getElementById('pricingChangeCount').textContent=changed ? `${changed} bậc giá chưa lưu` : 'Chưa có thay đổi';
  document.getElementById('savePricing').disabled=!pricingDirty;
  document.getElementById('resetPricing').disabled=!pricingDirty;
}
function deleteTierRow(button,id) {
  const row=button.closest('tr');
  if(String(id).startsWith('new_'))row.remove();
  else {
    const deleting=row.dataset.deleted!=='1';
    row.dataset.deleted=deleting?'1':'0';
    row.classList.toggle('price-row-deleted',deleting);
    row.querySelectorAll('input').forEach(input=>input.disabled=deleting);
    const existing=priceForm.querySelector(`[name="tier_deleted_${id}"]`);
    if(existing)existing.remove();
    if(deleting){const hidden=document.createElement('input');hidden.type='hidden';hidden.name='tier_deleted_'+id;hidden.value='1';priceForm.append(hidden);}
    button.textContent=deleting?'Khôi phục':'×';
    button.setAttribute('aria-label',deleting?'Khôi phục bậc giá đã bỏ':'Bỏ bậc giá');
  }
  refreshPricingChanges();
}
function addNewTierRow(tableId,category,unit) {
  const table=document.getElementById(tableId),body=table.tBodies[0];
  const rows=[...body.querySelectorAll('tr')].filter(row=>row.dataset.deleted!=='1');
  const last=rows.at(-1),lastMax=last?.querySelector('[name^=tier_max_]');
  const min=lastMax ? Number(lastMax.value)+1 : 1;
  const max=min+99,id='new_'+(++newTierCounter);
  const row=document.createElement('tr');row.id='tier_row_'+id;row.dataset.tierId=id;
  row.innerHTML=`<td><input type="hidden" name="tier_cat_${id}" value="${category}"><input type="number" name="tier_min_${id}" min="0" step="1" required value="${min}" aria-label="Số lượng từ bậc mới"></td><td><input type="number" name="tier_max_${id}" min="0" step="1" required value="${max}" aria-label="Số lượng đến bậc mới"></td><td class="numeric muted">Mới</td><td><div class="price-input-wrap"><input type="number" name="tier_price_${id}" min="0" step="1" required value="0" aria-label="Giá bậc mới"><span>đ</span></div></td><td class="price-delta numeric">Mới</td><td><button class="remove-tier" type="button" onclick="deleteTierRow(this,'${id}')" aria-label="Bỏ bậc mới">×</button></td>`;
  body.append(row);refreshPricingChanges();row.querySelector('[type=number]').focus();
}
function choosePriceGroup(group) {
  document.querySelectorAll('[data-price-panel]').forEach(panel=>panel.hidden=panel.dataset.pricePanel!==group);
  document.querySelectorAll('[data-price-group]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.priceGroup===group)));
}
if(priceForm){
  priceForm.querySelectorAll('input[type=number]').forEach(input=>input.dataset.original=input.value);
  // Snapshot after recording the original values, so reset also restores comparison metadata.
  originalPriceTables=[...priceForm.querySelectorAll('tbody')].map(body=>[body,body.innerHTML]);
  priceForm.addEventListener('input',refreshPricingChanges);
  document.querySelectorAll('[data-price-group]').forEach(button=>button.addEventListener('click',()=>choosePriceGroup(button.dataset.priceGroup)));
  document.getElementById('resetPricing').addEventListener('click',()=>{
    if(!confirm('Hoàn tác toàn bộ thay đổi bảng giá chưa lưu?'))return;
    originalPriceTables.forEach(([body,html])=>body.innerHTML=html);
    priceForm.querySelectorAll('[name^=tier_deleted_]').forEach(input=>input.remove());
    document.getElementById('pricingValidation').textContent='';refreshPricingChanges();
  });
  // Capture invalid controls in a hidden group, reveal them before native validation focuses them.
  priceForm.addEventListener('invalid',event=>{
    const panel=event.target.closest('[data-price-panel]');if(panel)choosePriceGroup(panel.dataset.pricePanel);
  },true);
  priceForm.addEventListener('submit',event=>{
    let bad=null;
    priceForm.querySelectorAll('tr[data-tier-id]').forEach(row=>{
      if(row.dataset.deleted==='1')return;
      const min=row.querySelector('[name^=tier_min_]'),max=row.querySelector('[name^=tier_max_]');
      if(min && max && Number(min.value)>Number(max.value))bad=bad||min;
    });
    if(bad){event.preventDefault();choosePriceGroup(bad.closest('[data-price-panel]').dataset.pricePanel);document.getElementById('pricingValidation').textContent='Số lượng bắt đầu không được lớn hơn số lượng kết thúc. Vui lòng kiểm tra dòng được chọn.';bad.focus();return;}
    if(!pricingDirty){event.preventDefault();return;}
    pricingDirty=false;
  },true);
  window.addEventListener('beforeunload',event=>{if(pricingDirty){event.preventDefault();event.returnValue='';}});
}

function applyAccessoryFilters(){
  const term=(document.getElementById('accessorySearch')?.value||'').toLocaleLowerCase('vi');
  const category=document.getElementById('accessoryCategory')?.value||'all';
  const visible=document.getElementById('accessoryVisibility')?.value||'all';
  let count=0;
  document.querySelectorAll('.acc-row').forEach(row=>{
    const match=(!term||row.textContent.toLocaleLowerCase('vi').includes(term)) && (category==='all'||row.dataset.category===category) && (visible==='all'||row.dataset.visible===visible);
    row.hidden=!match;if(match)count++;
  });
  const counter=document.getElementById('accessoryResultCount');if(counter)counter.textContent=`Hiển thị ${count} phụ kiện`;
  const empty=document.getElementById('accessoryEmptyRow');if(empty)empty.hidden=count!==0;
}
['accessorySearch','accessoryCategory','accessoryVisibility'].forEach(id=>document.getElementById(id)?.addEventListener('input',applyAccessoryFilters));
applyAccessoryFilters();

let dialogReturnFocus=null;
function showAccessoryDialog(id){
  const modal=document.getElementById(id);dialogReturnFocus=document.activeElement;
  modal.classList.add('active');document.body.classList.add('accessory-dialog-open');
  modal.querySelector('input:not([type=hidden]),button')?.focus();
}
function hideAccessoryDialog(id){document.getElementById(id).classList.remove('active');document.body.classList.remove('accessory-dialog-open');dialogReturnFocus?.focus();}
document.querySelectorAll('.modal-overlay').forEach(modal=>{
  modal.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();hideAccessoryDialog(modal.id);}
    if(event.key==='Tab'){
      const controls=[...modal.querySelectorAll('button,input,select,textarea,a[href]')].filter(e=>!e.disabled&&e.getClientRects().length);
      const first=controls[0],last=controls.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    }
  });
});
document.querySelectorAll('.thumb-preview-wrap').forEach(button=>button.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();button.click();}}));
