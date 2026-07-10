#!/usr/bin/env python3
"""
NeuralCline License Manager — Key Generation, Validation & Revocation
======================================================================
Handles the full lifecycle of license keys:
  - Generate: Create a new license key for a customer
  - Validate: Check if a license key is valid and return tier info
  - Revoke: Deactivate a license key
  - Renew: Re-activate a revoked license
  - List: List all stored licenses

License Format: NC-XXXXXXXX-XXXXXXXX-XXXXXXXX
  - NC prefix identifies NeuralCline licenses
  - 24 hex characters derived from email + tier + timestamp + salt
  - Stored as JSON files in session-state/licenses/

Usage:
    python3 lib/payment/license_manager.py generate --email user@example.com --tier pro
    python3 lib/payment/license_manager.py validate --key NC-XXXXXXXX-XXXXXXXX-XXXXXXXX
    python3 lib/payment/license_manager.py revoke --email user@example.com
    python3 lib/payment/license_manager.py list
"""

import os
import sys
import json
import time
import uuid
import hashlib
import hmac
from datetime import datetime, timezone

# Paths
SESSION_DIR = os.environ.get(
    'NEURALCLINE_SESSION_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'session-state')
)
LICENSE_DIR = os.path.join(SESSION_DIR, 'licenses')

os.makedirs(LICENSE_DIR, exist_ok=True)

# Tier definitions (imported from pricing_tiers)
try:
    from lib.payment.pricing_tiers import TIERS, get_tier, get_feature, get_limit
except ImportError:
    # Fallback tier definitions
    TIERS = {
        'free': {'name': 'Free', 'features': [], 'limits': {}},
        'pro': {'name': 'Pro', 'features': [], 'limits': {}},
        'enterprise': {'name': 'Enterprise', 'features': [], 'limits': {}},
        'lifetime': {'name': 'Lifetime', 'features': [], 'limits': {}},
    }
    def get_tier(t): return TIERS.get(t, TIERS['free'])
    def get_feature(t, f): return False
    def get_limit(t, l): return 0


def generate_license(email, tier, metadata=None):
    """
    Generate a new license key for the given email and tier.
    
    License Format: NC-XXXXXXXX-XXXXXXXX-XXXXXXXX
    Where X is a hex character from SHA-256 hash of:
      - email
      - tier
      - timestamp (seconds since epoch)
      - random salt (8 hex chars)
    
    The license is stored as a JSON file in LICENSE_DIR/.
    
    Args:
        email: Customer email address
        tier: License tier (pro, enterprise, lifetime)
        metadata: Optional dict of additional metadata
    
    Returns:
        dict with license_key, email, tier, and expiration info
    """
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}. Valid tiers: {', '.join(TIERS.keys())}")
    
    now = datetime.now(timezone.utc)
    timestamp = int(time.time())
    salt = uuid.uuid4().hex[:8]
    
    # Create license key from hash
    raw = f"{email}:{tier}:{timestamp}:{salt}:{uuid.uuid4().hex}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest().upper()
    
    # Format: NC-XXXXXXXX-XXXXXXXX-XXXXXXXX
    license_key = f"NC-{key_hash[:8]}-{key_hash[8:16]}-{key_hash[16:24]}"
    
    # Calculate expiration
    tier_config = get_tier(tier)
    expires_at = None
    if tier_config and tier_config.get('interval') == 'month':
        # Expires in 30 days
        from datetime import timedelta
        expires_at = (now + timedelta(days=30)).isoformat()
    elif tier == 'lifetime':
        # Lifetime licenses don't expire
        expires_at = None
    
    # Build license data
    license_data = {
        'license_key': license_key,
        'email': email,
        'tier': tier,
        'granted_at': now.isoformat(),
        'expires_at': expires_at,
        'active': True,
        'features': tier_config.get('features', []) if tier_config else [],
        'validation_count': 0,
        'last_validated': None,
        'metadata': metadata or {},
        'version': '2.0.0'
    }
    
    # Store license file
    email_hash = hashlib.md5(email.encode()).hexdigest()
    license_path = os.path.join(LICENSE_DIR, f"{email_hash}.json")
    
    with open(license_path, 'w') as f:
        json.dump(license_data, f, indent=2)
    
    return {
        'license_key': license_key,
        'email': email,
        'tier': tier,
        'expires_at': expires_at,
        'active': True
    }


def validate_license(license_key):
    """
    Validate a license key and return its tier and features.
    
    Checks:
    1. License key exists in storage
    2. License is active (not revoked)
    3. License hasn't expired (if applicable)
    4. Updates validation count and last_validated timestamp
    
    Args:
        license_key: The license key to validate (format: NC-...)
    
    Returns:
        dict with valid, tier, features, email, and message
    """
    if not os.path.exists(LICENSE_DIR):
        return {'valid': False, 'message': 'No licenses directory found'}
    
    # Search all license files
    for filename in os.listdir(LICENSE_DIR):
        if not filename.endswith('.json'):
            continue
        
        license_path = os.path.join(LICENSE_DIR, filename)
        try:
            with open(license_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue
        
        if data.get('license_key') == license_key:
            # Check if active
            if not data.get('active', False):
                return {
                    'valid': False,
                    'message': 'License has been revoked',
                    'revoked_at': data.get('revoked_at', 'unknown')
                }
            
            # Check expiration
            expires_at = data.get('expires_at')
            if expires_at:
                try:
                    expires = datetime.fromisoformat(expires_at)
                    if datetime.now(timezone.utc) > expires.replace(tzinfo=timezone.utc):
                        return {
                            'valid': False,
                            'message': 'License has expired',
                            'expired_at': expires_at
                        }
                except Exception:
                    pass
            
            # Update validation count
            data['validation_count'] = data.get('validation_count', 0) + 1
            data['last_validated'] = datetime.now(timezone.utc).isoformat()
            
            with open(license_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {
                'valid': True,
                'tier': data.get('tier', 'free'),
                'features': data.get('features', []),
                'email': data.get('email', ''),
                'expires_at': data.get('expires_at'),
                'message': f"Valid {data.get('tier', 'free')} license"
            }
    
    return {'valid': False, 'message': 'License key not found'}


def revoke_license(email):
    """
    Revoke all licenses for the given email.
    
    Args:
        email: Customer email address
    
    Returns:
        dict with success status and count of revoked licenses
    """
    email_hash = hashlib.md5(email.encode()).hexdigest()
    license_path = os.path.join(LICENSE_DIR, f"{email_hash}.json")
    
    if not os.path.exists(license_path):
        return {'success': False, 'message': 'No license found for this email'}
    
    try:
        with open(license_path) as f:
            data = json.load(f)
        
        data['active'] = False
        data['revoked_at'] = datetime.now(timezone.utc).isoformat()
        
        with open(license_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'email': email,
            'tier': data.get('tier', 'unknown'),
            'license_key': data.get('license_key', 'unknown'),
            'revoked_at': data['revoked_at']
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}


def renew_license(email):
    """
    Renew (re-activate) a license for the given email.
    
    Args:
        email: Customer email address
    
    Returns:
        dict with success status and renewed license info
    """
    email_hash = hashlib.md5(email.encode()).hexdigest()
    license_path = os.path.join(LICENSE_DIR, f"{email_hash}.json")
    
    if not os.path.exists(license_path):
        return {'success': False, 'message': 'No license found for this email'}
    
    try:
        with open(license_path) as f:
            data = json.load(f)
        
        data['active'] = True
        data['renewed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Extend expiration if applicable
        if data.get('expires_at'):
            from datetime import timedelta
            new_expires = datetime.now(timezone.utc) + timedelta(days=30)
            data['expires_at'] = new_expires.isoformat()
        
        with open(license_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'email': email,
            'tier': data.get('tier', 'unknown'),
            'license_key': data.get('license_key', 'unknown'),
            'expires_at': data.get('expires_at'),
            'renewed_at': data['renewed_at']
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}


def list_licenses():
    """
    List all stored licenses.
    
    Returns:
        list of dicts with license summaries
    """
    if not os.path.exists(LICENSE_DIR):
        return []
    
    licenses = []
    for filename in os.listdir(LICENSE_DIR):
        if not filename.endswith('.json'):
            continue
        
        license_path = os.path.join(LICENSE_DIR, filename)
        try:
            with open(license_path) as f:
                data = json.load(f)
            
            licenses.append({
                'license_key': data.get('license_key', 'unknown')[:20] + '...',
                'email': data.get('email', 'unknown'),
                'tier': data.get('tier', 'unknown'),
                'active': data.get('active', False),
                'granted_at': data.get('granted_at', 'unknown'),
                'expires_at': data.get('expires_at', 'never'),
                'validation_count': data.get('validation_count', 0),
                'last_validated': data.get('last_validated', 'never')
            })
        except Exception:
            pass
    
    return sorted(licenses, key=lambda l: l.get('granted_at', ''), reverse=True)


# ─── CLI Interface ──────────────────────────────────────────────────────────


def main():
    """CLI entry point for license management."""
    if len(sys.argv) < 2:
        print("NeuralCline License Manager v2.0.0")
        print()
        print("Usage:")
        print("  python3 lib/payment/license_manager.py generate --email <email> --tier <tier>")
        print("  python3 lib/payment/license_manager.py validate --key <license_key>")
        print("  python3 lib/payment/license_manager.py revoke --email <email>")
        print("  python3 lib/payment/license_manager.py renew --email <email>")
        print("  python3 lib/payment/license_manager.py list")
        print()
        print("Tiers: pro, enterprise, lifetime")
        return
    
    command = sys.argv[1]
    
    if command == 'generate':
        email = None
        tier = 'pro'
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--email' and i + 2 < len(sys.argv):
                email = sys.argv[i + 3]
            elif arg == '--tier' and i + 2 < len(sys.argv):
                tier = sys.argv[i + 3]
        
        if not email:
            print("Error: --email is required")
            return
        
        try:
            result = generate_license(email, tier)
            print(json.dumps(result, indent=2))
            print()
            print(f"License key generated for {email}")
            print(f"Tier: {tier}")
            print(f"Key: {result['license_key']}")
            print(f"Store this key securely. Set NEURALCLINE_LICENSE_KEY to activate.")
        except Exception as e:
            print(f"Error: {e}")
    
    elif command == 'validate':
        license_key = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--key' and i + 2 < len(sys.argv):
                license_key = sys.argv[i + 3]
        
        if not license_key:
            print("Error: --key is required")
            return
        
        result = validate_license(license_key)
        print(json.dumps(result, indent=2))
        
        if result['valid']:
            print(f"✅ Valid {result['tier']} license for {result.get('email', 'unknown')}")
        else:
            print(f"❌ {result['message']}")
    
    elif command == 'revoke':
        email = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--email' and i + 2 < len(sys.argv):
                email = sys.argv[i + 3]
        
        if not email:
            print("Error: --email is required")
            return
        
        result = revoke_license(email)
        print(json.dumps(result, indent=2))
        
        if result['success']:
            print(f"✅ License revoked for {email}")
        else:
            print(f"❌ {result['message']}")
    
    elif command == 'renew':
        email = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == '--email' and i + 2 < len(sys.argv):
                email = sys.argv[i + 3]
        
        if not email:
            print("Error: --email is required")
            return
        
        result = renew_license(email)
        print(json.dumps(result, indent=2))
        
        if result['success']:
            print(f"✅ License renewed for {email}")
        else:
            print(f"❌ {result['message']}")
    
    elif command == 'list':
        licenses = list_licenses()
        if not licenses:
            print("No licenses found.")
            return
        
        print(f"Found {len(licenses)} license(s):")
        print()
        for lic in licenses:
            status = '✅ Active' if lic['active'] else '❌ Revoked'
            print(f"  {lic['email']} — {lic['tier']} — {status}")
            print(f"    Key: {lic['license_key']}")
            print(f"    Granted: {lic['granted_at']}")
            if lic['expires_at'] != 'never':
                print(f"    Expires: {lic['expires_at']}")
            print(f"    Validations: {lic['validation_count']}")
            print()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()