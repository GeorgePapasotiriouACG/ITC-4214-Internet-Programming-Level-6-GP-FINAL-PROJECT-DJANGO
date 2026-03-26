'use strict';

// ── CSRF Helper ────────────────────────────────────────────
function getCookie(name) {
  let v = null;
  document.cookie.split(';').forEach(c => {
    const [k, val] = c.trim().split('=');
    if (k === name) v = decodeURIComponent(val);
  });
  return v;
}
const csrfToken = getCookie('csrftoken');

function fetchPost(url, data) {
  return fetch(url, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

function fetchPostForm(url, formData) {
  formData.append('csrfmiddlewaretoken', csrfToken);
  return fetch(url, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken },
    body: formData,
  });
}

// ── Toast Notifications ─────────────────────────────────────
const Toast = {
  container: null,
  init() {
    this.container = document.querySelector('.toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },
  show(msg, type = 'success', duration = 4000) {
    if (!this.container) this.init();
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.setAttribute('role', 'alert');
    t.setAttribute('aria-live', 'polite');
    t.innerHTML = `<span class="toast-icon">${icons[type] || '💬'}</span><span class="toast-msg">${msg}</span><button class="toast-close" aria-label="Close">✕</button>`;
    this.container.appendChild(t);
    t.querySelector('.toast-close').addEventListener('click', () => t.remove());
    setTimeout(() => { if (t.parentNode) { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); } }, duration);
  }
};

// ── Dropdown Menus ──────────────────────────────────────────
function initDropdowns() {
  document.querySelectorAll('[data-dropdown]').forEach(trigger => {
    const menuId = trigger.dataset.dropdown;
    const menu = document.getElementById(menuId);
    if (!menu) return;
    trigger.addEventListener('click', e => {
      e.stopPropagation();
      const isOpen = menu.classList.contains('open');
      document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
      if (!isOpen) menu.classList.add('open');
    });
    trigger.setAttribute('aria-haspopup', 'true');
    trigger.setAttribute('aria-expanded', 'false');
    menu.addEventListener('keydown', e => { if (e.key === 'Escape') { menu.classList.remove('open'); trigger.focus(); } });
  });
  document.addEventListener('click', () => document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open')));
}

// ── Mobile Nav ──────────────────────────────────────────────
function initMobileNav() {
  const toggleBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  if (toggleBtn && mobileMenu) {
    toggleBtn.addEventListener('click', () => {
      const expanded = toggleBtn.getAttribute('aria-expanded') === 'true';
      toggleBtn.setAttribute('aria-expanded', !expanded);
      mobileMenu.classList.toggle('open', !expanded);
    });
  }
  const searchToggle = document.getElementById('mobile-search-btn');
  const searchBar = document.getElementById('navbar-search');
  if (searchToggle && searchBar) {
    searchToggle.addEventListener('click', () => {
      searchBar.classList.toggle('mobile-open');
      if (searchBar.classList.contains('mobile-open')) searchBar.querySelector('input').focus();
    });
  }
}

// ── Search Autocomplete ─────────────────────────────────────
function initSearchAutocomplete() {
  const input = document.getElementById('search-input');
  const dropdown = document.getElementById('search-autocomplete');
  if (!input || !dropdown) return;

  let debounceTimer;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 2) { dropdown.classList.remove('open'); dropdown.innerHTML = ''; return; }
    debounceTimer = setTimeout(() => {
      fetch(`/search/autocomplete/?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => {
          dropdown.innerHTML = '';
          if (!data.results.length) { dropdown.classList.remove('open'); return; }
          data.results.forEach(p => {
            const item = document.createElement('a');
            item.href = `/products/${p.slug}/`;
            item.className = 'autocomplete-item';
            item.innerHTML = `${p.image ? `<img src="${p.image}" alt="${p.name}" loading="lazy">` : ''}<div><div class="autocomplete-item-name">${p.name}</div><div class="autocomplete-item-price">$${p.price} <span style="color:var(--text-light);font-size:.75rem;">&mdash; ${p.category}</span></div></div>`;
            dropdown.appendChild(item);
          });
          dropdown.classList.add('open');
        });
    }, 280);
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { dropdown.querySelector('a')?.focus(); e.preventDefault(); }
    if (e.key === 'Escape') { dropdown.classList.remove('open'); }
  });
  document.addEventListener('click', e => { if (!input.contains(e.target) && !dropdown.contains(e.target)) dropdown.classList.remove('open'); });

  const searchForm = input.closest('form');
  if (searchForm) {
    searchForm.addEventListener('submit', e => {
      if (!input.value.trim()) { e.preventDefault(); input.focus(); }
    });
  }
}

// ── Cart AJAX ───────────────────────────────────────────────
function initCart() {
  // Add to cart buttons
  document.querySelectorAll('.add-to-cart-form').forEach(form => {
    form.addEventListener('submit', e => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      const fd = new FormData(form);
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>';
      fetchPostForm(form.action, fd)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            Toast.show(data.message || 'Added to cart!', 'success');
            updateCartBadge(data.cart_count);
          } else {
            Toast.show('Could not add to cart.', 'error');
          }
        })
        .catch(() => Toast.show('Network error. Please try again.', 'error'))
        .finally(() => { btn.disabled = false; btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg> Add to Cart'; });
    });
  });

  // Qty controls on cart page
  document.querySelectorAll('.qty-minus, .qty-plus').forEach(btn => {
    btn.addEventListener('click', () => {
      const wrapper = btn.closest('[data-item-id]');
      const itemId = wrapper.dataset.itemId;
      const input = wrapper.querySelector('.qty-input');
      let qty = parseInt(input.value, 10);
      qty = btn.classList.contains('qty-minus') ? Math.max(0, qty - 1) : qty + 1;
      input.value = qty;
      updateCartItem(itemId, qty, wrapper);
    });
  });

  document.querySelectorAll('.qty-input').forEach(input => {
    input.addEventListener('change', () => {
      const wrapper = input.closest('[data-item-id]');
      const itemId = wrapper.dataset.itemId;
      updateCartItem(itemId, parseInt(input.value, 10) || 0, wrapper);
    });
  });

  document.querySelectorAll('.remove-cart-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const itemId = btn.dataset.itemId;
      const fd = new FormData();
      fetchPostForm(`/cart/remove/${itemId}/`, fd)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            btn.closest('.cart-item')?.remove();
            updateCartBadge(data.cart_count);
            document.querySelector('.cart-total-amount')?.textContent !== undefined &&
              (document.querySelector('.cart-total-amount').textContent = `$${parseFloat(data.cart_total).toFixed(2)}`);
            Toast.show('Item removed from cart.', 'success');
            if (data.cart_count === 0) location.reload();
          }
        });
    });
  });
}

function updateCartItem(itemId, qty, wrapper) {
  const fd = new FormData();
  fd.append('quantity', qty);
  fetchPostForm(`/cart/update/${itemId}/`, fd)
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        updateCartBadge(data.cart_count);
        const subtotalEl = wrapper.querySelector('.cart-item-subtotal');
        if (subtotalEl) subtotalEl.textContent = `$${parseFloat(data.subtotal).toFixed(2)}`;
        const totalEl = document.querySelector('.cart-total-amount');
        if (totalEl) totalEl.textContent = `$${parseFloat(data.cart_total).toFixed(2)}`;
        if (qty === 0) { wrapper.remove(); if (data.cart_count === 0) location.reload(); }
      }
    });
}

function updateCartBadge(count) {
  document.querySelectorAll('.cart-badge').forEach(el => {
    el.textContent = count;
    el.style.display = count > 0 ? 'flex' : 'none';
  });
}

// ── Wishlist ────────────────────────────────────────────────
function initWishlist() {
  document.querySelectorAll('.wishlist-toggle-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.preventDefault();
      const productId = btn.dataset.productId;
      const fd = new FormData();
      fd.append('product_id', productId);
      fetchPostForm('/wishlist/toggle/', fd)
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            btn.classList.toggle('active', data.action === 'added');
            btn.setAttribute('aria-label', data.action === 'added' ? 'Remove from wishlist' : 'Add to wishlist');
            Toast.show(data.action === 'added' ? 'Added to wishlist ❤️' : 'Removed from wishlist', data.action === 'added' ? 'success' : 'info');
          }
        });
    });
  });
}

// ── Star Ratings ────────────────────────────────────────────
function initStarRating() {
  const starsContainer = document.querySelector('.stars-interactive');
  const ratingInput = document.getElementById('rating-value');
  if (!starsContainer || !ratingInput) return;

  const stars = starsContainer.querySelectorAll('.star');
  let currentRating = parseInt(ratingInput.value, 10) || 0;

  function setStars(n, type = 'set') {
    stars.forEach((s, i) => {
      s.classList.toggle('filled', i < n);
      if (type === 'hover') s.classList.toggle('hover', i < n);
    });
  }
  if (currentRating) setStars(currentRating);

  stars.forEach((star, i) => {
    star.addEventListener('mouseenter', () => setStars(i + 1, 'hover'));
    star.addEventListener('mouseleave', () => { stars.forEach(s => s.classList.remove('hover')); setStars(currentRating); });
    star.addEventListener('click', () => {
      currentRating = i + 1;
      ratingInput.value = currentRating;
      setStars(currentRating);
    });
    star.setAttribute('tabindex', '0');
    star.setAttribute('role', 'radio');
    star.setAttribute('aria-label', `${i + 1} star${i > 0 ? 's' : ''}`);
    star.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); star.click(); } });
  });
}

function initRatingForm() {
  const form = document.getElementById('rating-form');
  if (!form) return;
  form.addEventListener('submit', e => {
    e.preventDefault();
    const rating = document.getElementById('rating-value')?.value;
    if (!rating || rating === '0') { Toast.show('Please select a star rating.', 'warning'); return; }
    const fd = new FormData(form);
    fetchPostForm(form.action, fd)
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          Toast.show('Your review has been submitted! ⭐', 'success');
          document.querySelector('.avg-rating-display')?.textContent !== undefined &&
            (document.querySelector('.avg-rating-display').textContent = data.avg_rating);
          document.querySelector('.rating-count-display')?.textContent !== undefined &&
            (document.querySelector('.rating-count-display').textContent = `${data.count} review${data.count !== 1 ? 's' : ''}`);
          const section = document.getElementById('reviews-list');
          if (section && data.review) {
            const card = document.createElement('div');
            card.className = 'review-card';
            card.style.animation = 'slideUp .4s ease';
            card.innerHTML = `<div class="review-header"><div class="review-avatar">${data.username[0].toUpperCase()}</div><div><div class="review-author">${data.username}</div><div class="stars">${'★'.repeat(data.rating)}${'☆'.repeat(5 - data.rating)}</div></div></div><p class="review-text">${data.review}</p>`;
            section.prepend(card);
          }
        } else {
          Toast.show(data.error || 'Failed to submit review.', 'error');
        }
      })
      .catch(() => Toast.show('Network error.', 'error'));
  });
}

// ── AI Chat ─────────────────────────────────────────────────
function initAIChat() {
  const trigger = document.getElementById('ai-chat-trigger');
  const panel = document.getElementById('ai-chat-panel');
  const closeBtn = document.getElementById('ai-chat-close');
  const input = document.getElementById('ai-input');
  const sendBtn = document.getElementById('ai-send');
  const messages = document.getElementById('ai-messages');
  if (!trigger || !panel) return;

  trigger.addEventListener('click', () => {
    panel.classList.toggle('open');
    trigger.setAttribute('aria-expanded', panel.classList.contains('open'));
    if (panel.classList.contains('open') && input) { setTimeout(() => input.focus(), 200); }
  });
  closeBtn?.addEventListener('click', () => { panel.classList.remove('open'); trigger.setAttribute('aria-expanded', 'false'); });

  function appendMsg(text, type) {
    const msg = document.createElement('div');
    msg.className = `ai-msg ${type}`;
    msg.setAttribute('aria-live', 'polite');
    msg.innerHTML = `<div class="ai-bubble">${text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}</div>`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    const t = document.createElement('div');
    t.className = 'ai-msg bot'; t.id = 'ai-typing-indicator';
    t.innerHTML = '<div class="ai-typing"><span></span><span></span><span></span></div>';
    messages.appendChild(t); messages.scrollTop = messages.scrollHeight;
    return t;
  }

  function sendMessage(text) {
    if (!text.trim()) return;
    appendMsg(text, 'user');
    if (input) input.value = '';
    const typing = showTyping();
    fetchPost('/ai/chat/', { message: text })
      .then(r => r.json())
      .then(data => { typing.remove(); appendMsg(data.reply, 'bot'); })
      .catch(() => { typing.remove(); appendMsg("Sorry, I'm having trouble connecting. Please try again!", 'bot'); });
  }

  sendBtn?.addEventListener('click', () => sendMessage(input?.value || ''));
  input?.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); } });

  document.querySelectorAll('.ai-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.textContent.trim()));
  });
}

// ── Filter Sidebar Collapse ─────────────────────────────────
function initFilterCollapse() {
  document.querySelectorAll('.filter-title').forEach(title => {
    title.addEventListener('click', () => {
      title.closest('.filter-group').classList.toggle('collapsed');
    });
  });
}

// ── Size Selector ───────────────────────────────────────────
function initSizeSelector() {
  document.querySelectorAll('.size-btn:not(.out-of-stock)').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.size-selector').querySelectorAll('.size-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      const sizeInput = document.getElementById('selected-size');
      if (sizeInput) sizeInput.value = btn.dataset.size;
    });
  });
}

// ── Sticky category highlight ───────────────────────────────
function initActiveCategoryNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-cat-link').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });
}

// ── Message auto-dismiss ────────────────────────────────────
function initDjangoMessages() {
  document.querySelectorAll('.django-message').forEach(el => {
    const type = el.dataset.type || 'success';
    Toast.show(el.textContent.trim(), type);
    el.remove();
  });
}

// ── Init all ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  initDropdowns();
  initMobileNav();
  initSearchAutocomplete();
  initCart();
  initWishlist();
  initStarRating();
  initRatingForm();
  initAIChat();
  initFilterCollapse();
  initSizeSelector();
  initActiveCategoryNav();
  initDjangoMessages();
});
