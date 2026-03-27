import re
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Custom middleware to add additional security headers
    """
    
    def process_response(self, request, response):
        # Add Content Security Policy header if configured
        if hasattr(settings, 'CSP_DEFAULT_SRC'):
            csp_directives = [
                f"default-src {getattr(settings, 'CSP_DEFAULT_SRC', '')}",
                f"script-src {getattr(settings, 'CSP_SCRIPT_SRC', '')}",
                f"style-src {getattr(settings, 'CSP_STYLE_SRC', '')}",
                f"font-src {getattr(settings, 'CSP_FONT_SRC', '')}",
                f"img-src {getattr(settings, 'CSP_IMG_SRC', '')}",
                f"connect-src {getattr(settings, 'CSP_CONNECT_SRC', '')}",
                f"frame-ancestors {getattr(settings, 'CSP_FRAME_ANCESTORS', '')}",
                f"form-action {getattr(settings, 'CSP_FORM_ACTION', '')}",
                f"base-uri {getattr(settings, 'CSP_BASE_URI', '')}",
            ]
            csp_header = '; '.join(directive for directive in csp_directives if directive.split()[1])
            response['Content-Security-Policy'] = csp_header
        
        # Add additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = getattr(settings, 'SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin')
        response['Cross-Origin-Opener-Policy'] = getattr(settings, 'SECURE_CROSS_ORIGIN_OPENER_POLICY', 'same-origin')
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
        
        return response


class XSSProtectionMiddleware(MiddlewareMixin):
    """
    Middleware to detect and block potential XSS attacks
    """
    
    # Common XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'expression\s*\(',
        r'@import',
        r'<\s*script',
        r'<\s*img[^>]*src\s*=\s*["\']?\s*javascript:',
    ]
    
    def process_request(self, request):
        """
        Check request parameters for potential XSS attacks
        """
        # Check GET parameters
        for param, value in request.GET.items():
            if self._contains_xss(value):
                return HttpResponseForbidden("Potential XSS attack detected in request parameters.")
        
        # Check POST data
        if hasattr(request, 'POST') and request.POST:
            for param, value in request.POST.items():
                if self._contains_xss(value):
                    return HttpResponseForbidden("Potential XSS attack detected in request data.")
        
        return None
    
    def _contains_xss(self, text):
        """
        Check if text contains potential XSS patterns
        """
        if not isinstance(text, str):
            return False
        
        text_lower = text.lower()
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True
        return False


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """
    Basic SQL injection protection middleware
    Note: This is additional protection - Django ORM provides primary protection
    """
    
    SQL_INJECTION_PATTERNS = [
        r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)',
        r'(--|#|\/\*|\*\/)',
        r'(\b(or|and)\s+\d+\s*=\s*\d+)',
        r'(\b(or|and)\s+\'\w+\'\s*=\s*\'\w+\')',
        r'(\b(or|and)\s+\"[^"]*\"\s*=\s*\"[^"]*\")',
        r'(;\s*(drop|delete|update|insert)\s)',
        r'(\b(waitfor\s+delay\b)',
        r'(\b(benchmark|sleep)\s*\()',
    ]
    
    def process_request(self, request):
        """
        Check request parameters for potential SQL injection patterns
        """
        # Skip admin and internal paths
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return None
        
        # Check GET parameters
        for param, value in request.GET.items():
            if self._contains_sql_injection(value):
                return HttpResponseForbidden("Potential SQL injection attack detected.")
        
        # Check POST data (excluding forms that might contain legitimate content)
        if hasattr(request, 'POST') and request.POST:
            for param, value in request.POST.items():
                # Skip common form fields that might contain legitimate text
                if param in ['description', 'review', 'content', 'message', 'comment']:
                    continue
                if self._contains_sql_injection(value):
                    return HttpResponseForbidden("Potential SQL injection attack detected.")
        
        return None
    
    def _contains_sql_injection(self, text):
        """
        Check if text contains potential SQL injection patterns
        """
        if not isinstance(text, str):
            return False
        
        text_lower = text.lower()
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware to prevent brute force attacks
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Implement basic rate limiting
        """
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for authenticated users with good standing
        if request.user.is_authenticated and not request.user.profile.role == 'admin':
            return None
        
        # Check rate limit for sensitive endpoints
        sensitive_endpoints = ['/login/', '/register/', '/password-reset/']
        if request.path in sensitive_endpoints:
            if self._is_rate_limited(client_ip):
                return HttpResponseForbidden("Too many requests. Please try again later.")
        
        return None
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_rate_limited(self, client_ip):
        """
        Check if IP has exceeded rate limit
        """
        # Simple implementation - in production, use Redis or similar
        import time
        current_time = time.time()
        
        # Clean old entries (older than 1 hour)
        self.request_counts = {
            ip: (count, timestamp) 
            for ip, (count, timestamp) in self.request_counts.items()
            if current_time - timestamp < 3600
        }
        
        # Check current IP
        if client_ip in self.request_counts:
            count, timestamp = self.request_counts[client_ip]
            if current_time - timestamp < 300:  # 5 minutes
                if count > 20:  # More than 20 requests in 5 minutes
                    return True
                self.request_counts[client_ip] = (count + 1, timestamp)
            else:
                self.request_counts[client_ip] = (1, current_time)
        else:
            self.request_counts[client_ip] = (1, current_time)
        
        return False
