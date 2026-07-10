#!/usr/bin/env python3
"""
NeuralCline Webhook Handler — Stripe Event Processing
=======================================================
Processes Stripe webhook events for license lifecycle management.

Events handled:
  - checkout.session.completed: Grant license
  - customer.subscription.updated: Update license tier
  - customer.subscription.deleted: Revoke license
  - invoice.paid: Renew license
  - invoice.payment_failed: Flag for manual review

Usage:
    python3 lib/payment/webhook_handler.py --payload <json_file> --signature <sig>
    python3 lib/payment/webhook_handler.py server [--port 8080]
"""

import os
import sys
import json
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('neuralcline-webhook')

# Stripe configuration
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Import license manager
try:
    from lib.payment.license_manager import generate_license, revoke_license, renew_license, validate_license
except ImportError:
    # Fallback paths
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from lib.payment.license_manager import generate_license, revoke_license, renew_license, validate_license


def verify_signature(payload, signature):
    """
    Verify Stripe webhook signature.
    
    In production, use the stripe Python library:
        stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    
    This is a simplified HMAC verification for environments without the stripe library.
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature verification")
        return True
    
    if not signature:
        logger.error("No signature provided")
        return False
    
    try:
        # Parse signature header
        # Format: t=timestamp,v1=signature
        parts = {}
        for param in signature.split(','):
            if '=' in param:
                key, val = param.split('=', 1)
                parts[key] = val
        
        timestamp = parts.get('t')
        sig = parts.get('v1')
        
        if not timestamp or not sig:
            logger.error("Invalid signature format")
            return False
        
        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode() if isinstance(payload, bytes) else payload}"
        expected_sig = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        if hmac.compare_digest(expected_sig, sig):
            return True
        else:
            logger.error("Signature mismatch")
            return False
    
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def handle_event(event):
    """
    Process a Stripe webhook event.
    
    Args:
        event: Parsed Stripe event dict
    
    Returns:
        dict with action taken and details
    """
    event_type = event.get('type', '')
    event_data = event.get('data', {}).get('object', {})
    
    logger.info(f"Processing event: {event_type}")
    
    if event_type == 'checkout.session.completed':
        session_id = event_data.get('id', '')
        customer_details = event_data.get('customer_details', {})
        customer_email = customer_details.get('email', '')
        metadata = event_data.get('metadata', {})
        tier = metadata.get('tier', 'pro')
        
        if not customer_email:
            logger.warning(f"No email in checkout session {session_id}")
            return {'action': 'error', 'reason': 'No customer email'}
        
        # Generate license
        license_result = generate_license(customer_email, tier, {'session_id': session_id})
        
        logger.info(f"License granted: {customer_email} ({tier}) — {license_result.get('license_key', '')}")
        
        return {
            'action': 'license_granted',
            'session_id': session_id,
            'customer_email': customer_email,
            'tier': tier,
            'license_key': license_result.get('license_key', ''),
        }
    
    elif event_type == 'customer.subscription.updated':
        subscription_id = event_data.get('id', '')
        customer = event_data.get('customer', {})
        customer_email = customer.get('email', '') if isinstance(customer, dict) else ''
        status = event_data.get('status', '')
        
        if status == 'active':
            logger.info(f"Subscription activated: {customer_email}")
        elif status == 'past_due':
            logger.warning(f"Subscription past due: {customer_email}")
        
        return {
            'action': 'subscription_updated',
            'subscription_id': subscription_id,
            'customer_email': customer_email,
            'status': status,
        }
    
    elif event_type == 'customer.subscription.deleted':
        subscription_id = event_data.get('id', '')
        customer = event_data.get('customer', {})
        customer_email = customer.get('email', '') if isinstance(customer, dict) else ''
        
        if customer_email:
            revoke_result = revoke_license(customer_email)
            logger.info(f"License revoked: {customer_email} — {revoke_result.get('success', False)}")
        
        return {
            'action': 'subscription_deleted',
            'subscription_id': subscription_id,
            'customer_email': customer_email,
        }
    
    elif event_type == 'invoice.paid':
        invoice_id = event_data.get('id', '')
        customer_email = event_data.get('customer_email', '')
        amount = event_data.get('amount_paid', 0)
        
        if customer_email:
            renew_result = renew_license(customer_email)
            logger.info(f"License renewed: {customer_email} — ${amount/100:.2f}")
        
        return {
            'action': 'invoice_paid',
            'invoice_id': invoice_id,
            'customer_email': customer_email,
            'amount_paid': amount,
        }
    
    elif event_type == 'invoice.payment_failed':
        invoice_id = event_data.get('id', '')
        customer_email = event_data.get('customer_email', '')
        attempt_count = event_data.get('attempt_count', 1)
        
        logger.warning(f"Payment failed for {customer_email} (attempt {attempt_count})")
        
        return {
            'action': 'payment_failed',
            'invoice_id': invoice_id,
            'customer_email': customer_email,
            'attempt_count': attempt_count,
        }
    
    else:
        logger.info(f"Ignored event type: {event_type}")
        return {
            'action': 'ignored',
            'event_type': event_type,
        }


# ─── HTTP Server ────────────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP server for receiving Stripe webhooks."""
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Stripe-Signature')
        self.end_headers()
    
    def do_POST(self):
        if self.path != '/webhook':
            self._json_response({'error': 'Not found'}, 404)
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        signature = self.headers.get('Stripe-Signature', '')
        
        # Verify signature
        if not verify_signature(body, signature):
            self._json_response({'error': 'Invalid signature'}, 401)
            return
        
        # Parse event
        try:
            event = json.loads(body)
        except json.JSONDecodeError as e:
            self._json_response({'error': f'Invalid JSON: {e}'}, 400)
            return
        
        # Process event
        result = handle_event(event)
        
        self._json_response({'received': True, 'result': result})
    
    def do_GET(self):
        if self.path == '/health':
            self._json_response({
                'status': 'ok',
                'service': 'NeuralCline Webhook Handler',
                'webhook_secret_configured': bool(STRIPE_WEBHOOK_SECRET),
            })
        else:
            self._json_response({'error': 'Not found'}, 404)
    
    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def log_message(self, format, *args):
        logger.info(f"{format % args}")


def run_server(port=8080):
    """Run the webhook HTTP server."""
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f"NeuralCline Webhook Handler running on http://0.0.0.0:{port}")
    print(f"Webhook endpoint: POST /webhook")
    print(f"Health check: GET /health")
    print(f"Webhook secret configured: {bool(STRIPE_WEBHOOK_SECRET)}")
    print()
    print("Configure Stripe to send webhooks to: http://your-server:{port}/webhook")
    print("Set webhook secret in environment: STRIPE_WEBHOOK_SECRET=whsec_...")
    server.serve_forever()


# ─── CLI Interface ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("NeuralCline Webhook Handler v2.0.0")
        print()
        print("Usage:")
        print("  python3 lib/payment/webhook_handler.py process --payload <json_file>")
        print("  python3 lib/payment/webhook_handler.py server [--port <port>]")
        return
    
    command = sys.argv[1]
    
    if command == 'process':
        payload_file = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--payload' and i + 2 < len(sys.argv):
                payload_file = sys.argv[i + 3]
        
        if not payload_file:
            print("Error: --payload is required")
            return
        
        with open(payload_file) as f:
            event = json.load(f)
        
        result = handle_event(event)
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