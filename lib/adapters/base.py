"""
NeuralCline Base Adapter — Abstract Interface for All AI Coding Agents
========================================================================
All adapters must inherit from BaseAdapter and implement:
  - name: Human-readable name of the agent
  - agent_id: Unique identifier for the agent
  - install(): Install NeuralCline integration for this agent
  - uninstall(): Remove NeuralCline integration
  - detect(): Check if this agent is present in the environment
  - get_version(): Get the agent's version string
  - get_config_path(): Get the agent's configuration file path
  - record_execution(cmd, dur_ms, exit_code, output_size): Record an execution
"""

from abc import ABC, abstractmethod
import os
import sys
import json


class BaseAdapter(ABC):
    """Abstract base class for all NeuralCline adapters."""
    
    @property
    @abstractmethod
    def name(self):
        """Human-readable name of the agent (e.g., 'Cline', 'GitHub Copilot')."""
        pass
    
    @property
    @abstractmethod
    def agent_id(self):
        """Unique identifier for the agent (e.g., 'cline', 'copilot')."""
        pass
    
    @abstractmethod
    def install(self):
        """
        Install NeuralCline integration for this agent.
        
        This typically involves:
        1. Creating symlinks to NeuralCline hooks
        2. Modifying the agent's configuration to use NeuralCline
        3. Setting up auto-init hooks
        4. Tuning timeout settings
        
        Returns dict with install results.
        """
        pass
    
    @abstractmethod
    def uninstall(self):
        """
        Remove NeuralCline integration for this agent.
        
        Returns dict with uninstall results.
        """
        pass
    
    @abstractmethod
    def detect(self):
        """
        Check if this agent is present in the environment.
        
        Returns dict with:
          - present: True/False
          - path: installation path (if found)
          - version: version string (if found)
        """
        pass
    
    @abstractmethod
    def get_version(self):
        """Get the agent's version string."""
        pass
    
    @abstractmethod
    def get_config_path(self):
        """Get the agent's configuration file path(s)."""
        pass
    
    def record_execution(self, command, duration_ms, exit_code, output_size=0):
        """
        Record an execution event through the session core.
        
        This is a convenience method that delegates to SessionCore.
        Adapters can override this to add agent-specific logic.
        """
        from lib.session_core import SessionCore
        core = SessionCore()
        return core.record_execution(command, duration_ms, exit_code, output_size)
    
    def get_status(self):
        """
        Get the adapter's integration status.
        
        Returns dict with:
          - adapter: agent name
          - installed: whether NeuralCline is integrated
          - config: agent configuration details
          - hooks: hook installation status
        """
        return {
            'adapter': self.name,
            'agent_id': self.agent_id,
            'installed': self._check_installation(),
            'config': self._get_config_status(),
            'hooks': self._get_hook_status()
        }
    
    def _check_installation(self):
        """Check if NeuralCline is installed for this agent."""
        return False  # Override in subclasses
    
    def _get_config_status(self):
        """Get configuration status for this agent."""
        return {}
    
    def _get_hook_status(self):
        """Get hook installation status for this agent."""
        return {}
    
    def __str__(self):
        return f"{self.name} Adapter ({self.agent_id})"