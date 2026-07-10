"""
NeuralCline Payment System — Monetization Infrastructure
=========================================================
Provides Stripe integration for subscription management, license key
generation and validation, and feature flag enforcement.

Modules:
  - stripe_checkout.py: Stripe Checkout session creation and management
  - license_manager.py: License key generation, validation, and revocation
  - webhook_handler.py: Stripe webhook event processing
  - pricing_tiers.py: Tier definitions with feature flags

Usage:
    from lib.payment import create_checkout, validate_license, list_products
    
    # Create a checkout session
    session = create_checkout('pro', customer_email='user@example.com')
    print(f"Redirect user to: {session['url']}")
    
    # Validate a license key
    result = validate_license('NC-XXXXXXXX-XXXXXXXX-XXXXXXXX')
    if result['valid']:
        print(f"Tier: {result['tier']}")
"""

import os

# Re-export main functions
from lib.payment.stripe_checkout import (
    create_checkout_session,
    verify_checkout_session,
    handle_webhook,
    list_products,
    run_server,
)

from lib.payment.pricing_tiers import (
    TIERS,
    get_tier,
    get_feature,
    get_limit,
    get_tiers_for_license,
)

from lib.payment.license_manager import (
    generate_license,
    validate_license,
    revoke_license,
    renew_license,
)

# Convenience function
def create_checkout(tier, customer_email=None):
    """Create a checkout session (convenience wrapper)."""
    return create_checkout_session(tier, customer_email=customer_email)