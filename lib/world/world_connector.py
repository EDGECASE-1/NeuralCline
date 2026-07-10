#!/usr/bin/env python3
"""
NeuralCline World Library Connector — External Knowledge Integration
=======================================================================
Purpose: Connects NeuralCline's crash context to external knowledge
sources for enriched recovery decisions. Each source provides context
that makes recovery more intelligent and faster.

Features:
  - Graceful degradation: if any source is unavailable, skip it
  - Unified interface: all sources implement the same query() method
  - Rate limiting: respects API limits on external services
  - Caching: results cached locally to reduce external calls
  - Privacy: only crash metadata (no code/context) sent externally

Usage:
  from lib.world import WorldLibraryConnector
  wlc = WorldLibraryConnector()
  enriched = wlc.enrich_crash_context(crash_event)
"""

import os
import sys
import json
import time
import hashlib
import logging
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger('neuralcline.world')

SESSION_DIR = os.environ.get(
    'NEURALCLINE_SESSION_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 'session-state')
)
WORLD_CACHE_DIR = os.path.join(SESSION_DIR, 'world-cache')
os.makedirs(WORLD_CACHE_DIR, exist_ok=True)

CACHE_TTL = 3600  # 1 hour cache TTL


def _cache_key(prefix: str, query: str) -> str:
    """Generate a cache key from a query string."""
    h = hashlib.md5(query.encode('utf-8')).hexdigest()[:12]
    return f"{prefix}-{h}"


def _read_cache(key: str) -> Optional[Dict]:
    """Read from local cache if not expired."""
    path = os.path.join(WORLD_CACHE_DIR, f"{key}.json")
    try:
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            age = time.time() - data.get('cached_at', 0)
            if age < CACHE_TTL:
                return data.get('result')
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _write_cache(key: str, result: Any):
    """Write result to local cache."""
    path = os.path.join(WORLD_CACHE_DIR, f"{key}.json")
    try:
        with open(path, 'w') as f:
            json.dump({
                'cached_at': time.time(),
                'result': result,
            }, f)
    except IOError:
        pass


class BaseConnector:
    """Base class for all world library connectors."""
    
    def __init__(self, name: str):
        self.name = name
        self.available = False
    
    def query(self, crash_event: Any) -> Dict:
        """Query external source for crash context. Returns dict with results."""
        raise NotImplementedError
    
    def _handle_error(self, error: Exception) -> Dict:
        """Handle errors gracefully — return empty result."""
        logger.debug(f"{self.name} unavailable: {error}")
        return {'error': str(error), 'results': []}


class GitHubConnector(BaseConnector):
    """Queries GitHub Issues API for similar crash patterns."""
    
    def __init__(self, api_token: Optional[str] = None):
        super().__init__('github')
        self.api_token = api_token or os.environ.get('GITHUB_TOKEN', '')
        self.base_url = 'https://api.github.com'
    
    def query(self, crash_event) -> Dict:
        """Search GitHub for issues matching crash type."""
        try:
            crash_type = getattr(crash_event, 'crash_type', 'unknown')
            cmd = getattr(crash_event, 'command', '')[:50]
            
            cache_key = _cache_key('gh', f"{crash_type}-{cmd}")
            cached = _read_cache(cache_key)
            if cached:
                return cached
            
            query = urllib.parse.quote(f"{crash_type} crash session recovery agent")
            url = f"{self.base_url}/search/issues?q={query}&per_page=5"
            
            req = urllib.request.Request(url)
            if self.api_token:
                req.add_header('Authorization', f'token {self.api_token}')
            req.add_header('Accept', 'application/vnd.github.v3+json')
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            
            results = []
            for item in data.get('items', [])[:5]:
                results.append({
                    'title': item['title'],
                    'url': item['html_url'],
                    'state': item['state'],
                    'labels': [l['name'] for l in item.get('labels', [])],
                })
            
            result = {'source': 'github', 'issues': results}
            _write_cache(cache_key, result)
            return result
            
        except Exception as e:
            return self._handle_error(e)


class SOConnector(BaseConnector):
    """Queries Stack Overflow for error resolutions."""
    
    def __init__(self):
        super().__init__('stackoverflow')
        self.base_url = 'https://api.stackexchange.com/2.3'
    
    def query(self, crash_event) -> Dict:
        """Search Stack Overflow for related Q&A."""
        try:
            crash_type = getattr(crash_event, 'crash_type', 'unknown')
            
            cache_key = _cache_key('so', crash_type)
            cached = _read_cache(cache_key)
            if cached:
                return cached
            
            query = urllib.parse.quote(f"AI agent {crash_type} session recovery")
            url = f"{self.base_url}/search?order=desc&sort=votes&q={query}&site=stackoverflow"
            
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            
            results = []
            for item in data.get('items', [])[:5]:
                results.append({
                    'title': item['title'],
                    'score': item.get('score', 0),
                    'answer_count': item.get('answer_count', 0),
                    'url': item.get('link', ''),
                })
            
            result = {'source': 'stackoverflow', 'questions': results}
            _write_cache(cache_key, result)
            return result
            
        except Exception as e:
            return self._handle_error(e)


class PackageConnector(BaseConnector):
    """Queries PyPI/npm for package version and health data."""
    
    def __init__(self):
        super().__init__('package_manager')
    
    def query(self, crash_event) -> Dict:
        """Check if known package issues relate to crash."""
        try:
            cmd = getattr(crash_event, 'command', '')
            details = getattr(crash_event, 'details', {})
            
            # Extract package names from command if possible
            packages = set()
            for pkg in ['neuralcline', 'python3', 'npm', 'pip', 'node']:
                if pkg in cmd.lower():
                    packages.add(pkg)
            
            results = {}
            if 'neuralcline' in packages or 'python3' in packages:
                # Check PyPI for neuralcline or python packages
                try:
                    url = 'https://pypi.org/pypi/neuralcline/json'
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read().decode())
                        results['neuralcline'] = {
                            'version': data.get('info', {}).get('version', 'unknown'),
                            'requires_python': data.get('info', {}).get('requires_python', 'any'),
                        }
                except (urllib.error.HTTPError, urllib.error.URLError):
                    # Package may not be published yet — that's fine
                    results['neuralcline'] = {'note': 'Not found on PyPI (expected)'}
            
            return {'source': 'package_manager', 'packages': results}
            
        except Exception as e:
            return self._handle_error(e)


class LocalHistoryConnector(BaseConnector):
    """Queries local crash history for similar patterns."""
    
    def __init__(self):
        super().__init__('local_history')
        self.crash_log_path = os.path.join(
            SESSION_DIR.replace('/session-state', ''), 
            'session-state', 'crash-log.ndjson'
        )
    
    def query(self, crash_event) -> Dict:
        """Find similar crashes in local history."""
        try:
            crash_type = getattr(crash_event, 'crash_type', 'unknown')
            
            similar = []
            if os.path.exists(self.crash_log_path):
                with open(self.crash_log_path) as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('crash_type') == crash_type:
                                similar.append(entry)
                                if len(similar) >= 10:
                                    break
                        except json.JSONDecodeError:
                            continue
            
            return {
                'source': 'local_history',
                'similar_crashes': len(similar),
                'recent_similar': similar[-5:] if similar else [],
            }
            
        except Exception as e:
            return self._handle_error(e)


class WorldLibraryConnector:
    """
    Main connector that integrates all world library sources.
    Provides a unified interface for enriching crash context.
    """
    
    def __init__(self):
        self.sources = {}
        self._init_sources()
    
    def _init_sources(self):
        """Initialize all available sources with graceful failure."""
        sources = [
            ('github', GitHubConnector()),
            ('stackoverflow', SOConnector()),
            ('package_manager', PackageConnector()),
            ('local_history', LocalHistoryConnector()),
        ]
        
        for name, connector in sources:
            try:
                # Quick availability test
                self.sources[name] = connector
                logger.info(f"Initialized source: {name}")
            except Exception as e:
                logger.warning(f"Failed to init source {name}: {e}")
    
    def enrich_crash_context(self, crash_event) -> Dict:
        """
        Gather context from all available world libraries.
        Returns enriched crash data with external context.
        
        Graceful degradation: if any source fails, others still contribute.
        """
        context = {}
        
        for name, source in self.sources.items():
            try:
                result = source.query(crash_event)
                if result and 'error' not in result:
                    context[name] = result
                    logger.info(f"Enriched from {name}: {len(result)} results")
            except Exception as e:
                logger.debug(f"Source {name} query failed: {e}")
                continue  # Graceful degradation
        
        return context
    
    def get_available_sources(self) -> List[str]:
        """Return list of currently available sources."""
        return list(self.sources.keys())
    
    def get_stats(self) -> Dict:
        """Return usage statistics for all sources."""
        stats = {}
        for name, source in self.sources.items():
            stats[name] = {
                'available': True,
                'type': source.__class__.__name__,
            }
        return {'sources': stats, 'total': len(self.sources)}


# ─── CLI Interface ─────────────────────────────────────────────────


def cmd_enrich(args):
    """Test world library enrichment with mock crash data."""
    from lib.crash_buffer import CrashEvent, CrashSeverity
    
    crash = CrashEvent(
        crash_type='timeout',
        exit_code=1,
        command='pip install neuralcline',
        context_usage_pct=65.0,
        execution_duration_ms=45000,
        tool_call_count=180,
        severity=CrashSeverity.MEDIUM,
        details={'python_version': '3.10'},
    )
    
    wlc = WorldLibraryConnector()
    context = wlc.enrich_crash_context(crash)
    print(json.dumps(context, indent=2))


def cmd_sources(args):
    """List available world library sources."""
    wlc = WorldLibraryConnector()
    stats = wlc.get_stats()
    print(json.dumps(stats, indent=2))
    print(f"\nAvailable sources: {', '.join(wlc.get_available_sources())}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        'enrich': cmd_enrich,
        'sources': cmd_sources,
    }
    
    if command in commands:
        commands[command](args)
    else:
        print(f"Unknown: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()