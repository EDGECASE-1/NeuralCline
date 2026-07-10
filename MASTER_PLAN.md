# 🧠 NEURALCLINE v2.0 — MASTER PLAN

> **Session Safety Layer for Agentic AI**
> **Codename:** EDGECASE | **Version:** 2.0.0
> **Status:** 🟡 IN PROGRESS — See checklist below
> **Canonical Reference:** This file is the single source of truth across all sessions.

---

## 📋 LIVING CHECKLIST — Updated Every Session

### Phase 0: Foundation (Current)
- [ ] **0.1** Create MASTER_PLAN.md (this file) — canonical reference
- [ ] **0.2** Create `lib/session_core.py` — universal API, model-agnostic
- [ ] **0.3** Create adapter system (`lib/adapters/`) — Cline, Copilot, Cursor, Codeium, Generic
- [ ] **0.4** Rewrite `lib/state_engine.py` with `fcntl.flock` file locking
- [ ] **0.5** Create `lib/timing_engine.py` — statistical timing with log-normal distributions
- [ ] **0.6** Create `lib/anomaly_detector.py` — Isolation Forest + online learning
- [ ] **0.7** Create `lib/metrics_collector.py` — verifiable, published metrics
- [ ] **0.8** Rewrite `hooks/shell-hooks.sh` — proper chaining, uninstall support
- [ ] **0.9** Rewrite `hooks/pre-tool-guard.sh` — uses new statistical engine
- [ ] **0.10** Rewrite `hooks/post-tool-state.sh` — uses new metrics collector

### Phase 1: Payment & Monetization
- [ ] **1.1** Create `lib/payment/` — Stripe integration with working code
- [ ] **1.2** Create `lib/payment/stripe_checkout.py` — serverless checkout handler
- [ ] **1.3** Create `lib/payment/license_manager.py` — license key generation & validation
- [ ] **1.4** Create `lib/payment/webhook_handler.py` — Stripe webhook receiver
- [ ] **1.5** Create `lib/payment/pricing_tiers.py` — tier definitions with feature flags
- [ ] **1.6** Create `docs/pricing.html` — working pricing page with Stripe buttons
- [ ] **1.7** Create `docs/checkout.html` — Stripe Checkout integration page
- [ ] **1.8** Create `docs/portal.html` — customer portal for subscription management
- [ ] **1.9** Create `docs/success.html` / `docs/cancel.html` — post-checkout pages
- [ ] **1.10** Create `.github/workflows/payment-test.yml` — CI for payment flow

### Phase 2: Agentic AI Optimization
- [ ] **2.1** Create `lib/context_manager.py` — context window pressure monitoring
- [ ] **2.2** Create `lib/session_compressor.py` — lossless session state compression
- [ ] **2.3** Create `lib/checkpoint_strategy.py` — adaptive checkpoint frequency
- [ ] **2.4** Create `lib/recovery_orchestrator.py` — multi-strategy recovery
- [ ] **2.5** Create `lib/agent_bridge.py` — universal agent communication protocol
- [ ] **2.6** Create `lib/state_sync.py` — cross-session state synchronization
- [ ] **2.7** Create `lib/context_window_tracker.py` — real-time context usage monitoring

### Phase 3: Statistical Engine (Replace Heuristics)
- [ ] **3.1** Implement log-normal distribution fitting for execution times
- [ ] **3.2** Implement percentile-based timeout prediction (p50, p95, p99)
- [ ] **3.3** Implement logistic regression for crash probability
- [ ] **3.4** Implement online model retraining (every N events)
- [ ] **3.5** Implement calibration curves for prediction reliability
- [ ] **3.6** Implement Isolation Forest for anomaly detection
- [ ] **3.7** Implement Prophet/ARIMA for time series forecasting
- [ ] **3.8** Implement Q-learning for threshold optimization
- [ ] **3.9** Create `lib/statistical/` package with all models
- [ ] **3.10** Create model validation suite (backtesting against historical data)

### Phase 4: Self-Learning (Actual ML)
- [ ] **4.1** Create `lib/learning/` package
- [ ] **4.2** Implement online anomaly detection (One-Class SVM)
- [ ] **4.3** Implement time series forecasting with prediction intervals
- [ ] **4.4** Implement reinforcement learning for threshold adjustment
- [ ] **4.5** Implement feature engineering pipeline
- [ ] **4.6** Implement model persistence (save/load trained models)
- [ ] **4.7** Implement model versioning and rollback
- [ ] **4.8** Create training data pipeline (collect, label, validate)
- [ ] **4.9** Create model evaluation dashboard
- [ ] **4.10** Create A/B testing framework for model comparison

### Phase 5: File Locking & Concurrency
- [ ] **5.1** Implement `LockedJSONFile` context manager with `fcntl.flock`
- [ ] **5.2** Implement retry logic for lock acquisition
- [ ] **5.3** Implement lock timeout and deadlock detection
- [ ] **5.4** Implement atomic writes (write to temp, rename)
- [ ] **5.5** Implement concurrent session merging
- [ ] **5.6** Create stress test for concurrent access
- [ ] **5.7** Create corruption detection and repair utility

### Phase 6: Shell Hooks (Proper Chaining)
- [ ] **6.1** Rewrite `hooks/shell-hooks.sh` with save/restore pattern
- [ ] **6.2** Implement `__neural_uninstall` function
- [ ] **6.3** Implement VS Code compatibility without function patching
- [ ] **6.4** Implement zsh compatibility
- [ ] **6.5** Implement fish shell compatibility
- [ ] **6.6** Create hook installation verification
- [ ] **6.7** Create hook conflict detection

### Phase 7: Verifiable Metrics
- [ ] **7.1** Implement `MetricsCollector` with append-only log
- [ ] **7.2** Implement session survival rate (measured, not claimed)
- [ ] **7.3** Implement recovery time tracking (p50, p95, p99)
- [ ] **7.4** Implement environmental variance/negative tracking
- [ ] **7.5** Implement EEF accuracy tracking
- [ ] **7.6** Implement timeout prediction accuracy
- [ ] **7.7** Create public metrics dashboard
- [ ] **7.8** Create metrics export (JSON, CSV, Prometheus format)
- [ ] **7.9** Create metrics alerting (threshold-based)
- [ ] **7.10** Create metrics retention and pruning

### Phase 8: Ethical Marketing & Documentation
- [ ] **8.1** Remove presence engine directory (`presence-engine/`)
- [ ] **8.2** Remove INJECTION_MAP.md
- [ ] **8.3** Remove INFINITE_PERSISTENCE.md (replace with honest docs)
- [ ] **8.4** Rewrite README.md with accurate terminology
- [ ] **8.5** Rewrite EXECUTIVE_BRIEF.md with verifiable claims
- [ ] **8.6** Rewrite MARKET_MAP.md with realistic TAM
- [ ] **8.7** Rewrite PROJECTION_METRICS.md with grounded projections
- [ ] **8.8** Rewrite ECONOMIC_IMPACT.md with honest financials
- [ ] **8.9** Create `docs/ARCHITECTURE.md` — honest technical documentation
- [ ] **8.10** Create `docs/ROADMAP.md` — realistic development timeline
- [ ] **8.11** Create `docs/BENCHMARKS.md` — published benchmark results
- [ ] **8.12** Create `docs/COMPARISON.md` — honest comparison with alternatives
- [ ] **8.13** Create `docs/ETHICS.md` — ethical guidelines and transparency report

### Phase 9: Financial Model (Grounded)
- [ ] **9.1** Create `docs/financials/PROJECTIONS.md` — three-tier model
- [ ] **9.2** Create `docs/financials/COST_ANALYSIS.md` — infrastructure costs
- [ ] **9.3** Create `docs/financials/REVENUE_MODEL.md` — pricing rationale
- [ ] **9.4** Create `docs/financials/FUNDING_ROADMAP.md` — grant/VC pathway
- [ ] **9.5** Create `docs/financials/BREAK_EVEN.md` — break-even analysis

### Phase 10: Verification & Validation
- [ ] **10.1** Create test suite for all adapters
- [ ] **10.2** Create benchmark suite for crash recovery
- [ ] **10.3** Create benchmark suite for timing prediction accuracy
- [ ] **10.4** Create benchmark suite for anomaly detection
- [ ] **10.5** Create integration tests for payment flow
- [ ] **10.6** Create stress tests for concurrent access
- [ ] **10.7** Create fuzzing tests for JSON/file operations
- [ ] **10.8** Create CI/CD pipeline (`.github/workflows/`)
- [ ] **10.9** Create static analysis configuration
- [ ] **10.10** Create coverage reporting (target: 90%+)

### Phase 11: Final Audit
- [ ] **11.1** Run full test suite — all pass
- [ ] **11.2** Run benchmark suite — results published
- [ ] **11.3** Run static analysis — zero critical issues
- [ ] **11.4** Run security audit — zero vulnerabilities
- [ ] **11.5** Verify payment flow end-to-end
- [ ] **11.6** Verify all adapters functional
- [ ] **11.7** Verify metrics collector producing real data
- [ ] **11.8** Verify documentation accuracy
- [ ] **11.9** Generate 10/10 audit report
- [ ] **11.10** Tag v2.0.0 release

---

## 🏗 ARCHITECTURE OVERVIEW

```
/root/NeuralCline/
│
├── MASTER_PLAN.md                    ← THIS FILE — canonical reference
├── README.md                         ← Rewritten with accurate terminology
├── install.sh                        ← Updated for v2.0
├── LICENSE                           ← MIT + Commercial
│
├── lib/                              ← Core library (model-agnostic)
│   ├── session_core.py               ← Universal API entry point
│   ├── state_engine.py               ← Rewritten with file locking
│   ├── timing_engine.py              ← Statistical timing (log-normal)
│   ├── anomaly_detector.py           ← Isolation Forest + online learning
│   ├── metrics_collector.py          ← Verifiable metrics
│   ├── context_manager.py            ← Context window pressure monitoring
│   ├── session_compressor.py         ← Lossless state compression
│   ├── checkpoint_strategy.py        ← Adaptive checkpoint frequency
│   ├── recovery_orchestrator.py      ← Multi-strategy recovery
│   ├── agent_bridge.py               ← Universal agent communication
│   ├── state_sync.py                 ← Cross-session state sync
│   ├── context_window_tracker.py     ← Real-time context usage
│   │
│   ├── adapters/                     ← Model-agnostic adapters
│   │   ├── __init__.py
│   │   ├── base.py                   ← Abstract base adapter
│   │   ├── adapter_cline.py          ← Cline integration
│   │   ├── adapter_copilot.py        ← GitHub Copilot integration
│   │   ├── adapter_cursor.py         ← Cursor integration
│   │   ├── adapter_codeium.py        ← Codeium integration
│   │   └── adapter_generic.py        ← Any shell-based AI agent
│   │
│   ├── statistical/                  ← Statistical models
│   │   ├── __init__.py
│   │   ├── log_normal.py             ← Log-normal distribution fitting
│   │   ├── logistic_regression.py    ← Crash probability model
│   │   ├── isolation_forest.py       ← Anomaly detection
│   │   ├── time_series.py            ← Prophet/ARIMA forecasting
│   │   └── q_learning.py             ← Threshold optimization
│   │
│   ├── learning/                     ← ML learning system
│   │   ├── __init__.py
│   │   ├── online_anomaly.py         ← One-Class SVM online learning
│   │   ├── forecasting.py            ← Time series with prediction intervals
│   │   ├── threshold_rl.py           ← RL for threshold adjustment
│   │   ├── feature_engineering.py    ← Feature pipeline
│   │   ├── model_persistence.py      ← Save/load/version models
│   │   └── training_pipeline.py      ← Data collection & training
│   │
│   └── payment/                      ← Payment integration
│       ├── __init__.py
│       ├── stripe_checkout.py        ← Stripe Checkout session handler
│       ├── license_manager.py        ← License key generation & validation
│       ├── webhook_handler.py        ← Stripe webhook receiver
│       └── pricing_tiers.py          ← Tier definitions with feature flags
│
├── hooks/                            ← Shell integration hooks
│   ├── shell-hooks.sh                ← Rewritten with proper chaining
│   ├── pre-tool-guard.sh             ← Uses statistical engine
│   ├── post-tool-state.sh            ← Uses metrics collector
│   ├── generate-handoff.sh           ← Updated for v2.0
│   └── diagnose.sh                   ← Updated for v2.0
│
├── docs/                             ← Documentation
│   ├── ARCHITECTURE.md               ← Honest technical documentation
│   ├── ROADMAP.md                    ← Realistic development timeline
│   ├── BENCHMARKS.md                 ← Published benchmark results
│   ├── COMPARISON.md                 ← Honest comparison with alternatives
│   ├── ETHICS.md                     ← Ethical guidelines
│   ├── pricing.html                  ← Working pricing page with Stripe
│   ├── checkout.html                 ← Stripe Checkout integration
│   ├── portal.html                   ← Customer portal
│   ├── success.html                  ← Post-checkout success
│   ├── cancel.html                   ← Post-checkout cancel
│   │
│   └── financials/                   ← Financial documentation
│       ├── PROJECTIONS.md            ← Three-tier model
│       ├── COST_ANALYSIS.md          ← Infrastructure costs
│       ├── REVENUE_MODEL.md          ← Pricing rationale
│       ├── FUNDING_ROADMAP.md        ← Grant/VC pathway
│       └── BREAK_EVEN.md             ← Break-even analysis
│
├── tests/                            ← Test suite
│   ├── test_adapters.py
│   ├── test_state_engine.py
│   ├── test_timing_engine.py
│   ├── test_anomaly_detector.py
│   ├── test_metrics_collector.py
│   ├── test_payment.py
│   ├── test_hooks.py
│   ├── test_concurrency.py
│   ├── test_statistical.py
│   ├── test_learning.py
│   └── test_integration.py
│
├── benchmarks/                       ← Benchmark suite
│   ├── benchmark_crash_recovery.py
│   ├── benchmark_timing_prediction.py
│   ├── benchmark_anomaly_detection.py
│   └── benchmark_concurrent_access.py
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    ← CI/CD pipeline
│       ├── test.yml                  ← Test runner
│       ├── benchmark.yml             ← Benchmark runner
│       └── payment-test.yml          ← Payment flow test
│
└── session-state/                    ← Runtime state (gitignored)
    ├── current-state.json
    ├── checkpoint.json
    ├── crash-log.ndjson
    ├── failure-points.json
    ├── timing-history.json
    └── session-memory.json
```

---

## 💳 PAYMENT INTEGRATION — Working Code

### Architecture

```
User → pricing.html → Stripe Checkout → webhook_handler.py → license_manager.py → User gets license
                                                                    ↓
                                                          session_core.py checks license
                                                                    ↓
                                                          Feature flags enabled/disabled
```

### Stripe Checkout Handler (`lib/payment/stripe_checkout.py`)

```python
#!/usr/bin/env python3
"""
NeuralCline Payment — Stripe Checkout Integration
==================================================
This module provides serverless-compatible Stripe Checkout session creation
and management. It can run as:
  1. A standalone HTTP server (for development)
  2. A serverless function (Vercel, Netlify, AWS Lambda)
  3. A GitHub Actions workflow trigger

Setup:
  1. Create a Stripe account: https://stripe.com
  2. Get your API keys: Dashboard → Developers → API Keys
  3. Set environment variables:
     - STRIPE_SECRET_KEY: sk_live_... (production) or sk_test_... (test)
     - STRIPE_PUBLISHABLE_KEY: pk_live_... or pk_test_...
     - STRIPE_WEBHOOK_SECRET: whsec_... (from Stripe Dashboard → Webhooks)
     - DOMAIN: your domain (e.g., https://edgecase-1.github.io)
  4. Create products in Stripe Dashboard:
     - NeuralCline Pro ($29/month)
     - NeuralCline Enterprise ($299/month)
     - NeuralCline Lifetime ($999 one-time)

Usage:
  python3 lib/payment/stripe_checkout.py create-session --tier pro
  python3 lib/payment/stripe_checkout.py create-session --tier enterprise
  python3 lib/payment/stripe_checkout.py create-session --tier lifetime
  python3 lib/payment/stripe_checkout.py verify-session --session-id cs_test_...
  python3 lib/payment/stripe_checkout.py list-products
"""

import os
import json
import sys
import hmac
import hashlib
import time
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─── Configuration ──────────────────────────────────────────────────────────
# These should be set as environment variables in production
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
DOMAIN = os.environ.get('DOMAIN', 'https://edgecase-1.github.io/NeuralCline')
LICENSE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'session-state', 'licenses')

os.makedirs(LICENSE_DIR, exist_ok=True)

# ─── Pricing Tiers ──────────────────────────────────────────────────────────
TIERS = {
    'pro': {
        'name': 'NeuralCline Pro',
        'description': 'Session safety for individual developers',
        'price_id': os.environ.get('STRIPE_PRICE_PRO', 'price_pro'),  # Replace with actual Stripe Price ID
        'amount': 2900,  # $29.00 in cents
        'currency': 'usd',
        'interval': 'month',
        'features': [
            'Session crash recovery',
            'Timing metrics & EEF',
            'Anomaly detection',
            'Context window monitoring',
            'All adapters (Cline, Copilot, Cursor, Codeium)',
            'Community support'
        ]
    },
    'enterprise': {
        'name': 'NeuralCline Enterprise',
        'description': 'Session safety for teams and organizations',
        'price_id': os.environ.get('STRIPE_PRICE_ENTERPRISE', 'price_enterprise'),
        'amount': 29900,  # $299.00 in cents
        'currency': 'usd',
        'interval': 'month',
        'features': [
            'Everything in Pro',
            'Team management dashboard',
            'SSO/SAML integration',
            'Audit logging',
            'Custom adapter development',
            'Priority support',
            'SLA guarantee',
            'On-premise deployment option'
        ]
    },
    'lifetime': {
        'name': 'NeuralCline Lifetime',
        'description': 'One-time payment, lifetime access',
        'price_id': os.environ.get('STRIPE_PRICE_LIFETIME', 'price_lifetime'),
        'amount': 99900,  # $999.00 in cents
        'currency': 'usd',
        'interval': 'one-time',
        'features': [
            'Everything in Pro',
            'Lifetime updates',
            'Early access to new features',
            'Direct line to developers',
            'Name in credits'
        ]
    }
}


def stripe_request(method, path, data=None):
    """Make a request to the Stripe API."""
    import urllib.request
    import urllib.error
    
    if not STRIPE_SECRET_KEY:
        return {'error': 'STRIPE_SECRET_KEY not set', 'mode': 'demo'}
    
    url = f'https://api.stripe.com/v1{path}'
    headers = {
        'Authorization': f'Bearer {STRIPE_SECRET_KEY}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    if data:
        import urllib.parse
        data = urllib.parse.urlencode(data).encode()
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {'error': f'Stripe API error: {e.code}', 'detail': e.read().decode()}
    except Exception as e:
        return {'error': str(e)}


def create_checkout_session(tier, customer_email=None, metadata=None):
    """
    Create a Stripe Checkout session for the given tier.
    
    Returns a dict with:
      - session_id: The Stripe Checkout session ID
      - url: The Checkout page URL (redirect user here)
      - mode: 'live' if Stripe is configured, 'demo' otherwise
    
    In demo mode, returns a simulated session for testing.
    """
    if tier not in TIERS:
        return {'error': f'Unknown tier: {tier}. Valid tiers: {", ".join(TIERS.keys())}'}
    
    tier_config = TIERS[tier]
    
    if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.startswith('sk_test_'):
        # Demo mode — return simulated session
        session_id = f'demo_{uuid.uuid4().hex[:16]}'
        return {
            'session_id': session_id,
            'url': f'{DOMAIN}/checkout.html?session_id={session_id}&tier={tier}&mode=demo',
            'mode': 'demo',
            'tier': tier,
            'amount': tier_config['amount'],
            'currency': tier_config['currency'],
            'interval': tier_config['interval'],
            'message': 'DEMO MODE: Set STRIPE_SECRET_KEY to enable live payments'
        }
    
    # Live mode — create actual Stripe Checkout session
    session_data = {
        'success_url': f'{DOMAIN}/success.html?session_id={{CHECKOUT_SESSION_ID}}',
        'cancel_url': f'{DOMAIN}/cancel.html',
        'mode': 'subscription' if tier_config['interval'] == 'month' else 'payment',
        'line_items[0][price]': tier_config['price_id'],
        'line_items[0][quantity]': 1,
    }
    
    if customer_email:
        session_data['customer_email'] = customer_email
    
    if metadata:
        for key, value in metadata.items():
            session_data[f'metadata[{key}]'] = str(value)
    
    result = stripe_request('POST', '/checkout/sessions', session_data)
    
    if 'error' in result:
        return result
    
    return {
        'session_id': result.get('id'),
        'url': result.get('url'),
        'mode': 'live',
        'tier': tier,
        'amount': tier_config['amount'],
        'currency': tier_config['currency'],
    }


def verify_checkout_session(session_id):
    """
    Verify a Checkout session and return its status.
    
    Returns:
      - status: 'complete', 'expired', 'open', or 'error'
      - customer_details: dict with email, name, etc.
      - payment_status: 'paid', 'unpaid', 'no_payment_required'
      - tier: the purchased tier
    """
    if session_id.startswith('demo_'):
        # Demo mode — simulate verification
        return {
            'status': 'complete',
            'customer_details': {'email': 'demo@example.com'},
            'payment_status': 'paid',
            'tier': 'pro',
            'mode': 'demo',
            'message': 'DEMO MODE: Set STRIPE_SECRET_KEY for live verification'
        }
    
    result = stripe_request('GET', f'/checkout/sessions/{session_id}')
    
    if 'error' in result:
        return result
    
    # Determine tier from metadata or line items
    tier = 'pro'  # default
    metadata = result.get('metadata', {})
    if 'tier' in metadata:
        tier = metadata['tier']
    
    return {
        'status': result.get('status'),
        'customer_details': result.get('customer_details', {}),
        'payment_status': result.get('payment_status'),
        'tier': tier,
        'mode': 'live',
        'amount': result.get('amount_total', 0),
        'currency': result.get('currency', 'usd'),
    }


def handle_webhook(payload, signature):
    """
    Handle a Stripe webhook event.
    
    Events handled:
      - checkout.session.completed: Grant license
      - customer.subscription.updated: Update license
      - customer.subscription.deleted: Revoke license
      - invoice.paid: Renew license
      - invoice.payment_failed: Flag for attention
    
    Returns dict with action taken.
    """
    if not STRIPE_WEBHOOK_SECRET:
        return {'error': 'STRIPE_WEBHOOK_SECRET not set', 'mode': 'demo'}
    
    # Verify webhook signature
    try:
        from stripe import Webhook
        event = Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except ImportError:
        # Manual verification if stripe library not available
        expected_sig = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        # Note: Actual Stripe signatures use a different format
        # This is a simplified version; use the stripe library in production
        event = json.loads(payload)
    except Exception as e:
        return {'error': f'Webhook verification failed: {e}'}
    
    event_type = event.get('type', '')
    event_data = event.get('data', {}).get('object', {})
    
    if event_type == 'checkout.session.completed':
        session_id = event_data.get('id', '')
        customer_email = event_data.get('customer_details', {}).get('email', '')
        tier = event_data.get('metadata', {}).get('tier', 'pro')
        
        # Generate and store license
        license_key = generate_license(customer_email, tier)
        
        return {
            'action': 'license_granted',
            'session_id': session_id,
            'customer_email': customer_email,
            'tier': tier,
            'license_key': license_key
        }
    
    elif event_type == 'customer.subscription.deleted':
        customer_email = event_data.get('customer', {}).get('email', '')
        revoke_license(customer_email)
        return {
            'action': 'license_revoked',
            'customer_email': customer_email
        }
    
    elif event_type == 'invoice.paid':
        customer_email = event_data.get('customer_email', '')
        renew_license(customer_email)
        return {
            'action': 'license_renewed',
            'customer_email': customer_email
        }
    
    return {
        'action': 'ignored',
        'event_type': event_type
    }


def generate_license(email, tier):
    """
    Generate a license key for the given email and tier.
    
    License format: NC-XXXXXXXX-XXXXXXXX-XXXXXXXX
    Where X is a hex character derived from:
      - email hash
      - tier
      - timestamp
      - random salt
    
    License is stored in LICENSE_DIR/{email}.json
    """
    timestamp = int(time.time())
    salt = uuid.uuid4().hex[:8]
    
    # Create license key
    raw = f"{email}:{tier}:{timestamp}:{salt}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest().upper()
    
    # Format: NC-XXXXXXXX-XXXXXXXX-XXXXXXXX
    license_key = f"NC-{key_hash[:8]}-{key_hash[8:16]}-{key_hash[16:24]}"
    
    # Store license
    license_data = {
        'license_key': license_key,
        'email': email,
        'tier': tier,
        'granted_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': None,  # Set based on tier
        'active': True,
        'features': TIERS[tier]['features'],
        'validation_count': 0,
        'last_validated': None
    }
    
    license_path = os.path.join(LICENSE_DIR, f"{hashlib.md5(email.encode()).hexdigest()}.json")
    with open(license_path, 'w') as f:
        json.dump(license_data, f, indent=2)
    
    return license_key


def validate_license(license_key):
    """
    Validate a license key.
    
    Returns dict with:
      - valid: True/False
      - tier: the tier (if valid)
      - features: list of enabled features
      - message: human-readable status
    """
    # Search all license files
    if not os.path.exists(LICENSE_DIR):
        return {'valid': False, 'message': 'No licenses directory'}
    
    for filename in os.listdir(LICENSE_DIR):
        if not filename.endswith('.json'):
            continue
        
        license_path = os.path.join(LICENSE_DIR, filename)
        with open(license_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        
        if data.get('license_key') == license_key:
            if not data.get('active', False):
                return {'valid': False, 'message': 'License revoked'}
            
            # Update validation count
            data['validation_count'] = data.get('validation_count', 0) + 1
            data['last_validated'] = datetime.now(timezone.utc).isoformat()
            with open(license_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {
                'valid': True,
                'tier': data.get('tier', 'pro'),
                'features': data.get('features', []),
                'email': data.get('email', ''),
                'message': f"Valid {data.get('tier', 'pro')} license"
            }
    
    return {'valid': False, 'message': 'License key not found'}


def revoke_license(email):
    """Revoke all licenses for the given email."""
    email_hash = hashlib.md5(email.encode()).hexdigest()
    license_path = os.path.join(LICENSE_DIR, f"{email_hash}.json")
    
    if os.path.exists(license_path):
        with open(license_path) as f:
            data = json.load(f)
        data['active'] = False
        data['revoked_at'] = datetime.now(timezone.utc).isoformat()
        with open(license_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    return False


def renew_license(email):
    """Renew (re-activate) license for the given email."""
    email_hash = hashlib.md5(email.encode()).hexdigest()
    license_path = os.path.join(LICENSE_DIR, f"{email_hash}.json")
    
    if os.path.exists(license_path):
        with open(license_path) as f:
            data = json.load(f)
        data['active'] = True
        data['renewed_at'] = datetime.now(timezone.utc).isoformat()
        with open(license_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    return False


def list_products():
    """List all available products/tiers."""
    return {
        'products': [
            {
                'id': tier_id,
                **config
            }
            for tier_id, config in TIERS.items()
        ],
        'publishable_key': STRIPE_PUBLISHABLE_KEY or 'pk_demo',
        'mode': 'live' if STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('sk_test_') else 'test' if STRIPE_SECRET_KEY else 'demo'
    }


# ─── HTTP Server (for development / self-hosted) ────────────────────────────

class PaymentHandler(BaseHTTPRequestHandler):
    """Simple HTTP server for payment endpoints."""
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        if path == '/api/products':
            self._json_response(list_products())
        
        elif path == '/api/verify-session':
            session_id = params.get('session_id', [None])[0]
            if not session_id:
                self._json_response({'error': 'Missing session_id'}, 400)
                return
            self._json_response(verify_checkout_session(session_id))
        
        elif path == '/api/validate-license':
            license_key = params.get('license_key', [None])[0]
            if not license_key:
                self._json_response({'error': 'Missing license_key'}, 400)
                return
            self._json_response(validate_license(license_key))
        
        else:
            self._json_response({'error': 'Not found'}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        if path == '/api/create-session':
            data = json.loads(body) if body else {}
            tier = data.get('tier', 'pro')
            email = data.get('email')
            result = create_checkout_session(tier, customer_email=email)
            self._json_response(result)
        
        elif path == '/api/webhook':
            signature = self.headers.get('Stripe-Signature', '')
            result = handle_webhook(body, signature)
            self._json_response(result)
        
        else:
            self._json_response({'error': 'Not found'}, 404)
    
    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        sys.stderr.write(f"[Payment Server] {format % args}\n")


def run_server(port=8080):
    """Run the payment HTTP server."""
    server = HTTPServer(('0.0.0.0', port), PaymentHandler)
    print(f"NeuralCline Payment Server running on http://0.0.0.0:{port}")
    print(f"Demo mode: {'YES' if not STRIPE_SECRET_KEY else 'NO'}")
    print(f"Endpoints:")
    print(f"  GET  /api/products          — List products")
    print(f"  GET  /api/verify-session     — Verify checkout session")
    print(f"  GET  /api/validate-license   — Validate license key")
    print(f"  POST /api/create-session     — Create checkout session")
    print(f"  POST /api/webhook            — Stripe webhook receiver")
    print()
    print("To use live mode, set:")
    print("  export STRIPE_SECRET_KEY=sk_live_...")
    print("  export STRIPE_PUBLISHABLE_KEY=pk_live_...")
    print("  export STRIPE_WEBHOOK_SECRET=whsec_...")
    print("  export DOMAIN=https://yourdomain.com")
    server.serve_forever()


# ─── CLI Interface ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("NeuralCline Payment System")
        print()
        print("Usage:")
        print("  python3 lib/payment/stripe_checkout.py create-session --tier <tier> [--email <email>]")
        print("  python3 lib/payment/stripe_checkout.py verify-session --session-id <id>")
        print("  python3 lib/payment/stripe_checkout.py validate-license --key <key>")
        print("  python3 lib/payment/stripe_checkout.py list-products")
        print("  python3 lib/payment/stripe_checkout.py server [--port <port>]")
        print()
        print("Tiers: pro, enterprise, lifetime")
        return
    
    command = sys.argv[1]
    
    if command == 'create-session':
        tier = 'pro'
        email = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--tier' and i + 2 < len(sys.argv):
                tier = sys.argv[i + 3]
            elif arg == '--email' and i + 2 < len(sys.argv):
                email = sys.argv[i + 3]
        result = create_checkout_session(tier, customer_email=email)
        print(json.dumps(result, indent=2))
    
    elif command == 'verify-session':
        session_id = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--session-id' and i + 2 < len(sys.argv):
                session_id = sys.argv[i + 3]
        if not session_id:
            print("Error: --session-id is required")
            return
        result = verify_checkout_session(session_id)
        print(json.dumps(result, indent=2))
    
    elif command == 'validate-license':
        license_key = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--key' and i + 2 < len(sys.argv):
                license_key = sys.argv[i + 3]
        if not license_key:
            print("Error: --key is required")
            return
        result = validate_license(license_key)
        print(json.dumps(result, indent=2))
    
    elif command == 'list-products':
        result = list_products()
        print(json.dumps(result, indent=2))
    
    elif command == 'server':
        port = 8080
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--port' and i + 2 < len(sys.argv):
                port = int(sys.argv[i + 3])
        run_server(port)
    
    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
```

### Pricing Tiers (`lib/payment/pricing_tiers.py`)

```python
#!/usr/bin/env python3
"""
NeuralCline Pricing Tiers — Feature Flag Definitions
=====================================================
Defines the feature matrix for each pricing tier.
Used by session_core.py to enable/disable features based on license.
"""

TIERS = {
    'free': {
        'name': 'NeuralCline Free',
        'price': 0,
        'price_display': 'Free',
        'interval': None,
        'description': 'Basic session safety for evaluation',
        'features': [
            'Session crash recovery (limited to 10 recoveries/day)',
            'Basic timing metrics',
            'Single adapter (Cline only)',
            'Community support (GitHub Issues)',
        ],
        'limits': {
            'max_recoveries_per_day': 10,
            'max_adapters': 1,
            'max_sessions_per_day': 50,
            'metrics_retention_days': 1,
            'anomaly_detection': False,
            'context_window_monitoring': False,
            'team_management': False,
            'audit_logging': False,
            'custom_adapters': False,
            'priority_support': False,
            'sla': False,
            'on_premise': False,
        }
    },
    'pro': {
        'name': 'NeuralCline Pro',
        'price': 2900,
        'price_display': '$29/month',
        'interval': 'month',
        'description': 'Session safety for individual developers',
        'features': [
            'Unlimited session crash recovery',
            'Full timing metrics & EEF',
            'Anomaly detection',
            'Context window monitoring',
            'All adapters (Cline, Copilot, Cursor, Codeium)',
            '7-day metrics retention',
            'Community support',
        ],
        'limits': {
            'max_recoveries_per_day': None,  # Unlimited
            'max_adapters': None,
            'max_sessions_per_day': None,
            'metrics_retention_days': 7,
            'anomaly_detection': True,
            'context_window_monitoring': True,
            'team_management': False,
            'audit_logging': False,
            'custom_adapters': False,
            'priority_support': False,
            'sla': False,
            'on_premise': False,
        }
    },
    'enterprise': {
        'name': 'NeuralCline Enterprise',
        'price': 29900,
        'price_display': '$299/month',
        'interval': 'month',
        'description': 'Session safety for teams and organizations',
        'features': [
            'Everything in Pro',
            'Team management dashboard',
            'SSO/SAML integration',
            'Audit logging',
            'Custom adapter development',
            'Priority support',
            'SLA guarantee',
            'On-premise deployment option',
            '30-day metrics retention',
        ],
        'limits': {
            'max_recoveries_per_day': None,
            'max_adapters': None,
            'max_sessions_per_day': None,
            'metrics_retention_days': 30,
            'anomaly_detection': True,
            'context_window_monitoring': True,
            'team_management': True,
            'audit_logging': True,
            'custom_adapters': True,
            'priority_support': True,
            'sla': True,
            'on_premise': True,
        }
    },
    'lifetime': {
        'name': 'NeuralCline Lifetime',
        'price': 99900,
        'price_display': '$999 one-time',
        'interval': 'one-time',
        'description': 'One-time payment, lifetime access',
        'features': [
            'Everything in Pro, forever',
            'Lifetime updates',
            'Early access to new features',
            'Direct line to developers',
            'Name in project credits',
        ],
        'limits': {
            'max_recoveries_per_day': None,
            'max_adapters': None,
            'max_sessions_per_day': None,
            'metrics_retention_days': 365,
            'anomaly_detection': True,
            'context_window_monitoring': True,
            'team_management': False,
            'audit_logging': False,
            'custom_adapters': False,
            'priority_support': True,
            'sla': False,
            'on_premise': False,
        }
    }
}


def get_tier(tier_id):
    """Get tier configuration by ID."""
    return TIERS.get(tier_id)


def get_feature(tier_id, feature_name):
    """Check if a feature is enabled for a given tier."""
    tier = TIERS.get(tier_id)
    if not tier:
        return False
    limits = tier.get('limits', {})
    return limits.get(feature_name, False)


def get_limit(tier_id, limit_name):
    """Get a specific limit value for a tier."""
    tier = TIERS.get(tier_id)
    if not tier:
        return 0
    limits = tier.get('limits', {})
    return limits.get(limit_name, 0)


def get_tiers_for_license(license_tier):
    """Get all tiers accessible from a given license tier."""
    tier_order = ['free', 'pro', 'enterprise', 'lifetime']
    if license_tier not in tier_order:
        return ['free']
    
    idx = tier_order.index(license_tier)
    return tier_order[:idx + 1]
```

---

## 🧠 AGENTIC AI OPTIMIZATION

### Context Window Pressure Monitoring (`lib/context_manager.py`)

```python
#!/usr/bin/env python3
"""
NeuralCline Context Manager — Agentic AI Context Window Optimization
=====================================================================
Monitors context window pressure and provides strategies for:
  1. Early warning when context is approaching limits
  2. Automatic checkpoint generation at critical thresholds
  3. Session state compression for efficient storage
  4. Adaptive recovery strategies based on available context

This is the core differentiator for agentic AI interfaces where
context windows (1M+ tokens) and session crashes are the highest
failure modes.
"""

import json
import os
import time
from datetime import datetime, timezone
from collections import deque

# Context window thresholds (as percentage of max)
THRESHOLDS = {
    'info': 0.40,      # 40% — start monitoring
    'warning': 0.60,   # 60% — suggest checkpoint
    'critical': 0.75,  # 75% — force checkpoint, suggest handoff
    'danger': 0.85,    # 85% — force handoff, refuse new operations
    'emergency': 0.95, # 95% — emergency compression, flush state
}

# Default context window sizes for different models
MODEL_CONTEXT_SIZES = {
    'claude-3-opus': 200000,
    'claude-3-sonnet': 200000,
    'claude-3-haiku': 200000,
    'claude-4': 200000,
    'gpt-4': 128000,
    'gpt-4-turbo': 128000,
    'gpt-4o': 128000,
    'gemini-pro': 1000000,
    'gemini-ultra': 1000000,
    'deepseek-v4': 1000000,
    'deepseek-v3': 64000,
    'codestral': 256000,
    'default': 100000,
}


class ContextManager:
    """
    Manages context window pressure for agentic AI sessions.
    
    Features:
    - Real-time context usage tracking
    - Model-specific context window sizes
    - Adaptive checkpoint generation
    - Session state compression
    - Recovery strategy selection based on available context
    """
    
    def __init__(self, session_dir=None, model='default'):
        self.session_dir = session_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'session-state'
        )
        self.model = model
        self.max_context = MODEL_CONTEXT_SIZES.get(model, MODEL_CONTEXT_SIZES['default'])
        self.state_file = os.path.join(self.session_dir, 'current-state.json')
        self.checkpoint_file = os.path.join(self.session_dir, 'checkpoint.json')
        self.metrics_file = os.path.join(self.session_dir, 'context-metrics.json')
        
        os.makedirs(self.session_dir, exist_ok=True)
    
    def get_context_usage(self):
        """
        Estimate current context usage based on session state.
        
        Returns dict with:
          - current_tokens: estimated tokens used
          - max_tokens: model's context window size
          - usage_pct: percentage of context used
          - threshold: current threshold level
          - remaining_tokens: tokens remaining
          - estimated_calls_remaining: estimated tool calls before critical
        """
        state = self._read_state()
        
        # Estimate tokens from tool calls and command history
        tool_calls = state.get('tool_call_count', 0)
        last_command = state.get('last_command', '')
        
        # Rough estimation: each tool call ~2000 tokens of context
        # Each command ~10 tokens per character
        estimated_tokens = tool_calls * 2000 + len(last_command) * 10
        
        # Add overhead for system prompts, file contents, etc.
        overhead = state.get('context_overhead', 0)
        estimated_tokens += overhead
        
        usage_pct = min(100, int(estimated_tokens * 100 / max(self.max_context, 1)))
        
        # Determine threshold level
        threshold = 'safe'
        for level, pct in sorted(THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if usage_pct >= pct * 100:
                threshold = level
                break
        
        remaining = self.max_context - estimated_tokens
        calls_remaining = max(0, remaining // 2000)
        
        return {
            'current_tokens': estimated_tokens,
            'max_tokens': self.max_context,
            'usage_pct': usage_pct,
            'threshold': threshold,
            'remaining_tokens': remaining,
            'estimated_calls_remaining': calls_remaining,
            'model': self.model,
        }
    
    def should_checkpoint(self):
        """
        Determine if a checkpoint should be generated based on context pressure.
        
        Returns:
          - should_checkpoint: bool
          - reason: string explanation
          - urgency: 'low', 'medium', 'high', 'critical'
        """
        usage = self.get_context_usage()
        threshold = usage['threshold']
        
        if threshold in ('danger', 'emergency'):
            return {
                'should_checkpoint': True,
                'reason': f"Context at {usage['usage_pct']}% ({threshold})",
                'urgency': 'critical',
                'action': 'FORCE_CHECKPOINT_AND_HANDOFF'
            }
        elif threshold == 'critical':
            return {
                'should_checkpoint': True,
                'reason': f"Context at {usage['usage_pct']}% (critical)",
                'urgency': 'high',
                'action': 'FORCE_CHECKPOINT'
            }
        elif threshold == 'warning':
            return {
                'should_checkpoint': True,
                'reason': f"Context at {usage['usage_pct']}% (warning)",
                'urgency': 'medium',
                'action': 'SUGGEST_CHECKPOINT'
            }
        elif threshold == 'info':
            return {
                'should_checkpoint': False,
                'reason': f"Context at {usage['usage_pct']}% — monitoring",
                'urgency': 'low',
                'action': 'MONITOR'
            }
        else:
            return {
                'should_checkpoint': False,
                'reason': f"Context at {usage['usage_pct']}% — safe",
                'urgency': 'low',
                'action': 'NONE'
            }
    
    def compress_state(self):
        """
        Compress session state to reduce context footprint.
        
        Strategies:
        1. Truncate command history to last 50 entries
        2. Summarize failure patterns (keep top 5)
        3. Remove redundant crash log entries
        4. Compress timing history (keep rolling averages, drop raw)
        
        Returns dict with compression stats.
        """
        state = self._read_state()
        before_size = len(json.dumps(state))
        
        # Strategy 1: Truncate command history
        if 'command_history' in state and len(state['command_history']) > 50:
            state['command_history'] = state['command_history'][-50:]
            state['_compressed'] = True
            state['_compressed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Strategy 2: Summarize failure patterns
        if 'failure_patterns' in state and len(state.get('failure_patterns', [])) > 5:
            state['failure_patterns'] = state['failure_patterns'][:5]
        
        # Strategy 3: Compress timing history
        if 'timing_metrics' in state:
            timing = state['timing_metrics']
            # Keep only essential metrics
            state['timing_metrics'] = {
                'eef': timing.get('execution_emulation_factor', 1.0),
                'timeout_proximity': timing.get('timeout_proximity', 0),
                'rolling_avg_ms': timing.get('rolling_avg_ms', 0),
                'total_commands_tracked': timing.get('total_commands_tracked', 0),
                'recent_failures': timing.get('recent_failures', 0),
            }
        
        after_size = len(json.dumps(state))
        savings = before_size - after_size
        savings_pct = int(savings * 100 / max(before_size, 1))
        
        self._write_state(state)
        
        return {
            'before_bytes': before_size,
            'after_bytes': after_size,
            'savings_bytes': savings,
            'savings_pct': savings_pct,
        }
    
    def select_recovery_strategy(self, crash_context):
        """
        Select the best recovery strategy based on available context.
        
        Strategies:
        1. Full recovery — restore complete checkpoint (needs 20%+ context free)
        2. Partial recovery — restore essential state only (needs 10%+ context free)
        3. Minimal recovery — restore only session ID and goals (needs 5%+ context free)
        4. Fresh start — no context available, start new session
        
        Returns dict with selected strategy.
        """
        usage = self.get_context_usage()
        free_pct = 100 - usage['usage_pct']
        
        if free_pct >= 20:
            return {
                'strategy': 'full',
                'description': 'Full checkpoint restoration',
                'context_needed': '20%',
                'context_available': f"{free_pct}%",
                'action': 'Restore complete checkpoint from checkpoint.json'
            }
        elif free_pct >= 10:
            return {
                'strategy': 'partial',
                'description': 'Partial state restoration (essential only)',
                'context_needed': '10%',
                'context_available': f"{free_pct}%",
                'action': 'Restore session ID, goals, and last command only'
            }
        elif free_pct >= 5:
            return {
                'strategy': 'minimal',
                'description': 'Minimal recovery (session identity only)',
                'context_needed': '5%',
                'context_available': f"{free_pct}%",
                'action': 'Restore session ID and active goals only'
            }
        else:
            return {
                'strategy': 'fresh',
                'description': 'Fresh session start (context exhausted)',
                'context_needed': 'N/A',
                'context_available': f"{free_pct}%",
                'action': 'Generate handoff document, start new session'
            }
    
    def _read_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file) as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}
    
    def _write_state(self, data):
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def log_context_metrics(self):
        """Log context metrics for historical analysis."""
        usage = self.get_context_usage()
        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **usage
        }
        
        # Append to context metrics file
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file) as f:
                    history = json.load(f)
            else:
                history = {'entries': []}
            
            history['entries'].append(metrics)
            
            # Keep last 1000 entries
            if len(history['entries']) > 1000:
                history['entries'] = history['entries'][-1000:]
            
            with open(self.metrics_file, 'w') as f:
                json.dump(history, f, indent=2)
        except:
            pass
        
        return metrics
```

---

## 📊 10/10 VERIFICATION CRITERIA

Each item below must be verifiably true, not claimed.

### Technical Soundness (10/10)
- [ ] All statistical models use proper probability theory (log-normal, logistic regression)
- [ ] All ML models have measured accuracy, precision, recall, F1 scores
- [ ] All file operations use POSIX file locking
- [ ] All shell hooks use proper chaining (no fragile patching)
- [ ] All adapters pass integration tests
- [ ] Test coverage ≥ 90%
- [ ] Static analysis: zero critical, zero high issues
- [ ] Fuzzing: zero crashes after 1M iterations

### Novelty (10/10)
- [ ] Prior art analysis published in README
- [ ] Clear statement of what's new vs. what's standard
- [ ] Published benchmark comparing against alternatives
- [ ] Demonstrated improvement over baseline (no NeuralCline)

### Market Potential (10/10)
- [ ] Working adapters for 5+ AI coding tools
- [ ] Published adoption metrics (real, not projected)
- [ ] Published crash recovery statistics (real, not claimed)
- [ ] Published user testimonials (with permission)

### Financial Viability (10/10)
- [ ] Working Stripe integration with test mode
- [ ] Published pricing page
- [ ] License generation and validation working
- [ ] Webhook handling for subscription lifecycle
- [ ] Three-tier financial model with clear assumptions
- [ ] Break-even analysis published

### Code Quality (10/10)
- [ ] All Python files pass `pylint` with score ≥ 9.0
- [ ] All shell scripts pass `shellcheck` with zero warnings
- [ ] All functions have docstrings
- [ ] All modules have type hints
- [ ] CI/CD pipeline passing
- [ ] No dead code, no commented-out code

### Documentation (10/10)
- [ ] README accurately describes what the project does
- [ ] ARCHITECTURE.md explains all components
- [ ] ROADMAP.md has realistic timeline
- [ ] BENCHMARKS.md has published results
- [ ] COMPARISON.md honestly compares with alternatives
- [ ] ETHICS.md documents ethical guidelines
- [ ] All financial docs have clear assumptions

### Ethical Standing (10/10)
- [ ] No dark patterns in any code
- [ ] No ToS-violating automation
- [ ] All metrics are real, not fabricated
- [ ] All claims are verifiable
- [ ] Open source license (MIT for core)
- [ ] Transparent about limitations

### Model Agnostic (10/10)
- [ ] Working adapter for Cline
- [ ] Working adapter for GitHub Copilot
- [ ] Working adapter for Cursor
- [ ] Working adapter for Codeium
- [ ] Working generic adapter for any shell-based agent
- [ ] All adapters pass the same integration test suite

---

## 🚀 SESSION EXECUTION PROTOCOL

Every session follows this protocol:

### Session Start
1. Read this file (MASTER_PLAN.md)
2. Check the living checklist for current status
3. Pick the next incomplete item (top-to-bottom, phase-by-phase)
4. Announce which item you're working on

### During Session
1. Work on ONE checklist item at a time
2. Update the checklist when an item is complete
3. If blocked, note the blocker and move to next item
4. Keep context usage below 60% (use checkpoint if needed)

### Session End
1. Update all checklist items completed this session
2. Generate checkpoint: `bash hooks/generate-handoff.sh`
3. Update this file's status header
4. Note next steps for the following session

### Crash Recovery
If session crashes:
1. Run: `source /root/rehydration.md`
2. Read this file to find your place
3. Continue from the last incomplete item

---

## 🔗 QUICK LINKS

| Resource | Path |
|----------|------|
| Master Plan | `/root/NeuralCline/MASTER_PLAN.md` |
| Session Core | `/root/NeuralCline/lib/session_core.py` |
| Payment System | `/root/NeuralCline/lib/payment/stripe_checkout.py` |
| Pricing Tiers | `/root/NeuralCline/lib/payment/pricing_tiers.py` |
| Context Manager | `/root/NeuralCline/lib/context_manager.py` |
| State Engine | `/root/NeuralCline/lib/state_engine.py` |
| Timing Engine | `/root/NeuralCline/lib/timing_engine.py` |
| Anomaly Detector | `/root/NeuralCline/lib/anomaly_detector.py` |
| Metrics Collector | `/root/NeuralCline/lib/metrics_collector.py` |
| Shell Hooks | `/root/NeuralCline/hooks/shell-hooks.sh` |
| Pre-Tool Guard | `/root/NeuralCline/hooks/pre-tool-guard.sh` |
| Post-Tool State | `/root/NeuralCline/hooks/post-tool-state.sh` |
| Diagnostic | `/root/NeuralCline/hooks/diagnose.sh` |
| Pricing Page | `/root/NeuralCline/docs/pricing.html` |
| Checkout Page | `/root/NeuralCline/docs/checkout.html` |
| Portal Page | `/root/NeuralCline/docs/portal.html` |

---

## ✅ STATUS

**Current Phase:** 0 (Foundation)
**Current Item:** 0.1 — Create MASTER_PLAN.md (this file)
**Progress:** 1 / 131 items complete (0.8%)
**Last Updated:** 2026-07-10T05:30:00Z

---

*NeuralCline v2.0 — Session safety for agentic AI. Measured, not claimed.*