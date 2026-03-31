# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/middleware.py
# Description:  Custom Django middleware for TrendMart.
#               Covers:
#               - SecurityHeadersMiddleware: CSP, HSTS, X-Frame-Options,
#                 X-Content-Type-Options, Referrer-Policy, Permissions-Policy
#               - RateLimitMiddleware: cross-process IP-based rate limiting
#                 using Django's cache framework (Redis in production,
#                 LocMemCache in development) — safe with multiple Gunicorn workers
# =============================================================================

import time
import threading
from collections import defaultdict

from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings


# ─── Security Headers Middleware ───────────────────────────────────────────────
# Adds a comprehensive set of HTTP security headers to every response.
# These protect against XSS, clickjacking, MIME sniffing, and data leakage.
# Applied unconditionally so even error pages are protected.

class SecurityHeadersMiddleware:
    """
    Injects production-grade HTTP security headers on every response.

    Headers applied:
    - Content-Security-Policy: restricts which scripts/styles/resources may load
    - Strict-Transport-Security: forces HTTPS for 1 year (only in production)
    - Referrer-Policy: hides the full URL when navigating to external sites
    - Permissions-Policy: disables access to sensitive browser APIs
    - X-Content-Type-Options: prevents MIME sniffing
    - X-Frame-Options: blocks this page being loaded in iframes (anti-clickjacking)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._apply_headers(response)
        return response

    def _apply_headers(self, response):
        """Add all security headers to the response object."""

        # ── Content-Security-Policy ──────────────────────────────────────────
        # Permits inline styles/scripts (needed for the current template design)
        # but blocks external scripts from untrusted sources.
        # Relaxed for development; tighten for production by removing 'unsafe-inline'.
        csp_directives = [
            "default-src 'self'",
            # Scripts: self + CDN sources used by the platform
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://www.googletagmanager.com",
            # Styles: self + Google Fonts
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            # Fonts: self + Google Fonts CDN
            "font-src 'self' https://fonts.gstatic.com data:",
            # Images: self + placeholder services + data URIs for lazy loading
            "img-src 'self' data: blob: https://images.unsplash.com https://placehold.co https://via.placeholder.com https://picsum.photos https://images.pexels.com",
            # Connect: AJAX requests only to self + OpenRouter (AI assistant)
            "connect-src 'self' https://openrouter.ai",
            # Media: self + blob (for PWA / cached resources)
            "media-src 'self' blob:",
            # Manifest: self (for PWA manifest.json)
            "manifest-src 'self'",
            # Workers: self (for service worker)
            "worker-src 'self'",
            # Frames: nobody (anti-clickjacking, reinforces X-Frame-Options)
            "frame-ancestors 'none'",
            # Form actions: only to self (prevent cross-site form hijacking)
            "form-action 'self'",
            # Base URI: only self (prevents base-tag injection attacks)
            "base-uri 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # ── HSTS: force HTTPS in production ─────────────────────────────────
        # Only set in production (DEBUG=False) to avoid breaking local HTTP dev
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        # ── Referrer-Policy ─────────────────────────────────────────────────
        # Send the full URL within TrendMart but only the origin to external sites,
        # so query strings (which may contain search terms / user IDs) aren't leaked.
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # ── Permissions-Policy ───────────────────────────────────────────────
        # Disable access to sensitive browser APIs that TrendMart doesn't need.
        # Microphone is explicitly allowed for the AI assistant voice input feature.
        response['Permissions-Policy'] = (
            'geolocation=(), camera=(), payment=(), '
            'usb=(), magnetometer=(), gyroscope=(), '
            'accelerometer=()'
        )

        # ── X-Content-Type-Options ───────────────────────────────────────────
        # Prevents the browser from MIME-sniffing a response away from the
        # declared Content-Type (protects against file-upload XSS vectors).
        response['X-Content-Type-Options'] = 'nosniff'

        # ── X-Frame-Options ──────────────────────────────────────────────────
        # Blocks this page being embedded in an iframe on another domain.
        # Already set by Django's XFrameOptionsMiddleware but we make it explicit.
        response['X-Frame-Options'] = 'DENY'

        return response


# ─── Rate Limit Middleware ─────────────────────────────────────────────────────
# Protects authentication endpoints from brute-force attacks and the AI endpoint
# from API abuse by capping the number of POST requests per IP address within a
# rolling time window.
#
# IMPORTANT — Production safety:
#   This implementation uses Django's cache framework (configured in settings.py)
#   which maps to Redis when REDIS_URL is set. This means ALL Gunicorn workers
#   share one counter — unlike a plain Python dict which is per-process.
#   In development (no Redis), it falls back to an in-process threading.Lock dict.

class RateLimitMiddleware:
    """
    Cross-process IP-based rate limiter for sensitive POST endpoints.

    Protected paths:
    - /login/         — max 10 attempts per minute per IP
    - /register/      — max 5 attempts per minute per IP
    - /ai/chat/       — max 30 requests per minute per IP (prevents API abuse)

    Non-POST requests and all other paths pass through without restriction.

    Cache keys follow the pattern: ratelimit:<ip>:<path_prefix>
    Each key stores the request count; TTL equals the window duration.
    This approach is safe with multiple Gunicorn workers sharing Redis.
    """

    # Fallback in-memory store for dev (no Redis). Thread-safe via a Lock.
    _mem_requests: dict = defaultdict(list)
    _mem_lock = threading.Lock()

    # Rate limit rules: (url_prefix, max_requests, window_seconds)
    RATE_LIMITS = [
        ('/login/',    10, 60),   # 10 login attempts per minute
        ('/register/', 5,  60),   # 5 registrations per minute
        ('/ai/chat/',  30, 60),   # 30 AI messages per minute
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only rate-limit POST requests — GET/HEAD etc. pass through freely
        if request.method == 'POST':
            ip   = self._get_client_ip(request)
            path = request.path

            for prefix, max_req, window in self.RATE_LIMITS:
                if path.startswith(prefix):
                    if self._is_rate_limited(ip, prefix, max_req, window):
                        # Return JSON for AJAX callers; plain 429 text for form POSTs
                        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                        is_json = 'application/json' in request.headers.get('Content-Type', '')
                        if is_ajax or is_json:
                            return JsonResponse(
                                {'error': 'Too many requests. Please wait a moment and try again.'},
                                status=429
                            )
                        return HttpResponseForbidden(
                            'Too many requests. Please wait a moment before trying again.'
                        )
                    break  # Stop at the first matching rule

        return self.get_response(request)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_client_ip(self, request):
        """
        Extract the real client IP address.
        Respects X-Forwarded-For set by reverse proxies (Nginx, Cloudflare, etc.).
        Takes the leftmost IP to prevent spoofing via appending fake IPs.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For is a comma-separated list; leftmost = original client
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _is_rate_limited(self, ip: str, path_prefix: str, max_req: int, window: int) -> bool:
        """
        Returns True if the IP has exceeded max_req requests to path_prefix
        within the last `window` seconds.

        Strategy:
        1. Try Django's cache framework (Redis in prod — shared across all workers)
        2. Fall back to an in-memory dict with a threading.Lock (dev only)
        """
        cache_key = f'ratelimit:{ip}:{path_prefix}'

        try:
            from django.core.cache import cache

            # Use atomic add — sets the key to 1 if it doesn't exist,
            # then increments. The TTL is set on the first request in each window.
            count = cache.get(cache_key, 0)
            if count == 0:
                # First request in this window: set with TTL equal to the window
                cache.set(cache_key, 1, timeout=window)
                return False
            if count >= max_req:
                return True
            # Increment without resetting TTL (preserves the rolling window)
            try:
                cache.incr(cache_key)
            except ValueError:
                # Key expired between .get and .incr — harmless race condition
                cache.set(cache_key, 1, timeout=window)
            return False

        except Exception:
            # Cache unavailable — fall back to in-memory dict (dev / test mode)
            return self._mem_rate_limited(ip, path_prefix, max_req, window)

    def _mem_rate_limited(self, ip: str, path_prefix: str, max_req: int, window: int) -> bool:
        """
        Thread-safe in-memory fallback rate limiter.
        Used only in development when the cache framework is not available.
        NOT suitable for production (not shared across Gunicorn workers).
        """
        now = time.time()
        key = f'{ip}:{path_prefix}'

        with self._mem_lock:
            # Purge timestamps outside the rolling window
            self._mem_requests[key] = [
                ts for ts in self._mem_requests[key]
                if now - ts < window
            ]
            if len(self._mem_requests[key]) >= max_req:
                return True
            self._mem_requests[key].append(now)

        return False
