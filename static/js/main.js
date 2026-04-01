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

// ── Instant Search Overlay ──────────────────────────────────
// Full-screen search overlay that shows product cards, category chips,
// brand chips, trending terms, and "did you mean?" corrections live as the
// user types. Keyboard-navigable (↑↓ Enter Escape). No extra requests.
function initSearchAutocomplete() {
  const input    = document.getElementById('search-input');
  const dropdown = document.getElementById('search-autocomplete');
  if (!input || !dropdown) return;

  let debounceTimer;
  let currentFocusIndex = -1;
  let allLinks = [];

  // ── Build the overlay HTML from API response ─────────────
  function renderOverlay(data, q) {
    dropdown.innerHTML = '';
    const { results = [], categories = [], brands = [], trending = [], did_you_mean = '' } = data;
    const hasContent = results.length || categories.length || brands.length || trending.length || did_you_mean;
    if (!hasContent) { dropdown.classList.remove('open'); return; }

    let html = '';

    // "Did you mean?" correction row
    if (did_you_mean) {
      html += `<div class="search-did-you-mean">Did you mean: <a href="/search/?q=${encodeURIComponent(did_you_mean)}" class="search-dym-link">${did_you_mean}</a>?</div>`;
    }

    // Trending searches (shown when query < 2 chars)
    if (trending.length) {
      html += `<div class="search-section-label">🔥 Trending searches</div><div class="search-chips">`;
      trending.forEach(term => {
        html += `<a href="/search/?q=${encodeURIComponent(term)}" class="search-chip">${term}</a>`;
      });
      html += `</div>`;
    }

    // Category chips
    if (categories.length) {
      html += `<div class="search-section-label">📂 Categories</div><div class="search-chips">`;
      categories.forEach(c => {
        html += `<a href="/category/${c.slug}/" class="search-chip search-chip-cat">${c.name}</a>`;
      });
      html += `</div>`;
    }

    // Brand chips
    if (brands.length) {
      html += `<div class="search-section-label">🏷️ Brands</div><div class="search-chips">`;
      brands.forEach(b => {
        html += `<a href="/search/?brand=${encodeURIComponent(b.slug)}" class="search-chip search-chip-brand">${b.name}</a>`;
      });
      html += `</div>`;
    }

    // Product results
    if (results.length) {
      html += `<div class="search-section-label">🛍️ Products</div>`;
      results.forEach(p => {
        const stars = '★'.repeat(Math.round(p.rating || 0)) + '☆'.repeat(5 - Math.round(p.rating || 0));
        const saleBadge = p.on_sale ? `<span class="search-result-sale">SALE</span>` : '';
        const originalPrice = p.original_price ? `<span class="search-result-original">$${p.original_price}</span>` : '';
        html += `
        <a href="/products/${p.slug}/" class="search-result-item" tabindex="0">
          ${p.image ? `<img src="${p.image}" alt="${p.name}" class="search-result-img" loading="lazy">` : '<div class="search-result-img-placeholder"></div>'}
          <div class="search-result-info">
            <div class="search-result-name">${p.name}${saleBadge}</div>
            <div class="search-result-meta">${p.category}${p.brand ? ' &middot; ' + p.brand : ''}</div>
            <div class="search-result-stars" aria-hidden="true">${stars}</div>
          </div>
          <div class="search-result-price">${originalPrice}<span class="search-result-current">$${p.price}</span></div>
        </a>`;
      });

      // "See all results" footer link
      if (q) {
        html += `<a href="/search/?q=${encodeURIComponent(q)}" class="search-see-all">See all results for "${q}" →</a>`;
      }
    }

    dropdown.innerHTML = html;
    dropdown.classList.add('open');

    // Re-build the focusable link list for keyboard nav
    allLinks = Array.from(dropdown.querySelectorAll('a'));
    currentFocusIndex = -1;
  }

  // ── Focus/blur: show trending when input clicked empty ───
  input.addEventListener('focus', () => {
    if (!input.value.trim()) {
      fetch('/search/autocomplete/?q=')
        .then(r => r.json())
        .then(data => renderOverlay(data, ''))
        .catch(() => {});
    }
  });

  // ── Live-as-you-type with 260ms debounce ─────────────────
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (!q) {
      fetch('/search/autocomplete/?q=')
        .then(r => r.json())
        .then(data => renderOverlay(data, ''))
        .catch(() => {});
      return;
    }
    debounceTimer = setTimeout(() => {
      fetch(`/search/autocomplete/?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => renderOverlay(data, q))
        .catch(() => dropdown.classList.remove('open'));
    }, 260);
  });

  // ── Keyboard navigation ───────────────────────────────────
  input.addEventListener('keydown', e => {
    if (!dropdown.classList.contains('open')) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      currentFocusIndex = Math.min(currentFocusIndex + 1, allLinks.length - 1);
      allLinks[currentFocusIndex]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      currentFocusIndex = Math.max(currentFocusIndex - 1, -1);
      if (currentFocusIndex === -1) input.focus();
      else allLinks[currentFocusIndex]?.focus();
    } else if (e.key === 'Escape') {
      dropdown.classList.remove('open');
      input.focus();
    }
  });

  // Arrow-key navigation within dropdown links
  dropdown.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      currentFocusIndex = Math.min(currentFocusIndex + 1, allLinks.length - 1);
      allLinks[currentFocusIndex]?.focus();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      currentFocusIndex = Math.max(currentFocusIndex - 1, -1);
      if (currentFocusIndex === -1) input.focus();
      else allLinks[currentFocusIndex]?.focus();
    } else if (e.key === 'Escape') {
      dropdown.classList.remove('open');
      input.focus();
    }
  });

  // ── Close when clicking outside ───────────────────────────
  document.addEventListener('click', e => {
    const searchWrap = document.getElementById('navbar-search');
    if (searchWrap && !searchWrap.contains(e.target)) {
      dropdown.classList.remove('open');
    }
  });

  // ── Form submit guard ─────────────────────────────────────
  const searchForm = input.closest('form');
  if (searchForm) {
    searchForm.addEventListener('submit', e => {
      if (!input.value.trim()) { e.preventDefault(); input.focus(); }
      dropdown.classList.remove('open');
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

    // ── Streaming send via SSE (token-by-token like ChatGPT) ───────────────
    // Falls back to regular JSON fetch if fetch/ReadableStream is unavailable.
    function sendWithStream() {
      const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
      fetch('/ai/stream/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(payload),
      })
      .then(resp => {
        if (!resp.ok || !resp.body) {
          // Server returned an error or no readable body — fall back to JSON
          return sendWithJson();
        }
        typing.remove();
        setStatus('online');

        // Create the bot message bubble that will be filled token-by-token
        const botMsg = document.createElement('div');
        botMsg.className = 'ai-msg bot';
        const bubble = document.createElement('div');
        bubble.className = 'ai-bubble';
        botMsg.appendChild(bubble);
        messages.appendChild(botMsg);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        function readChunk() {
          reader.read().then(({ done, value }) => {
            if (done) {
              // Stream complete — apply full markdown formatting
              bubble.innerHTML = formatBotText(fullText);
              messages.scrollTop = messages.scrollHeight;
              // Fetch rich product cards via the regular endpoint
              fetchPost('/ai/chat/', payload)
                .then(r => r.json())
                .then(d => appendRichCards(botMsg, d.products || []))
                .catch(() => {});
              // Update quick-action context
              const lowerMsg = msgText.toLowerCase();
              if (lowerMsg.match(/order|track|delivery|ship/)) updateQuickBtns('order');
              else if (lowerMsg.match(/size|measurements|fit|eu|uk size/)) updateQuickBtns('size');
              else if (lowerMsg.match(/product|show|find|search|recommend/)) updateQuickBtns('product');
              else updateQuickBtns('default');
              return;
            }

            // Parse each SSE line: "data: {...}\n\n"
            const text = decoder.decode(value, { stream: true });
            text.split('\n').forEach(line => {
              if (!line.startsWith('data: ')) return;
              const payload_str = line.slice(6).trim();
              if (payload_str === '[DONE]') return;
              try {
                const chunk = JSON.parse(payload_str);
                if (chunk.token) {
                  fullText += chunk.token;
                  // Show plain text while streaming, format when done
                  bubble.textContent = fullText;
                  messages.scrollTop = messages.scrollHeight;
                }
              } catch (_e) { /* skip malformed chunk */ }
            });

            readChunk(); // Read next chunk
          }).catch(() => {
            // Stream error mid-way — show what we have so far
            if (fullText) bubble.innerHTML = formatBotText(fullText);
            else appendMsg("Sorry, I'm having trouble connecting. Please try again! 🔄", 'bot');
            setStatus('error');
            setTimeout(() => setStatus('online'), 4000);
          });
        }
        readChunk();
      })
      .catch(() => sendWithJson()); // Network error — fall back to JSON
    }

    function sendWithJson() {
      fetchPost('/ai/chat/', payload)
        .then(r => r.json())
        .then(data => {
          typing.remove();
          setStatus('online');
          const replyText = data.reply || "Sorry, I couldn't process that.";
          const botMsg = appendMsgTyped(replyText, 'bot');
          const cardDelay = Math.min(replyText.length * 12 + 300, 3500);
          setTimeout(() => appendRichCards(botMsg, data.products), cardDelay);
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

    // Use streaming if ReadableStream is supported (all modern browsers).
    // Image uploads bypass streaming and go directly through the JSON endpoint
    // because the multimodal payload needs to be sent as a single request.
    if (typeof ReadableStream !== 'undefined' && !pendingImage) {
      sendWithStream();
    } else {
      sendWithJson();
    }
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

    // Skeleton while loading
    if (body) body.innerHTML = `
      <div class="qv-img-col">
        <div class="qv-main-img-wrap skeleton"></div>
        <div class="qv-thumb-row" style="margin-top:.75rem;display:flex;gap:.5rem">
          ${[1,2,3].map(() => '<div class="skeleton" style="width:60px;height:60px;border-radius:8px;flex-shrink:0"></div>').join('')}
        </div>
      </div>
      <div class="qv-info-col">
        <div class="skeleton" style="height:14px;width:80px;border-radius:4px;margin-bottom:10px"></div>
        <div class="skeleton" style="height:28px;width:90%;border-radius:6px;margin-bottom:12px"></div>
        <div class="skeleton" style="height:18px;width:40%;border-radius:4px;margin-bottom:10px"></div>
        <div class="skeleton" style="height:36px;width:60%;border-radius:6px;margin-bottom:18px"></div>
        <div class="skeleton" style="height:12px;width:100%;border-radius:4px;margin-bottom:8px"></div>
        <div class="skeleton" style="height:12px;width:80%;border-radius:4px;margin-bottom:24px"></div>
        <div class="skeleton" style="height:44px;width:100%;border-radius:10px"></div>
      </div>`;

    // Fetch rich JSON from the dedicated API endpoint
    fetch(`/api/products/${slug}/quickview/`)
      .then(r => r.json())
      .then(p => {
        if (title) title.textContent = p.name;

        // Star rendering
        const filled = Math.round(p.rating);
        const stars = '★'.repeat(filled) + '☆'.repeat(5 - filled);

        // Price block
        const priceHtml = p.on_sale
          ? `<span class="qv-price-current">$${p.sale_price}</span>
             <span class="qv-price-original">$${p.price}</span>
             <span class="qv-badge-sale">-${p.discount_pct}%</span>`
          : `<span class="qv-price-current">$${p.price}</span>`;

        // Stock badge
        const stockBadge = p.in_stock
          ? (p.stock <= 5
              ? `<span class="qv-stock low">⚡ Only ${p.stock} left!</span>`
              : `<span class="qv-stock ok">✓ In Stock</span>`)
          : `<span class="qv-stock out">✗ Out of Stock</span>`;

        // Thumbnail strip (main image + extra images)
        const allImgs = [p.image, ...p.extra_images].filter(Boolean).slice(0, 4);
        const thumbsHtml = allImgs.length > 1
          ? `<div class="qv-thumb-row">${allImgs.map((src, i) =>
              `<img src="${src}" class="qv-thumb${i === 0 ? ' active' : ''}" data-src="${src}" loading="lazy" alt="View ${i + 1}">`
            ).join('')}</div>`
          : '';

        // Variants (size pills)
        const sizeVariants = [...new Set(p.variants.filter(v => v.size).map(v => v.size))];
        const sizeHtml = sizeVariants.length
          ? `<div class="qv-label">Size</div>
             <div class="qv-size-row">${sizeVariants.map(s =>
               `<button class="qv-size-btn" data-size="${s}">${s}</button>`
             ).join('')}</div>`
          : (p.size ? `<div class="qv-label">Size</div><div class="qv-size-row"><button class="qv-size-btn active">${p.size}</button></div>` : '');

        // Add to cart form
        const atcHtml = p.in_stock
          ? `<form class="qv-atc-form add-to-cart-form" action="/cart/add/" method="post">
               <input type="hidden" name="csrfmiddlewaretoken" value="${p.csrf_token}">
               <input type="hidden" name="product_id" value="${p.product_id}">
               <div class="qv-qty-row">
                 <button type="button" class="qv-qty-btn" data-delta="-1">−</button>
                 <input type="number" name="quantity" class="qv-qty-input" value="1" min="1" max="${p.stock}">
                 <button type="button" class="qv-qty-btn" data-delta="1">+</button>
               </div>
               <button type="submit" class="btn btn-primary btn-full qv-atc-btn">
                 <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>
                 Add to Cart
               </button>
             </form>`
          : `<button class="btn btn-secondary btn-full" disabled>Out of Stock</button>`;

        if (body) body.innerHTML = `
          <div class="qv-img-col">
            <div class="qv-main-img-wrap">
              <img src="${p.image}" alt="${p.name}" class="qv-main-img" id="qv-main-img" loading="eager">
              ${p.on_sale ? `<span class="qv-img-sale-badge">SALE</span>` : ''}
            </div>
            ${thumbsHtml}
          </div>
          <div class="qv-info-col">
            ${p.brand ? `<div class="qv-brand"><a href="/search/?brand=${p.brand_slug}" style="color:var(--primary);font-weight:700;font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;text-decoration:none">${p.brand}</a></div>` : ''}
            <div class="qv-category" style="font-size:.8rem;color:var(--text-light);margin-bottom:.35rem">${p.category}</div>
            <div class="qv-price-row">${priceHtml}</div>
            <div class="qv-rating-row" aria-label="${p.rating} out of 5">
              <span class="qv-stars" aria-hidden="true">${stars}</span>
              <span class="qv-rating-num">${p.rating}</span>
              <span class="qv-rating-cnt">(${p.rating_count} review${p.rating_count !== 1 ? 's' : ''})</span>
            </div>
            ${stockBadge}
            ${p.short_description ? `<p class="qv-desc">${p.short_description}</p>` : (p.description ? `<p class="qv-desc">${p.description}${p.description.length >= 400 ? '…' : ''}</p>` : '')}
            ${sizeHtml}
            ${atcHtml}
            <a href="${p.url}" class="qv-full-link">View full details & all reviews →</a>
          </div>`;

        // Thumbnail click — swap main image
        body.querySelectorAll('.qv-thumb').forEach(thumb => {
          thumb.addEventListener('click', () => {
            const mainImg = body.querySelector('#qv-main-img');
            if (mainImg) mainImg.src = thumb.dataset.src;
            body.querySelectorAll('.qv-thumb').forEach(t => t.classList.remove('active'));
            thumb.classList.add('active');
          });
        });

        // Size pill selection
        body.querySelectorAll('.qv-size-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            body.querySelectorAll('.qv-size-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
          });
        });

        // Qty +/− buttons
        body.querySelectorAll('.qv-qty-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            const input = body.querySelector('.qv-qty-input');
            if (!input) return;
            const delta = parseInt(btn.dataset.delta, 10);
            const newVal = Math.max(1, Math.min(p.stock, parseInt(input.value, 10) + delta));
            input.value = newVal;
          });
        });

        // AJAX ATC from quick view (override default form submit)
        const atcForm = body.querySelector('.qv-atc-form');
        if (atcForm) {
          atcForm.addEventListener('submit', e => {
            e.preventDefault();
            const qty = body.querySelector('.qv-qty-input')?.value || '1';
            fetchPost('/cart/add/', { product_id: p.product_id, quantity: parseInt(qty, 10) })
              .then(r => r.json())
              .then(d => {
                if (d.success || d.cart_count !== undefined) {
                  Toast.show(`${p.name} added to cart! 🛒`, 'success');
                  document.querySelectorAll('.cart-count').forEach(el => { el.textContent = d.cart_count || ''; });
                  const atcBtn = body.querySelector('.qv-atc-btn');
                  if (atcBtn) {
                    atcBtn.textContent = '✓ Added!';
                    atcBtn.style.background = 'var(--success)';
                    setTimeout(() => { atcBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg> Add to Cart'; atcBtn.style.background = ''; }, 2000);
                  }
                } else {
                  Toast.show('Please log in to add items to cart.', 'error');
                }
              })
              .catch(() => Toast.show('Could not add to cart. Please try again.', 'error'));
          });
        }
      })
      .catch(() => {
        if (body) body.innerHTML = `
          <div style="grid-column:1/-1;text-align:center;padding:3rem">
            <div style="font-size:2.5rem;margin-bottom:1rem">😕</div>
            <p style="color:var(--text-light);margin-bottom:1.5rem">Could not load product details.</p>
            <a href="/products/${slug}/" class="btn btn-primary">View Full Product Page</a>
          </div>`;
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
// Slides up from the bottom when the main product form scrolls out of view.
// Targets the main ATC form on product detail pages; falls back gracefully.
function initStickyCartBar() {
  const stickyBar = document.getElementById('sticky-atc-bar');
  if (!stickyBar) return;

  // Observe the primary Add-to-Cart form — when it leaves the viewport,
  // show the sticky bar so the user always has a way to add to cart.
  const mainForm = document.querySelector('.product-actions');
  if (!mainForm) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      const visible = !entry.isIntersecting;
      stickyBar.classList.toggle('visible', visible);
      stickyBar.setAttribute('aria-hidden', String(!visible));
    });
  }, { threshold: 0, rootMargin: '-80px 0px 0px 0px' });
  observer.observe(mainForm);
}

// ── Product Image Carousel (thumbnail strip) ─────────────────────────────────
// Clicking a thumbnail swaps the main product image.  Works alongside the
// zoom lens so the zoomed view always shows the currently selected image.
function initProductThumbCarousel() {
  const strip = document.getElementById('product-thumb-strip');
  const mainImg = document.getElementById('main-product-img');
  const zoomWrap = document.getElementById('product-zoom-wrap');
  if (!strip || !mainImg) return;

  strip.querySelectorAll('.product-thumb').forEach(thumb => {
    thumb.addEventListener('click', () => {
      const fullSrc = thumb.dataset.full || thumb.src;
      mainImg.src = fullSrc;

      // Update zoom lens result panel image if present
      const zoomResultImg = document.querySelector('.zoom-result-panel img');
      if (zoomResultImg) zoomResultImg.src = fullSrc;

      // Update active state on thumbnails
      strip.querySelectorAll('.product-thumb').forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
    });
  });
}

// ── Sale Countdown Timer ──────────────────────────────────────────────────────
// Shows a live ticking countdown on sale products.  The end-time is stored in
// localStorage keyed by product URL so it persists across page refreshes
// (user sees consistent countdown, not a reset on every visit).
// Duration: 48 hours from first visit.
function initSaleCountdown() {
  const el = document.getElementById('sale-countdown');
  if (!el) return;
  const hEl = document.getElementById('cd-h');
  const mEl = document.getElementById('cd-m');
  const sEl = document.getElementById('cd-s');
  if (!hEl || !mEl || !sEl) return;

  const key = 'tm_sale_end_' + window.location.pathname;
  let endTime = parseInt(localStorage.getItem(key), 10);
  if (!endTime || endTime < Date.now()) {
    endTime = Date.now() + 48 * 60 * 60 * 1000;
    localStorage.setItem(key, endTime);
  }

  function tick() {
    const diff = endTime - Date.now();
    if (diff <= 0) { el.style.display = 'none'; return; }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    hEl.textContent = String(h).padStart(2, '0');
    mEl.textContent = String(m).padStart(2, '0');
    sEl.textContent = String(s).padStart(2, '0');
  }
  tick();
  setInterval(tick, 1000);
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

// ── AI Review Summarisation Button ───────────────────────────────────────────
// Clicking "✨ AI Summary" POSTs to the backend which calls OpenRouter to
// generate a 2-3 sentence consensus summary of the product's reviews.
function initAIReviewSummary() {
  const btn = document.getElementById('ai-summarise-btn');
  if (!btn) return;
  const panel = document.getElementById('ai-review-summary');
  const textEl = document.getElementById('ai-summary-text');
  const spinner = document.getElementById('ai-summary-spinner');

  let loaded = false;
  btn.addEventListener('click', () => {
    if (loaded) {
      panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      return;
    }
    const slug = btn.dataset.slug;
    panel.style.display = 'block';
    if (spinner) spinner.style.display = 'inline-block';
    if (textEl) textEl.textContent = 'Generating AI summary…';

    fetchPost(`/products/${slug}/summarise-reviews/`, {})
      .then(r => r.json())
      .then(data => {
        if (spinner) spinner.style.display = 'none';
        if (textEl) textEl.textContent = data.summary || 'Could not generate summary.';
        loaded = true;
      })
      .catch(() => {
        if (spinner) spinner.style.display = 'none';
        if (textEl) textEl.textContent = 'Failed to load AI summary. Please try again.';
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
  initProductThumbCarousel();
  initSaleCountdown();
  initPasswordStrength();
  initCookieBanner();
  initNotificationBell();
  initNewsletter();
  initPromoCode();
  initAjaxCartQty();
  initFocusTrap();
  initSocialShare();
  patchCartForMiniCart();
  initAIReviewSummary();
  initProductComparison();
});

/* ═══════════════════════════════════════════════════════════
   PRODUCT COMPARISON
   - Up to 4 products stored in localStorage
   - Floating bar slides up; Compare Now opens a side-by-side modal
   ═══════════════════════════════════════════════════════════ */
function initProductComparison() {
  const MAX = 4;
  const bar = document.getElementById('compare-bar');
  const barItems = document.getElementById('compare-bar-items');
  const barCount = document.getElementById('compare-bar-count');
  const compareNowBtn = document.getElementById('compare-now-btn');
  const compareClearBtn = document.getElementById('compare-clear-btn');
  const modalOverlay = document.getElementById('compare-modal-overlay');
  const modalClose = document.getElementById('compare-modal-close');
  const tableHead = document.getElementById('compare-table-head');
  const tableBody = document.getElementById('compare-table-body');
  if (!bar) return;

  // State stored in memory (survives page navigation via sessionStorage)
  let compareList = JSON.parse(sessionStorage.getItem('tm-compare') || '[]');

  function saveState() {
    sessionStorage.setItem('tm-compare', JSON.stringify(compareList));
  }

  function renderBar() {
    barItems.innerHTML = '';
    if (compareList.length === 0) {
      bar.classList.remove('visible');
      bar.setAttribute('aria-hidden', 'true');
      return;
    }
    bar.classList.add('visible');
    bar.setAttribute('aria-hidden', 'false');
    barCount.textContent = `${compareList.length}/${MAX} selected`;

    compareList.forEach(p => {
      const item = document.createElement('div');
      item.className = 'compare-bar-item';
      item.innerHTML = `
        <span style="font-size:.8rem;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${p.name}</span>
        <button class="compare-bar-item-remove" data-slug="${p.slug}" aria-label="Remove ${p.name} from comparison">&times;</button>
      `;
      barItems.appendChild(item);
    });

    barItems.querySelectorAll('.compare-bar-item-remove').forEach(btn => {
      btn.addEventListener('click', () => removeFromCompare(btn.dataset.slug));
    });
  }

  function syncButtons() {
    document.querySelectorAll('.compare-btn[data-compare]').forEach(btn => {
      const isActive = compareList.some(p => p.slug === btn.dataset.compare);
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }

  function addToCompare(slug, data) {
    if (compareList.some(p => p.slug === slug)) {
      removeFromCompare(slug);
      return;
    }
    if (compareList.length >= MAX) {
      Toast.show(`You can compare up to ${MAX} products at a time.`, 'error');
      return;
    }
    compareList.push({ slug, ...data });
    saveState();
    renderBar();
    syncButtons();
  }

  function removeFromCompare(slug) {
    compareList = compareList.filter(p => p.slug !== slug);
    saveState();
    renderBar();
    syncButtons();
  }

  function openModal() {
    if (compareList.length < 2) {
      Toast.show('Add at least 2 products to compare.', 'error');
      return;
    }

    // Build header row
    const ROWS = ['Image', 'Price', 'Brand', 'Category', 'Rating', 'Stock', 'Actions'];
    tableHead.innerHTML = `<th>Feature</th>${compareList.map(p =>
      `<th class="compare-product-col">
        <img src="${p.img || ''}" alt="${p.name}" class="compare-product-img" onerror="this.style.display='none'">
        <a href="${p.url}" class="compare-product-name" target="_blank">${p.name}</a>
      </th>`
    ).join('')}`;

    // Build body rows
    const rows = [
      ['Price', p => `<strong style="color:var(--primary);font-size:1.1rem">$${p.price}</strong>`],
      ['Brand', p => p.brand || '<span style="color:var(--text-light)">—</span>'],
      ['Category', p => p.category || '<span style="color:var(--text-light)">—</span>'],
      ['Rating', p => {
        const filled = Math.round(parseFloat(p.rating || 0));
        return `<span class="compare-stars">${'★'.repeat(filled)}${'☆'.repeat(5 - filled)}</span> <span style="font-size:.8rem;color:var(--text-light)">${p.rating || '0'}</span>`;
      }],
      ['Availability', p => p.stock === 'In Stock'
        ? `<span style="color:var(--success);font-weight:700">✓ ${p.stock}</span>`
        : `<span style="color:var(--error);font-weight:700">✗ ${p.stock}</span>`],
      ['View', p => `<a href="${p.url}" class="btn btn-primary btn-sm" target="_blank">View Product</a>`],
    ];

    tableBody.innerHTML = rows.map(([label, render], i) =>
      `<tr ${i % 2 === 0 ? 'class="compare-highlight"' : ''}>
        <td>${label}</td>
        ${compareList.map(p => `<td class="compare-product-col">${render(p)}</td>`).join('')}
      </tr>`
    ).join('');

    modalOverlay.classList.add('open');
    modalOverlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    modalClose.focus();
  }

  function closeModal() {
    modalOverlay.classList.remove('open');
    modalOverlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // Wire up static buttons
  compareNowBtn?.addEventListener('click', openModal);
  compareClearBtn?.addEventListener('click', () => {
    compareList = [];
    saveState();
    renderBar();
    syncButtons();
  });
  modalClose?.addEventListener('click', closeModal);
  modalOverlay?.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && modalOverlay?.classList.contains('open')) closeModal();
  });

  // Delegate compare button clicks (works for dynamically loaded cards)
  document.addEventListener('click', e => {
    const btn = e.target.closest('.compare-btn[data-compare]');
    if (!btn) return;
    e.preventDefault();
    addToCompare(btn.dataset.compare, {
      name: btn.dataset.compareName || btn.dataset.compare,
      price: btn.dataset.comparePrice || '0',
      brand: btn.dataset.compareBrand || '',
      category: btn.dataset.compareCategory || '',
      rating: btn.dataset.compareRating || '0',
      stock: btn.dataset.compareStock || 'Unknown',
      img: btn.dataset.compareImg || '',
      url: btn.dataset.compareUrl || `/products/${btn.dataset.compare}/`,
    });
  });

  // Restore state on page load
  renderBar();
  syncButtons();
}

/* ═══════════════════════════════════════════════════════════
   ACCESSIBILITY HUB — radial bubble + options panel + voice AI
   ═══════════════════════════════════════════════════════════ */
function initAccessibilityHub() {
  const hub = document.getElementById('a11y-hub');
  const mainBtn = document.getElementById('a11y-main-btn');
  const options = document.getElementById('a11y-options');
  if (!hub || !mainBtn) return;

  // ── Hub open/close (purple button fans sub-options) ───────────────────────
  function toggleHub() {
    const isOpen = hub.classList.toggle('open');
    mainBtn.setAttribute('aria-expanded', isOpen);
    options?.setAttribute('aria-hidden', !isOpen);
    if (!isOpen) closePanelOverlay();
  }

  mainBtn.addEventListener('click', (e) => { e.stopPropagation(); toggleHub(); });

  document.addEventListener('click', e => {
    const inPanel = panelOverlay?.contains(e.target);
    if (!hub.contains(e.target) && !inPanel) {
      hub.classList.remove('open');
      mainBtn.setAttribute('aria-expanded', 'false');
      options?.setAttribute('aria-hidden', 'true');
      closePanelOverlay();
    }
  });

  // ── Options Panel ─────────────────────────────────────────
  const panelOverlay = document.getElementById('a11y-panel-overlay');

  function openPanelOverlay() {
    panelOverlay?.classList.add('open');
    panelOverlay?.querySelector('.a11y-panel')?.focus?.();
  }
  function closePanelOverlay() {
    panelOverlay?.classList.remove('open');
  }
  function togglePanelOverlay() {
    panelOverlay?.classList.contains('open') ? closePanelOverlay() : openPanelOverlay();
  }

  panelOverlay?.addEventListener('click', e => {
    if (e.target === panelOverlay) closePanelOverlay();
  });

  // Save & Close button — closes the panel, keeps settings
  document.getElementById('a11y-save-options')?.addEventListener('click', () => {
    closePanelOverlay();
  });

  // Sub-option buttons in the radial menu
  document.getElementById('a11y-voice-btn')?.addEventListener('click', openVoiceOverlay);
  document.getElementById('a11y-text-btn')?.addEventListener('click', () => { togglePanelOverlay(); hub.classList.remove('open'); });
  document.getElementById('a11y-color-btn')?.addEventListener('click', () => { togglePanelOverlay(); hub.classList.remove('open'); });
  document.getElementById('a11y-contrast-btn')?.addEventListener('click', () => {
    toggleHighContrast();
    hub.classList.remove('open');
    closePanelOverlay();
  });
  document.getElementById('a11y-font-btn')?.addEventListener('click', () => {
    toggleDyslexiaFont();
    hub.classList.remove('open');
    closePanelOverlay();
  });

  // ── Text size ────────────────────────────────────────────
  const TEXT_SIZES = ['smaller', 'normal', 'larger', 'largest'];
  const SIZE_LABELS = { smaller: 'Smaller', normal: 'Normal', larger: 'Larger', largest: 'Largest' };
  let textSizeIdx = parseInt(localStorage.getItem('tm-a11y-text') || '1', 10);
  const sizeLabel = document.getElementById('a11y-size-label');

  function applyTextSize() {
    const size = TEXT_SIZES[textSizeIdx];
    document.documentElement.setAttribute('data-a11y-text', size);
    localStorage.setItem('tm-a11y-text', textSizeIdx);
    if (sizeLabel) sizeLabel.textContent = SIZE_LABELS[size];
  }
  applyTextSize();

  document.getElementById('a11y-larger')?.addEventListener('click', () => {
    textSizeIdx = Math.min(textSizeIdx + 1, TEXT_SIZES.length - 1);
    applyTextSize();
  });
  document.getElementById('a11y-smaller')?.addEventListener('click', () => {
    textSizeIdx = Math.max(textSizeIdx - 1, 0);
    applyTextSize();
  });
  document.getElementById('a11y-reset-size')?.addEventListener('click', () => {
    textSizeIdx = 1; applyTextSize();
  });

  // ── Colorblind modes ──────────────────────────────────────
  const savedColor = localStorage.getItem('tm-a11y-color') || 'normal';
  function applyColorMode(mode) {
    document.documentElement.setAttribute('data-a11y-color', mode);
    localStorage.setItem('tm-a11y-color', mode);
    document.querySelectorAll('[data-color-mode]').forEach(btn => {
      const active = btn.dataset.colorMode === mode;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }
  applyColorMode(savedColor);

  document.querySelectorAll('[data-color-mode]').forEach(btn => {
    btn.addEventListener('click', () => applyColorMode(btn.dataset.colorMode));
  });

  // ── High contrast ─────────────────────────────────────────
  let contrastOn = localStorage.getItem('tm-a11y-contrast') === '1';
  const contrastBtn = document.getElementById('a11y-contrast-toggle');
  function applyContrast() {
    document.documentElement.setAttribute('data-a11y-contrast', contrastOn ? 'high' : 'normal');
    localStorage.setItem('tm-a11y-contrast', contrastOn ? '1' : '0');
    contrastBtn?.classList.toggle('active', contrastOn);
    contrastBtn?.setAttribute('aria-pressed', contrastOn ? 'true' : 'false');
  }
  function toggleHighContrast() { contrastOn = !contrastOn; applyContrast(); }
  applyContrast();
  contrastBtn?.addEventListener('click', toggleHighContrast);

  // ── Dyslexia font ─────────────────────────────────────────
  let dyslexicOn = localStorage.getItem('tm-a11y-font') === '1';
  const fontBtn = document.getElementById('a11y-font-toggle');
  function applyFont() {
    document.documentElement.setAttribute('data-a11y-font', dyslexicOn ? 'dyslexic' : 'normal');
    localStorage.setItem('tm-a11y-font', dyslexicOn ? '1' : '0');
    fontBtn?.classList.toggle('active', dyslexicOn);
    fontBtn?.setAttribute('aria-pressed', dyslexicOn ? 'true' : 'false');
  }
  function toggleDyslexiaFont() { dyslexicOn = !dyslexicOn; applyFont(); }
  applyFont();
  fontBtn?.addEventListener('click', toggleDyslexiaFont);

  // ── Reduce motion ─────────────────────────────────────────
  let reduceMotion = localStorage.getItem('tm-a11y-motion') === '1';
  const motionBtn = document.getElementById('a11y-motion-toggle');
  function applyMotion() {
    if (reduceMotion) {
      document.documentElement.style.setProperty('--transition', '0ms');
    } else {
      document.documentElement.style.removeProperty('--transition');
    }
    localStorage.setItem('tm-a11y-motion', reduceMotion ? '1' : '0');
    motionBtn?.classList.toggle('active', reduceMotion);
    motionBtn?.setAttribute('aria-pressed', reduceMotion ? 'true' : 'false');
  }
  applyMotion();
  motionBtn?.addEventListener('click', () => { reduceMotion = !reduceMotion; applyMotion(); });

  // ── Reset all ─────────────────────────────────────────────
  document.getElementById('a11y-reset-all')?.addEventListener('click', () => {
    textSizeIdx = 1; applyTextSize();
    applyColorMode('normal');
    contrastOn = false; applyContrast();
    dyslexicOn = false; applyFont();
    reduceMotion = false; applyMotion();
    ['tm-a11y-text','tm-a11y-color','tm-a11y-contrast','tm-a11y-font','tm-a11y-motion']
      .forEach(k => localStorage.removeItem(k));
  });
}

/* ═══════════════════════════════════════════════════════════
   VOICE AI ASSISTANT — Web Speech API + Text-to-Speech
   + TrendMart action execution (search, add-to-cart, navigate)
   ═══════════════════════════════════════════════════════════ */
const voiceOverlay = document.getElementById('voice-overlay');
const voiceStatus = document.getElementById('voice-status');
const voiceTranscript = document.getElementById('voice-transcript');

function openVoiceOverlay() {
  if (!voiceOverlay) return;
  voiceOverlay.classList.add('active');
  voiceOverlay.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  setTimeout(() => speak('Hi! I\'m TrendMart\'s voice assistant. How can I help you today?'), 400);
}

function closeVoiceOverlay() {
  stopListening();
  window.speechSynthesis?.cancel();
  voiceOverlay?.classList.remove('active', 'listening', 'thinking', 'speaking');
  voiceOverlay?.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

document.getElementById('voice-close-btn')?.addEventListener('click', closeVoiceOverlay);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && voiceOverlay?.classList.contains('active')) closeVoiceOverlay();
});

// Tap the orb to start listening
voiceOverlay?.querySelector('.voice-orb')?.addEventListener('click', startListening);

// ── Speech Synthesis (TTS) ────────────────────────────────
function speak(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.rate = 1.05; utt.pitch = 1; utt.volume = 1;

  // Prefer a pleasant female voice if available
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    v.lang.startsWith('en') && (v.name.includes('Female') || v.name.includes('Google US') || v.name.includes('Samantha'))
  ) || voices.find(v => v.lang.startsWith('en'));
  if (preferred) utt.voice = preferred;

  utt.onstart = () => {
    voiceOverlay?.classList.remove('listening', 'thinking');
    voiceOverlay?.classList.add('speaking');
    if (voiceStatus) voiceStatus.textContent = 'Speaking…';
  };
  utt.onend = () => {
    voiceOverlay?.classList.remove('speaking');
    if (voiceStatus) voiceStatus.textContent = 'Tap the orb to speak';
  };
  if (voiceTranscript) {
    voiceTranscript.textContent = text;
    voiceTranscript.classList.add('response-text');
  }
  window.speechSynthesis.speak(utt);
}

// ── Speech Recognition (STT) ──────────────────────────────
let recognition = null;
let isListening = false;

function startListening() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    speak('Sorry, your browser does not support voice input. Please try Chrome or Edge.');
    return;
  }
  if (isListening) { stopListening(); return; }

  recognition = new SR();
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    isListening = true;
    voiceOverlay?.classList.add('listening');
    voiceOverlay?.classList.remove('thinking', 'speaking');
    if (voiceStatus) voiceStatus.textContent = 'Listening…';
    if (voiceTranscript) { voiceTranscript.textContent = ''; voiceTranscript.classList.remove('response-text'); }
  };

  recognition.onresult = e => {
    const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
    if (voiceTranscript) voiceTranscript.textContent = transcript;
    if (e.results[0].isFinal) {
      stopListening();
      processVoiceCommand(transcript.trim().toLowerCase());
    }
  };

  recognition.onerror = (e) => {
    stopListening();
    if (e.error === 'not-allowed') {
      speak('Microphone access was denied. Please allow microphone access to use voice features.');
    } else if (e.error !== 'no-speech') {
      speak('I had trouble hearing you. Please tap the orb and try again.');
    } else {
      if (voiceStatus) voiceStatus.textContent = 'Tap the orb to speak';
    }
  };

  recognition.onend = () => { isListening = false; };
  recognition.start();
}

function stopListening() {
  if (recognition) { try { recognition.stop(); } catch(e) {} recognition = null; }
  isListening = false;
  voiceOverlay?.classList.remove('listening');
}

// ── Action Execution Engine ───────────────────────────────
let pendingAction = null;

function processVoiceCommand(cmd) {
  voiceOverlay?.classList.add('thinking');
  if (voiceStatus) voiceStatus.textContent = 'Thinking…';

  // Check for pending confirmation first
  if (pendingAction) {
    const yes = /\b(yes|yeah|yep|sure|ok|okay|add|do it|confirm|please)\b/.test(cmd);
    const no = /\b(no|nope|cancel|nevermind|stop|don't)\b/.test(cmd);
    if (yes) {
      const action = pendingAction;
      pendingAction = null;
      executePendingAction(action);
      return;
    } else if (no) {
      pendingAction = null;
      voiceOverlay?.classList.remove('thinking');
      speak('Okay, I\'ve cancelled that. What else can I help you with?');
      return;
    }
  }

  setTimeout(() => {
    voiceOverlay?.classList.remove('thinking');
    handleVoiceIntent(cmd);
  }, 600);
}

function handleVoiceIntent(cmd) {
  // ── Navigation ────────────────────────────────────────────
  if (/\b(go to|open|show me|take me to)\b.*(home|homepage|main page)/.test(cmd)) {
    speak('Taking you to the homepage!'); setTimeout(() => window.location.href = '/', 1500); return;
  }
  if (/\b(go to|open|show me)\b.*(cart|shopping cart|my cart)/.test(cmd)) {
    speak('Opening your cart!'); setTimeout(() => window.location.href = '/cart/', 1500); return;
  }
  if (/\b(go to|open|show me)\b.*(wishlist|saved items)/.test(cmd)) {
    speak('Opening your wishlist!'); setTimeout(() => window.location.href = '/wishlist/', 1500); return;
  }
  if (/\b(go to|open|show me)\b.*(orders|my orders|purchase history)/.test(cmd)) {
    speak('Opening your orders!'); setTimeout(() => window.location.href = '/orders/', 1500); return;
  }
  if (/\b(go to|open|show me)\b.*(profile|account|my account)/.test(cmd)) {
    speak('Opening your profile!'); setTimeout(() => window.location.href = '/profile/', 1500); return;
  }
  if (/\b(go to|open|show me)\b.*(dashboard)/.test(cmd)) {
    speak('Opening your dashboard!'); setTimeout(() => window.location.href = '/dashboard/', 1500); return;
  }
  if (/\b(faq|help|how does|how do i|frequently asked)/.test(cmd)) {
    speak('Opening our FAQ page!'); setTimeout(() => window.location.href = '/faq/', 1500); return;
  }
  if (/\b(login|log in|sign in)/.test(cmd)) {
    speak('Opening the login page!'); setTimeout(() => window.location.href = '/login/', 1500); return;
  }

  // ── Search / Browse ───────────────────────────────────────
  const searchMatch = cmd.match(/\b(?:search|find|look for|show me|i want|i need|browse)\b[\s,]*(?:some\s)?(?:me\s)?(.+)/);
  if (searchMatch) {
    const query = searchMatch[1].replace(/\b(please|thanks|thank you)\b/g, '').trim();
    if (query.length > 1) {
      speak(`Searching for "${query}" now!`);
      setTimeout(() => window.location.href = `/products/?q=${encodeURIComponent(query)}`, 1800);
      return;
    }
  }

  // ── Add to cart (on product page) ────────────────────────
  if (/\b(add to cart|add it to cart|add this to cart|buy this|purchase this|add to my cart)\b/.test(cmd)) {
    const addBtn = document.querySelector('.add-to-cart-form button[type="submit"], #sticky-add-to-cart');
    if (addBtn) {
      pendingAction = { type: 'cart', btn: addBtn };
      const productName = document.querySelector('.product-title, h1')?.textContent?.trim() || 'this item';
      speak(`Should I add "${productName}" to your cart?`);
    } else {
      speak('I don\'t see a product to add here. Try navigating to a product page first.');
    }
    return;
  }

  // ── Wishlist ──────────────────────────────────────────────
  if (/\b(add to wishlist|save this|save for later|add to my wishlist)\b/.test(cmd)) {
    const wBtn = document.querySelector('.wishlist-toggle-btn');
    if (wBtn) {
      pendingAction = { type: 'wishlist', btn: wBtn };
      const productName = document.querySelector('.product-title, h1')?.textContent?.trim() || 'this item';
      speak(`Should I add "${productName}" to your wishlist?`);
    } else {
      speak('I can\'t find a wishlist button here. Try visiting a product page.');
    }
    return;
  }

  // ── Cart info ─────────────────────────────────────────────
  if (/\b(what is|what's|whats|how many)\b.*(in my cart|in the cart|cart)\b/.test(cmd)) {
    const badge = document.querySelector('.cart-badge');
    const count = badge?.textContent?.trim() || '0';
    speak(`You have ${count} item${count === '1' ? '' : 's'} in your cart.`);
    return;
  }

  // ── Sale / deals ──────────────────────────────────────────
  if (/\b(sale|deals|discount|offer|what's on sale|flash deal)\b/.test(cmd)) {
    speak('Let me show you our latest deals!');
    setTimeout(() => window.location.href = '/products/?sort=newest&sale=1', 1800);
    return;
  }

  // ── Contact / support ─────────────────────────────────────
  if (/\b(contact|support|help me|customer service|complaint)\b/.test(cmd)) {
    speak('Opening our customer support page!');
    setTimeout(() => window.location.href = '/contact-support/', 1500);
    return;
  }

  // ── Stop / close ──────────────────────────────────────────
  if (/\b(stop|close|exit|goodbye|bye|dismiss)\b/.test(cmd)) {
    speak('Goodbye! Have a great shopping experience!');
    setTimeout(closeVoiceOverlay, 1500);
    return;
  }

  // ── Fallback — send to AI assistant ──────────────────────
  fetchAIVoiceResponse(cmd);
}

function executePendingAction(action) {
  if (action.type === 'cart') {
    action.btn.closest('form')?.submit() || action.btn.click();
    speak('Done! Item added to your cart. You can view it anytime by clicking the cart icon.');
  } else if (action.type === 'wishlist') {
    action.btn.click();
    speak('Done! Item saved to your wishlist.');
  }
}

function fetchAIVoiceResponse(query) {
  voiceOverlay?.classList.add('thinking');
  if (voiceStatus) voiceStatus.textContent = 'Asking TrendMart AI…';

  fetch('/ai/chat/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ message: query, voice: true })
  })
  .then(r => r.json())
  .then(data => {
    voiceOverlay?.classList.remove('thinking');
    const reply = data.reply || data.message || 'I\'m not sure about that. Try asking me something else!';
    const cleanReply = reply.replace(/[*_#`\[\]()]/g, '').substring(0, 300);
    speak(cleanReply);
  })
  .catch(() => {
    voiceOverlay?.classList.remove('thinking');
    speak('I had a connection issue. Please try again in a moment.');
  });
}

// ── Video demo hover play/pause ───────────────────────────
function initVideoHover() {
  document.querySelectorAll('.product-card-image').forEach(card => {
    const video = card.querySelector('.product-card-video');
    if (!video) return;
    card.addEventListener('mouseenter', () => { video.play().catch(() => {}); });
    card.addEventListener('mouseleave', () => { video.pause(); video.currentTime = 0; });
  });
}

// ── Infinite Scroll (replaces Load More button) ───────────
function initInfiniteScroll() {
  const btn = document.getElementById('load-more-btn');
  const grid = document.getElementById('product-grid');
  if (!btn || !grid) return;

  let loading = false;

  function loadNext() {
    const nextPage = btn.dataset.nextPage;
    const hasNext = btn.dataset.hasNext === 'true';
    if (!hasNext || loading) return;

    loading = true;
    const url = new URL(window.location);
    url.searchParams.set('page', nextPage);
    url.searchParams.set('ajax', '1');

    fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.json())
      .then(data => {
        const tmp = document.createElement('div');
        tmp.innerHTML = data.html;
        tmp.querySelectorAll('article.product-card').forEach(card => {
          card.style.opacity = '0';
          card.style.transform = 'translateY(16px)';
          grid.appendChild(card);
          requestAnimationFrame(() => {
            card.style.transition = 'opacity .3s ease, transform .3s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
          });
        });
        initVideoHover();

        const wrap = document.getElementById('load-more-wrap');
        if (data.has_next) {
          btn.dataset.nextPage = data.next_page;
          btn.dataset.hasNext = 'true';
          const countEl = document.getElementById('load-more-count');
          if (countEl) {
            const loaded = grid.querySelectorAll('article.product-card').length;
            countEl.textContent = `Showing ${loaded} of ${data.total_count} products`;
          }
        } else {
          btn.dataset.hasNext = 'false';
          if (wrap) wrap.innerHTML = `<p style="font-size:.875rem;color:var(--text-light);text-align:center">All ${data.total_count} products shown</p>`;
        }
        loading = false;
      })
      .catch(() => { loading = false; });
  }

  // IntersectionObserver — trigger when button scrolls into view
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) loadNext();
    }, { rootMargin: '200px' });
    observer.observe(btn);
    btn.style.display = 'none';
  } else {
    btn.addEventListener('click', loadNext);
  }
}

// Initialise everything on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  if (typeof initProductComparison === 'function') initProductComparison();
  initAccessibilityHub();
  initVideoHover();
  initInfiniteScroll();
  initWebPush();
});

// ── Web Push Notifications ────────────────────────────────────────────────────
// Registers the service worker, fetches the VAPID public key from the server,
// and subscribes the browser to push notifications. Silently skips if the
// browser doesn't support the Push API or if the user denies permission.
async function initWebPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

  try {
    const reg = await navigator.serviceWorker.ready;

    // Fetch server's VAPID public key
    const keyResp = await fetch('/push/vapid-key/');
    const { publicKey } = await keyResp.json();
    if (!publicKey) return;  // VAPID not configured on server

    // Convert base64url key to Uint8Array
    const vapidKey = urlBase64ToUint8Array(publicKey);

    // Check if already subscribed
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      // Request permission and subscribe
      const perm = await Notification.requestPermission();
      if (perm !== 'granted') return;

      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: vapidKey,
      });
    }

    // Send subscription to server
    const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
    await fetch('/push/subscribe/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(sub.toJSON()),
    });
  } catch (_e) {
    // Silent fail — push is an enhancement, not a requirement
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

/* ── Mobile Filter Drawer ──────────────────────────────────────────── */
function initMobileFilterDrawer() {
  const toggleBtn = document.getElementById('mobileFilterToggle');
  const closeBtn  = document.getElementById('mobileFilterClose');
  const sidebar   = document.getElementById('filtersSidebar');
  const overlay   = document.getElementById('mobileFilterOverlay');
  if (!toggleBtn || !sidebar) return;

  function openDrawer() {
    sidebar.classList.add('mobile-open');
    overlay?.classList.add('active');
    overlay?.removeAttribute('aria-hidden');
    toggleBtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    sidebar.classList.remove('mobile-open');
    overlay?.classList.remove('active');
    overlay?.setAttribute('aria-hidden', 'true');
    toggleBtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  toggleBtn.addEventListener('click', openDrawer);
  closeBtn?.addEventListener('click', closeDrawer);
  overlay?.addEventListener('click', closeDrawer);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) closeDrawer();
  });
}

document.addEventListener('DOMContentLoaded', initMobileFilterDrawer);
