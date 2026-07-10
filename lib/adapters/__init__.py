"""
NeuralCline Adapters — Model-Agnostic Integration Layer
========================================================
Each adapter translates between a specific AI coding agent's format
and NeuralCline's universal session core API.

Available adapters:
  - Cline:     adapter_cline.py
  - Copilot:   adapter_copilot.py
  - Cursor:    adapter_cursor.py
  - Codeium:   adapter_codeium.py
  - Generic:   adapter_generic.py (any shell-based agent)

Usage:
    from lib.adapters import get_adapter
    adapter = get_adapter('cline')
    adapter.install()
    adapter.record_execution("ls -la", 1500, 0)
"""

from lib.adapters.base import BaseAdapter
from lib.adapters.adapter_cline import ClineAdapter
from lib.adapters.adapter_generic import GenericAdapter

ADAPTER_REGISTRY = {
    'cline': ClineAdapter,
    'generic': GenericAdapter,
}


def get_adapter(name):
    """Get an adapter instance by name."""
    if name not in ADAPTER_REGISTRY:
        raise ValueError(f"Unknown adapter: {name}. Available: {list(ADAPTER_REGISTRY.keys())}")
    return ADAPTER_REGISTRY[name]()


def list_adapters():
    """List all available adapters."""
    return list(ADAPTER_REGISTRY.keys())


def register_adapter(name, adapter_class):
    """Register a new adapter."""
    if not issubclass(adapter_class, BaseAdapter):
        raise TypeError(f"Adapter must inherit from BaseAdapter")
    ADAPTER_REGISTRY[name] = adapter_class