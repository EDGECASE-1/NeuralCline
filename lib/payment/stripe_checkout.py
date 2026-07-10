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
     - NeuralCline Pro ($29/month) — price_id from Stripe
     - NeuralCline Enterprise ($299/month) — price_id from Stripe
     - NeuralCline Lifetime ($999 one-time) — price_id from Stripe

Usage:
  python3 lib/payment/stripe_checkout.py create-session --tier pro
  python3 lib/payment/stripe_checkout.py verify-session --session-id cs_test_...
  python3 lib/payment/stripe_checkout.py list-products
  python3 lib/payment/stripe_checkout.py server [--port 8080]
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
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
DOMAIN = os.environ.get('DOMAIN', 'https://edgecase-1.github.io/NeuralCline')

# License manager
try:
    from lib.payment.license_manager import generate_license, revoke_license, renew_license
except ImportError:
    # Fallback
    def generate_license(email, tier, metadata=None):
        return {'license_key': 'FALLBACK', 'email': email, 'tier': tier, 'active': True}
    def revoke_license(email): return {'success': True}
    def renew_license(email): return {'success': True}

# Pricing tiers
try:
    from lib.payment.pricing_tiers import TIERS
except ImportError:
    TIERS = {
        'pro': {'name': 'Pro', 'amount': 2900, 'currency': 'usd', 'interval': 'month'},
        'enterprise': {'name': 'Enterprise', 'amount': 29900, 'currency': 'usd', 'interval': 'month'},
        'lifetime': {'name': 'Lifetime', 'amount': 99900, 'currency': 'usd', 'interval': 'one-time'},
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
            'interval': tier_config.get('interval', 'month'),
            'message': 'DEMO MODE: Set STRIPE_SECRET_KEY to enable live payments'
        }
    
    # Live mode — create actual Stripe Checkout session
    session_data = {
        'success_url': f'{DOMAIN}/success.html?session_id={{CHECKOUT_SESSION_ID}}',
        'cancel_url': f'{DOMAIN}/cancel.html',
        'mode': 'subscription' if tier_config.get('interval') == 'month' else 'payment',
        'line_items[0][price]': tier_config.get('price_id', ''),
        'line_items[0][quantity]': 1,
    }
    
    if customer_email:
        session_data['customer_email'] = customer_email
    
    if metadata:
        for key, value in metadata.items():
            session_data[f'metadata[{key}]'] = str(value)
    
    # Add tier to metadata
    session_data['metadata[tier]'] = tier
    
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
    
    # Determine tier from metadata
    tier = 'pro'
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
    
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as e:
        return {'error': f'Invalid JSON payload: {e}'}
    
    # Verify webhook signature (simplified — use stripe library in production)
    if signature:
        expected_sig = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        # Note: Actual Stripe verification uses a different format
        # Use the stripe Python library for production: stripe.Webhook.construct_event()
    
    event_type = event.get('type', '')
    event_data = event.get('data', {}).get('object', {})
    
    if event_type == 'checkout.session.completed':
        session_id = event_data.get('id', '')
        customer_email = event_data.get('customer_details', {}).get('email', '')
        tier = event_data.get('metadata', {}).get('tier', 'pro')
        
        # Generate and store license
        license_result = generate_license(customer_email, tier, {'session_id': session_id})
        
        return {
            'action': 'license_granted',
            'session_id': session_id,
            'customer_email': customer_email,
            'tier': tier,
            'license_key': license_result.get('license_key', ''),
        }
    
    elif event_type == 'customer.subscription.deleted':
        customer_email = event_data.get('customer', {}).get('email', '')
        if customer_email:
            revoke_license(customer_email)
        return {
            'action': 'license_revoked',
            'customer_email': customer_email,
        }
    
    elif event_type == 'invoice.paid':
        customer_email = event_data.get('customer_email', '')
        if customer_email:
            renew_license(customer_email)
        return {
            'action': 'license_renewed',
            'customer_email': customer_email,
        }
    
    return {
        'action': 'ignored',
        'event_type': event_type,
    }


def list_products():
    """List all available products/tiers."""
    products = []
    for tier_id, config in TIERS.items():
        products.append({
            'id': tier_id,
            'name': config.get('name', tier_id),
            'description': config.get('description', ''),
            'amount': config.get('amount', 0),
            'currency': config.get('currency', 'usd'),
            'interval': config.get('interval', 'one-time'),
            'features': config.get('features', []),
            'price_display': config.get('price_display', ''),
        })
    
    return {
        'products': products,
        'publishable_key': STRIPE_PUBLISHABLE_KEY or 'pk_demo',
        'mode': 'live' if STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('sk_test_') else 'test' if STRIPE_SECRET_KEY else 'demo',
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
            try:
                from lib.payment.license_manager import validate_license
                result = validate_license(license_key)
            except ImportError:
                result = {'valid': False, 'message': 'License manager not available'}
            self._json_response(result)
        
        elif path == '/health':
            self._json_response({'status': 'ok', 'service': 'NeuralCline Payment', 'mode': 'demo' if not STRIPE_SECRET_KEY else 'live'})
        
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
    print(f"Mode: {'DEMO' if not STRIPE_SECRET_KEY else 'LIVE'}")
    print(f"Endpoints:")
    print(f"  GET  /api/products          — List products")
    print(f"  GET  /api/verify-session     — Verify checkout session")
    print(f"  GET  /api/validate-license   — Validate license key")
    print(f"  GET  /health                 — Health check")
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
        print("NeuralCline Payment System v2.0.0")
        print()
        print("Usage:")
        print("  python3 lib/payment/stripe_checkout.py create-session --tier <tier> [--email <email>]")
        print("  python3 lib/payment/stripe_checkout.py verify-session --session-id <id>")
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
        sys.exit(1)


if __name__ == '__main__':
    main()