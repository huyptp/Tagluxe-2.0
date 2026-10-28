document.getElementById('printBill').addEventListener('click', async function () {
  const status = document.getElementById('printStatus');
  this.disabled = true;
  try {
    await Promise.all(Array.from(document.images).map(img => img.decode()));
    status.textContent = '';
    window.print();
  } catch (_) {
    status.textContent = 'Chưa tải được ảnh hoặc QR. Vui lòng tải lại trang trước khi in.';
  } finally {
    this.disabled = false;
  }
});
