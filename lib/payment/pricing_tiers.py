#!/usr/bin/env python3
"""
NeuralCline Pricing Tiers — Feature Flag Definitions
=====================================================
Defines the feature matrix for each pricing tier.
Used by session_core.py to enable/disable features based on license.

Tiers:
  - free:       Basic session safety, limited recoveries, single adapter
  - pro:        Full session safety, all adapters, 7-day metrics
  - enterprise: Team management, SSO, audit logging, custom adapters
  - lifetime:   One-time payment, lifetime access, all pro features

Usage:
    from lib.payment.pricing_tiers import get_tier, get_feature, get_limit
    
    tier = get_tier('pro')
    if get_feature('pro', 'anomaly_detection'):
        print("Anomaly detection enabled")
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


def format_price(amount_cents):
    """Format a price in cents to a human-readable string."""
    if amount_cents == 0:
        return 'Free'
    dollars = amount_cents // 100
    cents = amount_cents % 100
    if cents == 0:
        return f'${dollars}'
    return f'${dollars}.{cents:02d}'