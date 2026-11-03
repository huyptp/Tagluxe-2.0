document.addEventListener('DOMContentLoaded', () => {
  const setExpanded = (id, expanded) => {
    const panel = document.getElementById(id);
    if (!panel) return;
    panel.hidden = !expanded;
    panel.previousElementSibling?.classList.toggle('customer-expanded', expanded);
    document.querySelectorAll('[data-customer-toggle]').forEach(button => {
      if (button.dataset.customerToggle !== id) return;
      button.setAttribute('aria-expanded', String(expanded));
      const label = button.querySelector('[data-expand-label]');
      if (label) label.textContent = expanded ? 'Thu gọn' : 'Xem báo giá';
    });
  };
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-customer-toggle]');
    if (button) setExpanded(button.dataset.customerToggle, button.getAttribute('aria-expanded') !== 'true');
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const panel = event.target.closest('.customer-history-row');
    if (!panel || panel.hidden) return;
    setExpanded(panel.id, false);
    const toggle = [...document.querySelectorAll('[data-customer-toggle]')].find(
      button => button.dataset.customerToggle === panel.id);
    toggle?.focus({preventScroll:true});
  });
});
