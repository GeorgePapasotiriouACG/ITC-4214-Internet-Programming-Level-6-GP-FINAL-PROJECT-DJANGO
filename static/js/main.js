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
function initAIChat() {
  const trigger = document.getElementById('ai-chat-trigger');
  const panel = document.getElementById('ai-chat-panel');
  const closeBtn = document.getElementById('ai-chat-close');
  const clearBtn = document.getElementById('ai-clear-chat');
  const input = document.getElementById('ai-input');
  const sendBtn = document.getElementById('ai-send');
  const messages = document.getElementById('ai-messages');
  const charCount = document.getElementById('ai-char-count');
  const statusLine = document.getElementById('ai-status-line');
  if (!trigger || !panel) return;

  let isOpen = false;

  // Update the status dot in the AI header (online / thinking / error)
  function setStatus(state) {
    if (!statusLine) return;
    const states = {
      online:   '● Online &mdash; ready to help',
      thinking: '● Thinking…',
      error:    '● Connection issue — retrying',
    };
    statusLine.innerHTML = states[state] || states.online;
    statusLine.style.color = state === 'error' ? '#EF4444' : state === 'thinking' ? '#F59E0B' : '';
  }

  function openPanel() {
    isOpen = true;
    panel.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
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

  // Clear chat — wipes all messages from the UI and resets session memory on the server
  clearBtn?.addEventListener('click', () => {
    if (!messages) return;
    // Clear the message area, keeping only the welcome message
    messages.innerHTML = '<div class="ai-msg bot"><div class="ai-bubble">Chat cleared! ✨ I\'m ready to help — what can I find for you?</div></div>';
    // Tell the backend to reset the session conversation history
    fetchPost('/ai/chat/', { action: 'clear_history' }).catch(() => {});
    if (input) { input.value = ''; input.focus(); }
    if (charCount) charCount.textContent = '0/300';
  });

  if (input && charCount) {
    input.addEventListener('input', () => {
      const len = input.value.length;
      const max = 300;
      charCount.textContent = `${len}/${max}`;
      charCount.className = 'ai-char-count' + (len > 250 ? ' near-limit' : '') + (len >= max ? ' at-limit' : '');
    });
  }

  function appendMsg(html, type) {
    const msg = document.createElement('div');
    msg.className = `ai-msg ${type}`;
    msg.innerHTML = `<div class="ai-bubble">${html}</div>`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
    return msg;
  }

  function formatBotText(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/~~(.*?)~~/g, '<s>$1</s>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--primary);text-decoration:underline;font-weight:600">$1</a>')
      .replace(/🔗<a href="([^"]+)"[^>]*>([^<]+)<\/a>/g, '<a href="$1" class="ai-product-card"><span class="ai-product-card-name">$2</span></a>')
      .replace(/\n/g, '<br>');
  }

  function showTyping() {
    const t = document.createElement('div');
    t.className = 'ai-msg bot'; t.id = 'ai-typing-indicator';
    t.innerHTML = '<div class="ai-typing"><span></span><span></span><span></span></div><span class="ai-thinking-label">thinking…</span>';
    messages.appendChild(t); messages.scrollTop = messages.scrollHeight;
    return t;
  }

  function updateQuickBtns(context) {
    const quickBtns = document.getElementById('ai-quick-btns');
    if (!quickBtns) return;
    const contextBtns = {
      product: ['➕ Add to cart', '⭐ Reviews', '📦 Stock', '💰 Best price'],
      order: ['📍 Track order', '↩️ Return item', '🧾 Invoice', '📞 Support'],
      default: ['🔥 Hot deals', '📦 My orders', '💡 Recommend me', '↩️ Return policy', '🔍 Search products', '🏷️ Best price'],
    };
    const btns = contextBtns[context] || contextBtns.default;
    quickBtns.innerHTML = btns.map(b => `<button class="ai-quick-btn">${b}</button>`).join('');
    quickBtns.querySelectorAll('.ai-quick-btn').forEach(btn => {
      btn.addEventListener('click', () => sendMessage(btn.textContent.trim()));
    });
  }

  function sendMessage(text) {
    if (!text.trim()) return;
    appendMsg(text.replace(/</g, '&lt;'), 'user');
    if (input) { input.value = ''; if (charCount) charCount.textContent = '0/300'; }
    sendBtn?.classList.add('sending');
    setTimeout(() => sendBtn?.classList.remove('sending'), 400);
    setStatus('thinking');  // Show "Thinking…" in header while waiting for AI

    const typing = showTyping();
    fetchPost('/ai/chat/', { message: text })
      .then(r => r.json())
      .then(data => {
        typing.remove();
        setStatus('online');  // Back to "Online" once reply arrives
        appendMsg(formatBotText(data.reply || "Sorry, I couldn't process that."), 'bot');
        if (text.match(/order|track|delivery/i)) updateQuickBtns('order');
        else if (text.match(/product|show|find|search/i)) updateQuickBtns('product');
        else updateQuickBtns('default');
      })
      .catch(() => {
        typing.remove();
        setStatus('error');
        setTimeout(() => setStatus('online'), 4000);  // Recover status after 4s
        appendMsg("Sorry, I'm having trouble connecting. Please try again!", 'bot');
      });
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

// ── Init all ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initDarkMode();
  initHeroParticles();
  Toast.init();
  initDropdowns();
  initMobileNav();
  initScrollToTop();
  initSearchAutocomplete();
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
});
