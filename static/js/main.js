'use strict';

// =============================================================================
// Author:       George Papasotiriou
// Date Created: March 28, 2026
// Project:      TrendMart E-Commerce Platform
// File:         static/js/main.js
// Description:  Main vanilla JavaScript file for TrendMart. Handles all
//               client-side interactivity including: dark mode toggle, hero
//               particle canvas, toast notifications, dropdown menus, mobile
//               navigation, search autocomplete, AJAX cart/wishlist/ratings,
//               AI chat assistant UI, product quick view, price slider,
//               currency converter, PWA install prompt, and recently viewed strip.
//
// No external JS frameworks are used — all vanilla ES6+ JavaScript.
// =============================================================================

// ── CSRF Helper ────────────────────────────────────────────
// Django requires a CSRF token for all POST requests.
// getCookie reads it from the browser's cookie jar so AJAX calls pass auth.
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

// ── Hero Particle Canvas ────────────────────────────────────
function initHeroParticles() {
  const canvas = document.getElementById('hero-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const hero = document.getElementById('hero-section');
  if (!hero) return;

  let mouse = { x: -9999, y: -9999 };
  let W, H, particles;

  function resize() {
    W = canvas.width = hero.offsetWidth;
    H = canvas.height = hero.offsetHeight;
  }

  function createParticles() {
    particles = [];
    const count = Math.min(Math.floor((W * H) / 9000), 70);
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * W,
        y: Math.random() * H,
        r: Math.random() * 18 + 8,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        opacity: Math.random() * 0.07 + 0.03,
        pulsePhase: Math.random() * Math.PI * 2,
        pulseSpeed: Math.random() * 0.015 + 0.008,
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      p.pulsePhase += p.pulseSpeed;
      const pulse = Math.sin(p.pulsePhase) * 0.015;
      const opacity = Math.max(0, p.opacity + pulse);

      const dx = mouse.x - p.x;
      const dy = mouse.y - p.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const repulseR = 140;

      if (dist < repulseR) {
        const force = (1 - dist / repulseR) * 0.9;
        p.x -= dx * force * 0.04;
        p.y -= dy * force * 0.04;
      }

      p.x += p.vx;
      p.y += p.vy;

      if (p.x < -p.r) p.x = W + p.r;
      if (p.x > W + p.r) p.x = -p.r;
      if (p.y < -p.r) p.y = H + p.r;
      if (p.y > H + p.r) p.y = -p.r;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${opacity})`;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }

  hero.addEventListener('mousemove', e => {
    const rect = hero.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });
  hero.addEventListener('mouseleave', () => { mouse.x = -9999; mouse.y = -9999; });

  window.addEventListener('resize', () => { resize(); createParticles(); });
  resize();
  createParticles();
  draw();
}

// ── Dark Mode ───────────────────────────────────────────────
function initDarkMode() {
  const savedTheme = localStorage.getItem('trendmart-theme') || 'light';
  if (savedTheme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

  function toggleDark() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const next = isDark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('trendmart-theme', next);
    document.querySelectorAll('[aria-label="Toggle dark mode"]').forEach(btn => {
      btn.setAttribute('aria-pressed', String(!isDark));
    });
  }

  document.getElementById('dark-mode-toggle')?.addEventListener('click', toggleDark);
  document.getElementById('dark-mode-toggle-mobile')?.addEventListener('click', toggleDark);

  const btn = document.getElementById('dark-mode-toggle');
  if (btn) btn.setAttribute('aria-pressed', savedTheme === 'dark' ? 'true' : 'false');
}

// ── Mobile Nav ──────────────────────────────────────────────
function initMobileNav() {
  const toggleBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const closeBtn = document.getElementById('mobile-menu-close');

  function openMenu() {
    mobileMenu.classList.add('open');
    toggleBtn.setAttribute('aria-expanded', 'true');
    toggleBtn.classList.add('open');
    document.body.style.overflow = 'hidden';
    closeBtn?.focus();
  }
  function closeMenu() {
    mobileMenu.classList.remove('open');
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.classList.remove('open');
    document.body.style.overflow = '';
    toggleBtn?.focus();
  }

  if (toggleBtn && mobileMenu) {
    toggleBtn.addEventListener('click', () => {
      mobileMenu.classList.contains('open') ? closeMenu() : openMenu();
    });
    closeBtn?.addEventListener('click', closeMenu);
    mobileMenu.addEventListener('click', e => { if (e.target === mobileMenu) closeMenu(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && mobileMenu.classList.contains('open')) closeMenu(); });
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
// Enhanced AI chat widget:
//  • DB-backed conversation history (auth users) with export + clear
//  • Voice input via Web Speech API (Chrome/Edge native)
//  • Image upload → base64 → backend vision search
//  • Rich product cards rendered from response metadata
//  • Typing animation (character-by-character reveal)
//  • Proactive contextual bubbles triggered by page context + idle time
//  • Sentiment detection → frustrated flag sent to backend
//  • Dynamic quick-action buttons that adapt to conversation context
// Author: George Papasotiriou — TrendMart 2026
function initAIChat() {
  const trigger      = document.getElementById('ai-chat-trigger');
  const panel        = document.getElementById('ai-chat-panel');
  const closeBtn     = document.getElementById('ai-chat-close');
  const clearBtn     = document.getElementById('ai-clear-chat');
  const exportBtn    = document.getElementById('ai-export-chat');
  const input        = document.getElementById('ai-input');
  const sendBtn      = document.getElementById('ai-send');
  const messages     = document.getElementById('ai-messages');
  const charCount    = document.getElementById('ai-char-count');
  const statusLine   = document.getElementById('ai-status-line');
  const micBtn       = document.getElementById('ai-mic-btn');
  const imgBtn       = document.getElementById('ai-img-btn');
  const imgFileInput = document.getElementById('ai-img-input');
  const imgPreview   = document.getElementById('ai-img-preview');
  const imgThumb     = document.getElementById('ai-img-thumb');
  const imgNameEl    = document.getElementById('ai-img-name');
  const imgRemove    = document.getElementById('ai-img-remove');
  const proactiveBubble  = document.getElementById('ai-proactive-bubble');
  const proactiveText    = document.getElementById('ai-proactive-text');
  const proactiveClose   = document.getElementById('ai-proactive-close');
  const proactiveOpen    = document.getElementById('ai-proactive-open');

  if (!trigger || !panel) return;

  let isOpen = false;
  let pendingImage = null;  // { dataUrl: string, name: string } when user picks an image

  // ── Frustration words — mirrored from backend for frontend detection ──────
  const FRUSTRATION_WORDS = [
    'terrible','broken','wrong','fraud','scam','disappointed','useless',
    'awful','horrible','furious','angry','refund','cancel','never again',
    'worst','hate','ridiculous','unacceptable','disgusting',
  ];

  // ── Status indicator in the chat header ───────────────────────────────────
  function setStatus(state) {
    if (!statusLine) return;
    const map = {
      online:   '● Online &mdash; ready to help',
      thinking: '⏳ Thinking…',
      error:    '● Connection issue — retrying',
    };
    statusLine.innerHTML = map[state] || map.online;
    statusLine.style.color = state === 'error' ? '#EF4444' : state === 'thinking' ? '#F59E0B' : '';
  }

  // ── Open / close panel ────────────────────────────────────────────────────
  function openPanel() {
    isOpen = true;
    panel.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
    hideProcativeBubble();
    setTimeout(() => input?.focus(), 220);
  }
  function closePanel() {
    isOpen = false;
    panel.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }

  trigger.addEventListener('click', () => isOpen ? closePanel() : openPanel());
  closeBtn?.addEventListener('click', closePanel);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) closePanel(); });

  // ── Clear conversation ────────────────────────────────────────────────────
  clearBtn?.addEventListener('click', () => {
    if (!messages) return;
    messages.innerHTML = '<div class="ai-msg bot"><div class="ai-bubble">Chat cleared! ✨ Fresh start — what can I find for you today?</div></div>';
    fetchPost('/ai/chat/', { action: 'clear_history' }).catch(() => {});
    if (input) { input.value = ''; input.focus(); }
    if (charCount) charCount.textContent = '0/500';
    clearPendingImage();
  });

  // ── Export conversation as .txt ────────────────────────────────────────────
  exportBtn?.addEventListener('click', () => {
    fetchPost('/ai/chat/', { action: 'export' })
      .then(r => r.json())
      .then(data => {
        const text = data.text || 'No conversation to export.';
        const blob = new Blob([text], { type: 'text/plain' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href = url; a.download = 'trendmart-ai-chat.txt';
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
      })
      .catch(() => {});
  });

  // ── Character counter ─────────────────────────────────────────────────────
  const MAX_CHARS = 500;
  if (input && charCount) {
    input.addEventListener('input', () => {
      const len = input.value.length;
      charCount.textContent = `${len}/${MAX_CHARS}`;
      charCount.className = 'ai-char-count'
        + (len > MAX_CHARS * 0.85 ? ' near-limit' : '')
        + (len >= MAX_CHARS ? ' at-limit' : '');
    });
  }

  // ── Append message bubble ─────────────────────────────────────────────────
  function appendMsg(html, type) {
    const msg = document.createElement('div');
    msg.className = `ai-msg ${type}`;
    msg.innerHTML = `<div class="ai-bubble">${html}</div>`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
    return msg;
  }

  // ── Typing animation: reveal characters one-by-one (ChatGPT style) ───────
  function appendMsgTyped(fullText, type) {
    const msg = document.createElement('div');
    msg.className = `ai-msg ${type}`;
    const bubble = document.createElement('div');
    bubble.className = 'ai-bubble';
    msg.appendChild(bubble);
    messages.appendChild(msg);
    let i = 0;
    // Build the final formatted HTML first, then 'type' it as plaintext
    // to avoid injecting partial HTML tags. We reveal char-by-char on a
    // plaintext copy then swap to formatted HTML once complete.
    const chars = Array.from(fullText);  // handle Unicode safely
    function typeNext() {
      if (i < chars.length) {
        bubble.textContent += chars[i++];
        messages.scrollTop = messages.scrollHeight;
        setTimeout(typeNext, 11);
      } else {
        // Animation complete — now apply full Markdown formatting
        bubble.innerHTML = formatBotText(fullText);
        messages.scrollTop = messages.scrollHeight;
      }
    }
    typeNext();
    return msg;
  }

  // ── Markdown-like text formatter ──────────────────────────────────────────
  function formatBotText(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/~~(.*?)~~/g, '<s>$1</s>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(124,58,237,.1);padding:.1em .3em;border-radius:4px;font-size:.875em">$1</code>')
      .replace(/• /g, '&bull; ')
      // Convert product references 🔗[Name — $price](/products/slug/) to links
      .replace(/🔗\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--primary);text-decoration:underline;font-weight:600">🔗 $1</a>')
      // Regular markdown links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--primary);text-decoration:underline;font-weight:600">$1</a>')
      .replace(/\n/g, '<br>');
  }

  // ── Rich product cards from AI metadata ───────────────────────────────────
  // When the backend returns `products` array, render mini product cards
  // below the AI bubble so users can browse directly in the chat.
  function appendRichCards(msgEl, products) {
    if (!products || !products.length) return;
    const container = document.createElement('div');
    container.className = 'ai-product-cards';
    products.forEach(p => {
      const stars = '★'.repeat(Math.round(p.rating || 0)) + '☆'.repeat(5 - Math.round(p.rating || 0));
      const originalPriceHtml = p.original_price
        ? `<span class="original">$${p.original_price}</span>` : '';
      const card = document.createElement('a');
      card.href = p.url;
      card.className = 'ai-rich-card';
      card.setAttribute('aria-label', `View ${p.name} — $${p.price}`);
      card.innerHTML = `
        <img src="${p.image}" alt="${p.name}" class="ai-rich-card-img" loading="lazy">
        <div class="ai-rich-card-body">
          <div class="ai-rich-card-name">${p.name}</div>
          <div class="ai-rich-card-meta">${p.category}${p.brand ? ' · ' + p.brand : ''}</div>
          <div class="ai-rich-card-stars" aria-label="${p.rating} stars">${stars}</div>
          <div class="ai-rich-card-price">${originalPriceHtml}$${p.price}</div>
        </div>
        <button class="ai-rich-card-cart" aria-label="Add ${p.name} to cart" data-slug="${p.slug}" type="button" title="Add to cart">🛒</button>
      `;
      // Add-to-cart from rich card via AJAX
      card.querySelector('.ai-rich-card-cart').addEventListener('click', ev => {
        ev.preventDefault();
        const slug = ev.currentTarget.dataset.slug;
        fetchPost('/cart/add/', { product_slug: slug, quantity: 1 })
          .then(r => r.json())
          .then(d => {
            if (d.success) {
              Toast.show('Added to cart! 🛒', 'success');
              document.querySelectorAll('.cart-count').forEach(el => { el.textContent = d.cart_count; });
            }
          })
          .catch(() => Toast.show('Could not add to cart.', 'error'));
      });
      container.appendChild(card);
    });
    // Append cards inside the bot bubble
    const bubble = msgEl.querySelector('.ai-bubble');
    if (bubble) bubble.appendChild(container);
    messages.scrollTop = messages.scrollHeight;
  }

  // ── Typing indicator (animated dots) ─────────────────────────────────────
  function showTyping() {
    const t = document.createElement('div');
    t.className = 'ai-msg bot'; t.id = 'ai-typing-indicator';
    t.innerHTML = '<div class="ai-typing"><span></span><span></span><span></span></div><span class="ai-thinking-label">thinking…</span>';
    messages.appendChild(t); messages.scrollTop = messages.scrollHeight;
    return t;
  }

  // ── Dynamic quick-action buttons ──────────────────────────────────────────
  function updateQuickBtns(context) {
    const quickBtns = document.getElementById('ai-quick-btns');
    if (!quickBtns) return;
    const contextBtns = {
      product: ['➕ Add to cart', '⭐ Reviews', '📦 In stock?', '💰 Best price', '🔁 Compare'],
      order:   ['📍 Track order', '↩️ Return item', '🧾 Invoice', '📞 Support'],
      size:    ['📏 My measurements', '👟 Shoe size guide', '👕 Clothing guide'],
      default: ['🔥 Hot deals', '📦 My orders', '💡 Recommend me', '📏 Find my size', '↩️ Returns', '🏷️ Best price'],
    };
    const btns = contextBtns[context] || contextBtns.default;
    quickBtns.innerHTML = btns.map(b => `<button class="ai-quick-btn">${b}</button>`).join('');
    quickBtns.querySelectorAll('.ai-quick-btn').forEach(btn => {
      btn.addEventListener('click', () => sendMessage(btn.textContent.trim()));
    });
  }

  // ── Sentiment detection (local) — mirrors backend _FRUSTRATION_WORDS ──────
  function detectFrustration(text) {
    const lower = text.toLowerCase();
    return FRUSTRATION_WORDS.some(w => lower.includes(w));
  }

  // ── Image handling ────────────────────────────────────────────────────────
  function clearPendingImage() {
    pendingImage = null;
    if (imgPreview) imgPreview.style.display = 'none';
    if (imgThumb) imgThumb.src = '';
    if (imgNameEl) imgNameEl.textContent = '';
    if (imgFileInput) imgFileInput.value = '';
  }

  imgBtn?.addEventListener('click', () => imgFileInput?.click());
  imgRemove?.addEventListener('click', clearPendingImage);

  imgFileInput?.addEventListener('change', () => {
    const file = imgFileInput.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { Toast.show('Image too large (max 5 MB).', 'error'); return; }
    const reader = new FileReader();
    reader.onload = ev => {
      pendingImage = { dataUrl: ev.target.result, name: file.name };
      if (imgThumb) imgThumb.src = ev.target.result;
      if (imgNameEl) imgNameEl.textContent = file.name;
      if (imgPreview) imgPreview.style.display = 'flex';
    };
    reader.readAsDataURL(file);
  });

  // ── Voice input via Web Speech API ───────────────────────────────────────
  let recognition = null;
  if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = ev => {
      const transcript = ev.results[0][0].transcript;
      if (input) {
        input.value = transcript;
        // Trigger char count update
        input.dispatchEvent(new Event('input'));
      }
      micBtn?.classList.remove('recording');
      micBtn?.setAttribute('aria-label', 'Start voice input');
    };
    recognition.onerror  = () => { micBtn?.classList.remove('recording'); };
    recognition.onend    = () => { micBtn?.classList.remove('recording'); };

    micBtn?.addEventListener('click', () => {
      if (micBtn.classList.contains('recording')) {
        recognition.stop();
        micBtn.classList.remove('recording');
        micBtn.setAttribute('aria-label', 'Start voice input');
      } else {
        recognition.start();
        micBtn.classList.add('recording');
        micBtn.setAttribute('aria-label', 'Stop recording');
      }
    });
  } else {
    // Browser does not support Web Speech API — hide mic button
    if (micBtn) micBtn.style.display = 'none';
  }

  // ── Core send function ────────────────────────────────────────────────────
  function sendMessage(text) {
    const msgText = (text || input?.value || '').trim();
    if (!msgText && !pendingImage) return;

    // Show user message in UI
    const displayText = msgText
      ? msgText.replace(/</g, '&lt;')
      : '📷 <em>Image uploaded for visual search</em>';
    if (pendingImage) {
      // Show image preview bubble
      const imgMsg = document.createElement('div');
      imgMsg.className = 'ai-msg user';
      imgMsg.innerHTML = `<div class="ai-bubble"><img src="${pendingImage.dataUrl}" alt="Uploaded image" style="max-width:140px;border-radius:8px;display:block;margin-bottom:.35rem">${msgText ? '<br>' + msgText.replace(/</g, '&lt;') : ''}</div>`;
      messages.appendChild(imgMsg);
    } else {
      appendMsg(displayText, 'user');
    }

    if (input) { input.value = ''; if (charCount) charCount.textContent = `0/${MAX_CHARS}`; }
    sendBtn?.classList.add('sending');
    setTimeout(() => sendBtn?.classList.remove('sending'), 400);
    setStatus('thinking');

    // Build request payload
    const payload = { message: msgText };
    if (pendingImage) payload.image_data = pendingImage.dataUrl;
    if (detectFrustration(msgText)) payload.is_frustrated = true;

    const imageForCard = pendingImage ? pendingImage.dataUrl : null;  // hold ref before clearing
    clearPendingImage();

    const typing = showTyping();
    fetchPost('/ai/chat/', payload)
      .then(r => r.json())
      .then(data => {
        typing.remove();
        setStatus('online');
        // Typing animation for bot reply
        const replyText = data.reply || "Sorry, I couldn't process that.";
        const botMsg = appendMsgTyped(replyText, 'bot');
        // Wait for typing animation then append rich cards
        const cardDelay = Math.min(replyText.length * 12 + 300, 3500);
        setTimeout(() => appendRichCards(botMsg, data.products), cardDelay);
        // Update quick-action context
        const lowerMsg = msgText.toLowerCase();
        if (lowerMsg.match(/order|track|delivery|ship/)) updateQuickBtns('order');
        else if (lowerMsg.match(/size|measurements|fit|eu|uk size/)) updateQuickBtns('size');
        else if (lowerMsg.match(/product|show|find|search|recommend/)) updateQuickBtns('product');
        else updateQuickBtns('default');
      })
      .catch(() => {
        typing.remove();
        setStatus('error');
        setTimeout(() => setStatus('online'), 4000);
        appendMsg("Sorry, I'm having trouble connecting. Please try again! 🔄", 'bot');
      });
  }

  sendBtn?.addEventListener('click', () => sendMessage(input?.value || ''));
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });

  // Wire up initial quick buttons
  document.querySelectorAll('.ai-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.textContent.trim()));
  });

  // ── Proactive contextual bubble ───────────────────────────────────────────
  // Shows a context-aware prompt to nudge users to interact with the AI.
  // Fires once per page, only if the chat panel is closed.
  let proactiveFired = false;
  function showProactiveBubble(msg, delayMs) {
    if (proactiveFired || isOpen) return;
    setTimeout(() => {
      if (isOpen || proactiveFired) return;
      proactiveFired = true;
      if (proactiveText) proactiveText.textContent = msg;
      if (proactiveBubble) proactiveBubble.style.display = 'block';
    }, delayMs);
  }
  function hideProcativeBubble() {
    if (proactiveBubble) proactiveBubble.style.display = 'none';
  }
  proactiveClose?.addEventListener('click', hideProcativeBubble);
  proactiveOpen?.addEventListener('click', () => { hideProcativeBubble(); openPanel(); });

  // Detect page context and fire the right proactive message
  const path = window.location.pathname;
  if (path.includes('/cart/')) {
    // On cart page after 30s — suggest accessories
    showProactiveBubble('💬 Need help finding accessories for items in your cart?', 30000);
  } else if (path.includes('/search/')) {
    // On search page after 10s — offer AI search help
    showProactiveBubble('🧠 Try our AI search — describe what you need in plain English!', 10000);
  } else if (path.includes('/products/')) {
    // On a product page after 60s idle — suggest comparison
    showProactiveBubble('❓ Questions about this product? I can compare it with similar items.', 60000);
  } else if (path === '/' || path === '') {
    // Homepage — general welcome after 20s
    showProactiveBubble('👋 Hi! I\'m TrendMart AI — I can help you find amazing deals. What are you looking for today?', 20000);
  }
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

// ── Scroll to Top ───────────────────────────────────────────
function initScrollToTop() {
  const btn = document.getElementById('scroll-top-btn');
  if (!btn) return;
  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 400);
  }, { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ── Price Range Slider ──────────────────────────────────────
function initPriceSlider() {
  const wrapper = document.getElementById('price-slider-wrapper');
  if (!wrapper) return;
  const minInput = wrapper.querySelector('[data-role="min"]');
  const maxInput = wrapper.querySelector('[data-role="max"]');
  const rangeEl = wrapper.querySelector('.price-slider-range');
  const minDisplay = wrapper.querySelector('[data-display="min"]');
  const maxDisplay = wrapper.querySelector('[data-display="max"]');
  const formMin = document.querySelector('input[name="min_price"]');
  const formMax = document.querySelector('input[name="max_price"]');

  if (!minInput || !maxInput) return;

  const absMin = parseFloat(minInput.min) || 0;
  const absMax = parseFloat(maxInput.max) || 5000;

  function updateSlider() {
    let min = parseFloat(minInput.value);
    let max = parseFloat(maxInput.value);
    if (min > max) { const t = min; min = max; max = t; minInput.value = min; maxInput.value = max; }
    const leftPct = ((min - absMin) / (absMax - absMin)) * 100;
    const rightPct = ((max - absMin) / (absMax - absMin)) * 100;
    rangeEl.style.left = leftPct + '%';
    rangeEl.style.width = (rightPct - leftPct) + '%';
    if (minDisplay) minDisplay.textContent = '$' + Math.round(min);
    if (maxDisplay) maxDisplay.textContent = '$' + Math.round(max);
    if (formMin) formMin.value = Math.round(min);
    if (formMax) formMax.value = Math.round(max);
  }

  minInput.addEventListener('input', updateSlider);
  maxInput.addEventListener('input', updateSlider);
  updateSlider();
}

// ── Quick View Modal ────────────────────────────────────────
function initQuickView() {
  const overlay = document.getElementById('quick-view-overlay');
  const closeBtn = document.getElementById('quick-view-close');
  const body = document.getElementById('quick-view-body');
  const title = document.getElementById('quick-view-title');
  if (!overlay) return;

  function openQuickView(slug, productName) {
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    if (title) title.textContent = productName || 'Product Details';
    if (body) body.innerHTML = `<div class="quick-view-img"><div class="skeleton skeleton-img"></div></div><div><div class="skeleton skeleton-text medium" style="margin-bottom:8px"></div><div class="skeleton skeleton-text short" style="margin-bottom:16px"></div><div class="skeleton skeleton-text medium" style="height:80px"></div></div>`;

    fetch(`/products/${slug}/?quickview=1`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const imgEl = doc.querySelector('.product-detail-img img, .product-images img');
        const priceEl = doc.querySelector('.price-current');
        const brandEl = doc.querySelector('.product-detail-brand');
        const descEl = doc.querySelector('.product-detail-description');
        const ratingEl = doc.querySelector('.avg-rating-display');
        const detailUrl = `/products/${slug}/`;

        if (body) body.innerHTML = `
          <div class="quick-view-img">${imgEl ? `<img src="${imgEl.src}" alt="${imgEl.alt}" loading="lazy">` : '<div class="skeleton skeleton-img"></div>'}</div>
          <div>
            ${brandEl ? `<p style="color:var(--primary);font-weight:700;font-size:.8125rem;text-transform:uppercase;margin-bottom:.5rem">${brandEl.textContent.trim()}</p>` : ''}
            ${priceEl ? `<p style="font-size:1.75rem;font-weight:900;color:var(--dark);margin-bottom:.75rem">${priceEl.textContent.trim()}</p>` : ''}
            ${ratingEl ? `<p style="color:var(--secondary);margin-bottom:.75rem">★ ${ratingEl.textContent.trim()}</p>` : ''}
            ${descEl ? `<p style="color:var(--text-light);font-size:.9375rem;line-height:1.7;margin-bottom:1.25rem">${descEl.textContent.trim().substring(0, 200)}${descEl.textContent.trim().length > 200 ? '…' : ''}</p>` : ''}
            <a href="${detailUrl}" class="btn btn-primary" style="margin-bottom:.75rem;display:inline-block">View Full Details</a>
          </div>`;
      })
      .catch(() => {
        if (body) body.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:2rem"><p>Could not load product details.</p><a href="/products/${slug}/" class="btn btn-primary" style="margin-top:1rem">View Product</a></div>`;
      });
  }

  function closeQuickView() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  closeBtn?.addEventListener('click', closeQuickView);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeQuickView(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && overlay.classList.contains('open')) closeQuickView(); });

  document.addEventListener('click', e => {
    const btn = e.target.closest('[data-quickview]');
    if (btn) {
      e.preventDefault();
      openQuickView(btn.dataset.quickview, btn.dataset.productName);
    }
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

// ── Multi-Currency Converter ─────────────────────────────────
function initCurrencySelector() {
  const btn = document.getElementById('currency-btn');
  const dropdown = document.getElementById('currency-dropdown');
  const flagEl = document.getElementById('currency-flag');
  const codeEl = document.getElementById('currency-code');
  if (!btn || !dropdown) return;

  const STORAGE_KEY = 'trendmart-currency';
  let current = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') || { code: 'USD', symbol: '$', rate: 1, flag: '🇺🇸' };

  function applyConversion() {
    flagEl.textContent = current.flag;
    codeEl.textContent = current.code;
    document.querySelectorAll('.currency-opt').forEach(o => {
      o.classList.toggle('active', o.dataset.currency === current.code);
    });
    document.querySelectorAll('[data-base-price]').forEach(el => {
      const base = parseFloat(el.dataset.basePrice);
      const converted = (base * current.rate).toFixed(current.rate >= 100 ? 0 : 2);
      el.textContent = current.symbol + converted;
    });
    document.querySelectorAll('.price-current, .price-original, .rv-card-price, .ai-product-card-price').forEach(el => {
      const raw = el.textContent.replace(/[^0-9.]/g, '');
      const base = parseFloat(el.dataset.usdPrice || raw);
      if (!el.dataset.usdPrice) el.dataset.usdPrice = raw;
      if (!base) return;
      const converted = (base * current.rate).toFixed(current.rate >= 100 ? 0 : 2);
      el.textContent = current.symbol + converted;
    });
  }

  function setCurrency(opt) {
    current = { code: opt.dataset.currency, symbol: opt.dataset.symbol, rate: parseFloat(opt.dataset.rate), flag: opt.dataset.flag };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
    dropdown.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    applyConversion();
    Toast.show(`Currency changed to ${current.code}`, 'info', 2500);
  }

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = dropdown.classList.contains('open');
    dropdown.classList.toggle('open', !isOpen);
    btn.setAttribute('aria-expanded', String(!isOpen));
  });
  document.addEventListener('click', () => { dropdown.classList.remove('open'); btn.setAttribute('aria-expanded', 'false'); });
  dropdown.querySelectorAll('.currency-opt').forEach(opt => opt.addEventListener('click', (e) => { e.stopPropagation(); setCurrency(opt); }));

  setTimeout(applyConversion, 100);
}

// ── PWA Install Banner ───────────────────────────────────────
function initPWAInstall() {
  let deferredPrompt = null;
  if (localStorage.getItem('pwa-dismissed')) return;

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const banner = document.createElement('div');
    banner.className = 'pwa-install-banner';
    banner.innerHTML = `
      <p>📱 Install TrendMart for a faster, app-like experience!</p>
      <div class="pwa-actions">
        <button class="pwa-install-btn">Install App</button>
        <button class="pwa-dismiss-btn">Not now</button>
      </div>`;
    document.body.appendChild(banner);
    setTimeout(() => banner.classList.add('show'), 3000);
    banner.querySelector('.pwa-install-btn').addEventListener('click', async () => {
      banner.remove();
      deferredPrompt.prompt();
      const result = await deferredPrompt.userChoice;
      if (result.outcome === 'accepted') Toast.show('TrendMart installed! 🎉', 'success');
      deferredPrompt = null;
    });
    banner.querySelector('.pwa-dismiss-btn').addEventListener('click', () => {
      banner.classList.remove('show');
      setTimeout(() => banner.remove(), 350);
      localStorage.setItem('pwa-dismissed', '1');
    });
  });
}

// ── Recently Viewed Strip (client-side) ──────────────────────
const RecentlyViewed = {
  STORAGE_KEY: 'tm-recently-viewed',
  MAX: 10,

  get() {
    try { return JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '[]'); } catch { return []; }
  },

  add(product) {
    if (!product || !product.slug) return;
    let items = this.get().filter(p => p.slug !== product.slug);
    items.unshift(product);
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(items.slice(0, this.MAX)));
  },

  renderStrip(currentSlug) {
    const items = this.get().filter(p => p.slug !== currentSlug);
    if (!items.length) return;
    const container = document.getElementById('recently-viewed-strip');
    if (!container) return;
    container.innerHTML = `
      <h3>👁️ Recently Viewed</h3>
      <div class="rv-scroll">
        ${items.slice(0, 8).map(p => `
          <a href="/products/${p.slug}/" class="rv-card" aria-label="${p.name}">
            <img src="${p.img}" alt="${p.name}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=130&h=100&fit=crop'">
            <div class="rv-card-body">
              <div class="rv-card-name">${p.name}</div>
              <div class="rv-card-price">${p.price}</div>
            </div>
          </a>`).join('')}
      </div>`;
    container.style.display = 'block';
  },

  trackCurrentProduct() {
    const productData = window.__productData;
    if (!productData) return;
    this.add(productData);
    this.renderStrip(productData.slug);
  }
};

// =============================================================================
// ── NEW FEATURE JS (112-Point Enhancement) ─────────────────────────────────
// Author: George Papasotiriou — TrendMart, March 2026
// =============================================================================

// ── Mini Cart Slide-In Drawer ────────────────────────────────────────────────
// Opens from the right when user clicks the cart icon or adds a product.
// Uses display:none/flex controlled by JS so the drawer is fully hidden until
// needed — this is bulletproof even when position:fixed is affected by parent
// CSS transforms (which can happen near canvas/animation elements).
function initMiniCart() {
  const overlay  = document.getElementById('mini-cart-overlay');
  const drawer   = document.getElementById('mini-cart-drawer');
  const closeBtn = document.getElementById('mini-cart-close');
  const cartIcon = document.getElementById('nav-cart-btn'); // cart icon in navbar
  if (!drawer) return;

  let isOpen = false;

  function openDrawer() {
    if (isOpen) return;
    isOpen = true;

    // Step 1: make elements visible in the DOM (but still off-screen via transform)
    drawer.style.display = 'flex';
    if (overlay) overlay.style.display = 'block';

    // Step 2: fetch fresh cart data
    fetch('/cart/mini/')
      .then(r => r.json())
      .then(data => {
        renderMiniCart(data);
        // Step 3: double-rAF ensures the browser has painted with display:flex
        // before we add .open, so the CSS transition fires correctly
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            overlay?.classList.add('open');
            drawer.classList.add('open');
            drawer.setAttribute('aria-hidden', 'false');
            closeBtn?.focus();
          });
        });
      })
      .catch(() => {
        isOpen = false;
        drawer.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
      });
  }

  function closeDrawer() {
    if (!isOpen) return;
    isOpen = false;

    // Remove .open — CSS transition slides drawer back to the right
    overlay?.classList.remove('open');
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');

    // After transition completes, hide with display:none so it's fully out of layout
    setTimeout(() => {
      drawer.style.display = 'none';
      if (overlay) overlay.style.display = 'none';
    }, 350); // slightly longer than the 320ms CSS transition
  }

  function renderMiniCart(data) {
    const itemsEl = document.getElementById('mini-cart-items');
    const totalEl = document.getElementById('mini-cart-total-val');
    const countEl = document.getElementById('mini-cart-count');
    if (!itemsEl) return;

    if (!data.items || data.items.length === 0) {
      itemsEl.innerHTML = `
        <div style="text-align:center;padding:3rem 1rem">
          <div style="font-size:3rem;margin-bottom:.75rem">🛒</div>
          <p style="color:var(--text-light);font-size:.9375rem">Your cart is empty</p>
          <a href="/products/" class="btn btn-primary" style="margin-top:1rem;display:inline-block">Browse Products</a>
        </div>`;
    } else {
      itemsEl.innerHTML = data.items.map(item => `
        <div class="mini-cart-item">
          <img src="${item.image}" alt="${item.name}" class="mini-cart-img" loading="lazy">
          <div class="mini-cart-item-body">
            <div class="mini-cart-name">${item.name}</div>
            ${item.size ? `<div class="mini-cart-meta">Size: ${item.size}</div>` : ''}
            <div class="mini-cart-meta">Qty: ${item.quantity}</div>
            <div class="mini-cart-price">$${parseFloat(item.subtotal).toFixed(2)}</div>
          </div>
        </div>
      `).join('');
    }

    if (totalEl) totalEl.textContent = `$${parseFloat(data.total || 0).toFixed(2)}`;
    if (countEl) countEl.textContent = data.count;
  }

  // Close on overlay click, close button, or Escape key
  overlay?.addEventListener('click', closeDrawer);
  closeBtn?.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen) closeDrawer(); });

  // Cart navbar icon: intercept click to open drawer instead of navigating
  cartIcon?.addEventListener('click', e => {
    e.preventDefault(); // stop navigation to /cart/ page
    openDrawer();
  });

  // Also open after every successful add-to-cart AJAX
  document.addEventListener('cart:added', openDrawer);
}

// ── Instant Search Overlay (live-as-you-type) ────────────────────────────────
// Fetches product suggestions as user types; supports keyboard navigation.
function initInstantSearch() {
  const searchForms = document.querySelectorAll('.nav-search-form, .search-form-wrap');
  searchForms.forEach(form => {
    if (!form) return;
    const input = form.querySelector('input[name="q"]');
    if (!input) return;

    // Build the dropdown DOM
    const dropdown = document.createElement('div');
    dropdown.className = 'search-dropdown';
    dropdown.setAttribute('role', 'listbox');
    dropdown.setAttribute('aria-label', 'Search suggestions');
    form.style.position = 'relative';
    form.appendChild(dropdown);

    const backdrop = document.createElement('div');
    backdrop.className = 'search-overlay-backdrop';
    document.body.appendChild(backdrop);

    // Search history from localStorage
    const HISTORY_KEY = 'tm_search_history';
    function getHistory() {
      try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch { return []; }
    }
    function addToHistory(q) {
      if (!q) return;
      const h = getHistory().filter(x => x !== q).slice(0, 4);
      h.unshift(q);
      try { localStorage.setItem(HISTORY_KEY, JSON.stringify(h)); } catch {}
    }

    function showDropdown() {
      dropdown.classList.add('active');
      backdrop.classList.add('active');
    }
    function hideDropdown() {
      dropdown.classList.remove('active');
      backdrop.classList.remove('active');
    }

    let debounceTimer;
    let highlighted = -1;

    function renderHistory() {
      const h = getHistory();
      if (!h.length) { hideDropdown(); return; }
      dropdown.innerHTML = `
        <div class="search-dropdown-section">
          <div class="search-dropdown-label">Recent Searches</div>
          <div style="padding:.375rem .875rem">
            ${h.map(term => `<button class="search-history-chip" type="button" aria-label="Search for ${term}">🕐 ${term}</button>`).join('')}
          </div>
        </div>`;
      dropdown.querySelectorAll('.search-history-chip').forEach(btn => {
        btn.addEventListener('click', () => { input.value = btn.textContent.replace('🕐 ', '').trim(); form.submit(); });
      });
      showDropdown();
    }

    function renderResults(results) {
      if (!results.length) { hideDropdown(); return; }
      dropdown.innerHTML = `
        <div class="search-dropdown-section">
          <div class="search-dropdown-label">Products</div>
          ${results.map((p, i) => `
            <a href="/products/${p.slug}/" class="search-dropdown-item" role="option" aria-selected="false" data-idx="${i}">
              <img src="${p.image}" alt="${p.name}" class="search-dropdown-item-img" loading="lazy">
              <div>
                <div class="search-dropdown-item-name">${p.name}</div>
                <div class="search-dropdown-item-meta">${p.category}${p.brand ? ' · ' + p.brand : ''}</div>
              </div>
              <span class="search-dropdown-item-price">$${p.price}</span>
            </a>`).join('')}
        </div>`;
      highlighted = -1;
      showDropdown();
    }

    input.addEventListener('focus', () => {
      if (!input.value.trim()) renderHistory();
    });

    input.addEventListener('input', () => {
      const q = input.value.trim();
      clearTimeout(debounceTimer);
      if (!q) { renderHistory(); return; }
      debounceTimer = setTimeout(() => {
        fetch(`/search/autocomplete/?q=${encodeURIComponent(q)}`)
          .then(r => r.json())
          .then(data => renderResults(data.results || []))
          .catch(() => hideDropdown());
      }, 220);  // 220ms debounce — responsive but not spammy
    });

    // Keyboard navigation (↑ ↓ Enter Escape)
    input.addEventListener('keydown', e => {
      const items = [...dropdown.querySelectorAll('.search-dropdown-item')];
      if (e.key === 'ArrowDown') {
        e.preventDefault(); highlighted = Math.min(highlighted + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle('highlighted', i === highlighted));
        items[highlighted]?.focus();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault(); highlighted = Math.max(highlighted - 1, -1);
        items.forEach((el, i) => el.classList.toggle('highlighted', i === highlighted));
        if (highlighted === -1) input.focus();
        else items[highlighted]?.focus();
      } else if (e.key === 'Escape') {
        hideDropdown(); input.blur();
      }
    });

    backdrop.addEventListener('click', hideDropdown);

    form.addEventListener('submit', () => {
      addToHistory(input.value.trim());
      hideDropdown();
    });
  });
}

// ── Product Image Zoom (Amazon-style magnifier) ────────────────────────────
// Hover over the main product image to see a magnified panel beside it.
function initImageZoom() {
  const imgWrap = document.getElementById('product-zoom-wrap');
  if (!imgWrap) return;
  const img = imgWrap.querySelector('img');
  if (!img) return;

  // Create zoom lens and result panel
  const lens = document.createElement('div');
  lens.className = 'zoom-lens';
  lens.setAttribute('aria-hidden', 'true');
  imgWrap.appendChild(lens);

  const resultPanel = document.createElement('div');
  resultPanel.className = 'zoom-result-panel';
  const resultImg = document.createElement('img');
  resultImg.src = img.src;
  resultImg.alt = '';
  resultPanel.appendChild(resultImg);
  imgWrap.parentElement.style.position = 'relative';
  imgWrap.parentElement.appendChild(resultPanel);

  const ZOOM = 2.5;  // Magnification factor
  const LENS_SIZE = 120;  // Lens square size in px

  lens.style.cssText += `width:${LENS_SIZE}px;height:${LENS_SIZE}px`;

  function moveLens(e) {
    const rect = imgWrap.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const lx = Math.max(0, Math.min(x - LENS_SIZE / 2, rect.width - LENS_SIZE));
    const ly = Math.max(0, Math.min(y - LENS_SIZE / 2, rect.height - LENS_SIZE));
    lens.style.left = lx + 'px';
    lens.style.top  = ly + 'py';
    lens.style.top  = ly + 'px';

    // Position the zoomed image inside the result panel
    const scaleX = resultPanel.offsetWidth / (LENS_SIZE / ZOOM);
    const scaleY = resultPanel.offsetHeight / (LENS_SIZE / ZOOM);
    resultImg.style.width  = img.naturalWidth  * (ZOOM * resultPanel.offsetWidth / img.offsetWidth) + 'px';
    resultImg.style.height = img.naturalHeight * (ZOOM * resultPanel.offsetHeight / img.offsetHeight) + 'px';
    resultImg.style.left = -(lx * ZOOM * resultPanel.offsetWidth / img.offsetWidth) + 'px';
    resultImg.style.top  = -(ly * ZOOM * resultPanel.offsetHeight / img.offsetHeight) + 'px';
  }

  imgWrap.addEventListener('mouseenter', () => {
    lens.classList.add('visible');
    resultPanel.style.display = 'block';
  });
  imgWrap.addEventListener('mouseleave', () => {
    lens.classList.remove('visible');
    resultPanel.style.display = 'none';
  });
  imgWrap.addEventListener('mousemove', moveLens);
}

// ── Sticky Add-to-Cart Bar ───────────────────────────────────────────────────
// Appears when the main CTA scrolls out of view on product detail pages.
function initStickyCartBar() {
  const mainCta = document.getElementById('main-atc-btn');  // main add-to-cart button
  const stickyBar = document.getElementById('sticky-cart-bar');
  if (!mainCta || !stickyBar) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      stickyBar.classList.toggle('visible', !entry.isIntersecting);
    });
  }, { threshold: 0, rootMargin: '0px 0px -60px 0px' });
  observer.observe(mainCta);
}

// ── Password Strength Meter ──────────────────────────────────────────────────
// Shows a coloured progress bar and label as the user types their password.
function initPasswordStrength() {
  const pwdInputs = document.querySelectorAll('input[type="password"][data-strength]');
  pwdInputs.forEach(input => {
    const wrap = document.createElement('div');
    wrap.className = 'pwd-strength-wrap';
    wrap.innerHTML = '<div class="pwd-strength-bar"><div class="pwd-strength-fill" id="pwd-fill"></div></div><div class="pwd-strength-label" id="pwd-label" aria-live="polite"></div>';
    input.insertAdjacentElement('afterend', wrap);
    const fill  = wrap.querySelector('.pwd-strength-fill');
    const label = wrap.querySelector('.pwd-strength-label');

    input.addEventListener('input', () => {
      const v = input.value;
      let score = 0;
      if (v.length >= 8) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      const levels = [
        { w: '0%', bg: 'transparent', text: '' },
        { w: '25%', bg: '#EF4444', text: 'Weak' },
        { w: '50%', bg: '#F59E0B', text: 'Fair' },
        { w: '75%', bg: '#3B82F6', text: 'Good' },
        { w: '100%', bg: '#10B981', text: 'Strong' },
      ];
      const level = levels[score] || levels[0];
      fill.style.width      = level.w;
      fill.style.background = level.bg;
      label.textContent     = level.text;
      label.style.color     = level.bg;
    });
  });
}

// ── GDPR Cookie Consent Banner ────────────────────────────────────────────────
// Non-blocking bottom banner; stores consent in localStorage.
function initCookieBanner() {
  const banner = document.getElementById('cookie-banner');
  if (!banner) return;
  if (localStorage.getItem('tm_cookie_consent')) return;  // already consented

  setTimeout(() => banner.classList.add('show'), 800);

  document.getElementById('cookie-accept')?.addEventListener('click', () => {
    localStorage.setItem('tm_cookie_consent', '1');
    banner.classList.remove('show');
    setTimeout(() => banner.remove(), 400);
  });
  document.getElementById('cookie-decline')?.addEventListener('click', () => {
    localStorage.setItem('tm_cookie_consent', '0');
    banner.classList.remove('show');
    setTimeout(() => banner.remove(), 400);
  });
}

// ── Notification Bell (AJAX unread count) ─────────────────────────────────
// Polls the server for unread notifications count and updates the badge.
function initNotificationBell() {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;

  function refreshCount() {
    fetch('/notifications/count/')
      .then(r => r.json())
      .then(data => {
        if (data.count > 0) {
          badge.textContent = data.count > 99 ? '99+' : data.count;
          badge.classList.add('visible');
        } else {
          badge.classList.remove('visible');
        }
      })
      .catch(() => {});
  }
  refreshCount();
  setInterval(refreshCount, 60000);  // refresh every 60 seconds
}

// ── Newsletter Subscription (AJAX) ───────────────────────────────────────────
function initNewsletter() {
  document.querySelectorAll('.newsletter-form').forEach(form => {
    form.addEventListener('submit', e => {
      e.preventDefault();
      const email = form.querySelector('input[name="email"]')?.value.trim();
      const name  = form.querySelector('input[name="name"]')?.value.trim() || '';
      if (!email) return;
      fetchPost('/newsletter/subscribe/', { email, name })
        .then(r => r.json())
        .then(data => {
          if (data.success) Toast.show(data.message, 'success');
          else Toast.show(data.error || 'Error subscribing.', 'error');
          form.reset();
        })
        .catch(() => Toast.show('Could not subscribe. Try again.', 'error'));
    });
  });
}

// ── Promo Code Application (AJAX) ────────────────────────────────────────────
function initPromoCode() {
  const form = document.getElementById('promo-form');
  if (!form) return;
  form.addEventListener('submit', e => {
    e.preventDefault();
    const code = form.querySelector('input[name="promo_code"]')?.value.trim();
    if (!code) return;
    fetchPost('/cart/promo/', { code })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          Toast.show(data.message, 'success');
          // Update cart total display
          const totalEl = document.getElementById('cart-total-display');
          if (totalEl) totalEl.textContent = `$${data.new_total.toFixed(2)}`;
          const discountEl = document.getElementById('promo-discount-display');
          if (discountEl) { discountEl.textContent = `-$${data.discount.toFixed(2)}`; discountEl.style.display = 'block'; }
        } else {
          Toast.show(data.error || 'Invalid code.', 'error');
        }
      })
      .catch(() => Toast.show('Could not apply code.', 'error'));
  });
}

// ── AJAX Cart Quantity Update ─────────────────────────────────────────────────
// Updates item quantity without page reload using +/- buttons.
function initAjaxCartQty() {
  document.querySelectorAll('[data-cart-qty-form]').forEach(form => {
    const qtyInput = form.querySelector('input[name="quantity"]');
    const plusBtn  = form.querySelector('[data-qty-plus]');
    const minusBtn = form.querySelector('[data-qty-minus]');

    function updateQty(newQty) {
      if (newQty < 1) return;
      const itemId = form.dataset.itemId;
      fetchPost(`/cart/update/${itemId}/`, { quantity: newQty })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            if (qtyInput) qtyInput.value = newQty;
            // Update totals in the UI (view returns 'subtotal' key)
            const subtotalEl = document.getElementById(`subtotal-${itemId}`);
            const sub = parseFloat(data.item_subtotal ?? data.subtotal ?? 0);
            if (subtotalEl) subtotalEl.textContent = `$${sub.toFixed(2)}`;
            const totalEl = document.getElementById('cart-total-display');
            if (totalEl) totalEl.textContent = `$${parseFloat(data.cart_total || 0).toFixed(2)}`;
            document.querySelectorAll('.cart-count').forEach(el => { el.textContent = data.cart_count; });
          }
        })
        .catch(() => {});
    }

    plusBtn?.addEventListener('click', () => updateQty(parseInt(qtyInput?.value || 1) + 1));
    minusBtn?.addEventListener('click', () => updateQty(Math.max(1, parseInt(qtyInput?.value || 1) - 1)));
  });
}

// ── Focus trap for modals ─────────────────────────────────────────────────────
// Ensures Tab cycles only within an open modal (WCAG 2.1 AA).
function trapFocus(element) {
  const focusable = element.querySelectorAll(
    'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last  = focusable[focusable.length - 1];
  element.addEventListener('keydown', e => {
    if (e.key !== 'Tab') return;
    if (e.shiftKey) {
      if (document.activeElement === first) { e.preventDefault(); last?.focus(); }
    } else {
      if (document.activeElement === last) { e.preventDefault(); first?.focus(); }
    }
  });
}

// Apply focus trap to the auth modal when it opens
function initFocusTrap() {
  const modal = document.getElementById('auth-modal');
  if (modal) {
    const observer = new MutationObserver(() => {
      if (modal.classList.contains('active')) {
        trapFocus(modal);
        // Set focus to first focusable element
        modal.querySelector('input, button')?.focus();
      }
    });
    observer.observe(modal, { attributes: true, attributeFilter: ['class'] });
  }
}

// ── Social Share buttons ────────────────────────────────────────────────────
function initSocialShare() {
  document.querySelectorAll('[data-share]').forEach(btn => {
    btn.addEventListener('click', () => {
      const url  = encodeURIComponent(window.location.href);
      const text = encodeURIComponent(document.title);
      const platform = btn.dataset.share;
      const urls = {
        whatsapp: `https://wa.me/?text=${text}%20${url}`,
        twitter:  `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
        facebook: `https://www.facebook.com/sharer/sharer.php?u=${url}`,
        copy:     null,
      };
      if (platform === 'copy') {
        navigator.clipboard.writeText(window.location.href)
          .then(() => Toast.show('Link copied! 🔗', 'success'))
          .catch(() => {});
      } else if (urls[platform]) {
        window.open(urls[platform], '_blank', 'width=600,height=400,noopener,noreferrer');
      }
    });
  });
}

// ── Dispatch cart:added event from add-to-cart responses ──────────────────
// Patches the existing fetchPost-based cart AJAX to fire a custom event
// that the mini cart drawer listens to.
function patchCartForMiniCart() {
  // Override the cart form submit handler to open the mini cart
  document.querySelectorAll('[data-add-to-cart]').forEach(form => {
    form.addEventListener('submit', () => {
      setTimeout(() => document.dispatchEvent(new CustomEvent('cart:added')), 400);
    });
  });
}

// ── Init all ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initHeroParticles();
  Toast.init();
  initDropdowns();
  initMobileNav();
  initScrollToTop();
  initSearchAutocomplete();
  initInstantSearch();
  initCart();
  initWishlist();
  initStarRating();
  initRatingForm();
  initAIChat();
  initFilterCollapse();
  initSizeSelector();
  initPriceSlider();
  initQuickView();
  initActiveCategoryNav();
  initDjangoMessages();
  initCurrencySelector();
  initPWAInstall();
  RecentlyViewed.trackCurrentProduct();
  // New feature initialisers
  initMiniCart();
  initImageZoom();
  initStickyCartBar();
  initPasswordStrength();
  initCookieBanner();
  initNotificationBell();
  initNewsletter();
  initPromoCode();
  initAjaxCartQty();
  initFocusTrap();
  initSocialShare();
  patchCartForMiniCart();
});
