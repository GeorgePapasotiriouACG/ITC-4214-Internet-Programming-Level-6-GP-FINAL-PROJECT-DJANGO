# 🛍️ TrendMart — E-Commerce Platform

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white"/>
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black"/>
  <img src="https://img.shields.io/badge/OpenRouter-AI-7C3AED?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/PWA-Ready-5A0FC8?style=for-the-badge&logo=googlechrome&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge"/>
</p>

> **Author:** George Papasotiriou · **Built:** March 2026

A full-stack e-commerce platform built with Django and Vanilla JavaScript. Supports three user roles (Customer, Retailer, Administrator), an AI shopping assistant, voice accessibility, and a Progressive Web App layer — no frontend framework required.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.2 (Python 3.13) |
| **Database** | SQLite (dev) · PostgreSQL-ready via `dj-database-url` |
| **Frontend** | HTML5 · CSS3 · Vanilla JavaScript (ES6+) |
| **AI / LLM** | OpenRouter API — model-agnostic (NVIDIA Nemotron, GPT-4o-mini, Gemini, Claude) |
| **Image Processing** | Pillow — auto WebP conversion on upload |
| **Charts** | Chart.js — retailer & admin analytics dashboards |
| **Voice** | Web Speech API (STT) · SpeechSynthesis (TTS) — browser-native |
| **PWA** | Service Worker · Web App Manifest · push notifications |
| **Real-time** | Django Channels + Redis (WebSockets for stock/cart updates) |
| **Cache** | LocMemCache (dev) · Redis (production) |
| **Static Files** | WhiteNoise (production) |
| **Config** | python-dotenv — all secrets loaded from `.env` |
| **Deployment** | Gunicorn · Docker · GitHub Actions CI |

---

## ✨ Features

### 🏪 Catalogue & Shopping
- Hierarchical product categories with advanced filters (price, brand, colour, size, sale toggle)
- Instant search overlay with fuzzy matching and autocomplete
- Product image carousel · zoom on hover · video demos
- Countdown timers on sale items · low-stock badges
- Persistent cart for guests and logged-in users · mini-cart drawer
- Promo / coupon codes · save-for-later · multi-step checkout

### 👤 Users & Personalisation
- Three roles: **Customer**, **Retailer**, **Administrator** — enforced server-side
- Personalised dashboard: orders, wishlist, loyalty points, recommendations
- Loyalty points (1pt / $1 spent) · referral programme
- Saved addresses · profile avatar · notification bell
- Dark / light mode · preference saved per user

### ⭐ Reviews & Social Proof
- AJAX star ratings · photo reviews · verified purchase badge
- Review helpfulness votes · retailer replies · rating distribution bar
- Product Q&A section

### 🤖 AI Shopping Assistant
- Floating chat bubble on every page
- Connects to OpenRouter LLM with live product catalogue injected into the system prompt
- Knows the user's cart, orders, wishlist, loyalty points, and remembered preferences
- Image upload for visual product search (vision API)
- Frustration detection — adapts tone when negative sentiment is detected
- Role-aware: customer, retailer, and admin each see different information
- **Graceful fallback** — keyword engine answers without any API key
- Streaming responses (SSE) · conversation export · chat history

### 🎤 Voice Accessibility Assistant
- Full-screen voice overlay with ChatGPT-style animated orb
- Hands-free shopping: *"I want a Macbook Pro"* → searches for product
- Navigation commands (Experimental): *"go to cart"*, *"show my orders"*, *"open FAQ"*
- Accessibility hub: colour-blind modes, text resize, dyslexia font, high contrast

### 🛍️ Retailer Portal
- Custom dashboard with sales analytics (Chart.js)
- Product management · bulk CSV import · AI-generated descriptions
- Public storefront page · product approval workflow
- Product variants (size/colour) with individual stock and pricing

### 🔐 Security & Performance
- CSRF, XSS auto-escaping, X-Frame-Options, HSTS, secure cookies
- `SECRET_KEY` guard — raises `RuntimeError` if insecure key used in production
- Rate limiting middleware · audit log · 2FA (TOTP)
- `select_related` / `prefetch_related` to eliminate N+1 queries
- Images lazy-loaded · WebP conversion · Redis caching

### 📱 PWA & Mobile
- Installable on Android/iOS ("Add to Home Screen")
- Offline fallback page via Service Worker
- Push notifications for flash deals and order updates
- Responsive on all screen sizes (320px → 4K)
- Mobile bottom navigation bar

---

## 🚀 Quick Start

```bash
git clone https://github.com/your-username/trendmart.git
cd trendmart

python -m venv venv            # Download latest releashe and run on VS Code with original .env file
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

pip install django pillow python-dotenv

cp .env.example .env           # fill in SECRET_KEY + OPENROUTER_API_KEY

pip install django-debug-toolbar
pip install whitenoise

python manage.py migrate  
python manage.py runserver

pip install redis              # For Redis Script
python redis_attack_demo.py --host localhost --port 6379

# To deploy on Render, use docker command: bash start.sh
Render Link: https://itc-4214-internet-programming-level-6-gp.onrender.com/
```


Open **http://127.0.0.1:8000**

### Default credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Retailer | `techretailer` | `retail123` |
| Customer | `testuser` | `test123` |

> **Note:** The `.env` file is listed in `.gitignore` and is never committed. Copy `.env.example` to `.env` and fill in your own keys.

---

## 📄 License

MIT © George Papasotiriou
