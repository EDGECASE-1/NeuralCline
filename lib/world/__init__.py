"""
NeuralCline World Library Integration — External Knowledge Connectors
=======================================================================
Purpose: Connect NeuralCline's nervous system to the world's major 
libraries and data sources so recovery decisions are smarter, faster,
and informed by global knowledge, not just local patterns.

Sources:
  - GitHub Issues API → Latest bug patterns & fixes
  - Stack Overflow API → Common error resolutions  
  - PyPI/npm API → Package version conflicts & known issues
  - Local file system → Project-specific crash history
  - Package health → Dependency vulnerability data

Usage:
  from lib.world import WorldLibraryConnector
  wlc = WorldLibraryConnector()
  context = wlc.enrich_crash_context(crash_event)
"""

from .world_connector import WorldLibraryConnector

__all__ = ['WorldLibraryConnector']