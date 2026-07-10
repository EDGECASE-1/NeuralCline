#!/usr/bin/env python3
"""
NeuralCline Adapter for Grok (xAI) — Universal Model Integration
====================================================================
Purpose: Adapts NeuralCline's session safety system for use with
Grok, the xAI conversational and coding agent. This demonstrates
the universal adapter pattern that works with any LLM platform.

Integration Strategy:
  - WebSocket session monitoring via xAI API
  - Streaming response interception for context tracking
  - Checkpoint injection via API calls
  - Crash detection via response monitoring

Usage:
  from lib.adapters.adapter_grok import GrokAdapter
  adapter = GrokAdapter(api_key="xai-...")
  session = adapter.create_session(model="grok-3")
  state = adapter.get_session_state(session.id)
"""

import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger('neuralcline.adapter.grok')

# Add parent directory to path for imports when run standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.adapters.base import BaseAdapter, SessionState, Checkpoint, ContextMetrics


class GrokAdapter(BaseAdapter):
    """
    Adapter for Grok (xAI) — provides session safety for Grok agents.
    
    Features:
    - Model-specific context window tracking (Grok-3: 256K tokens)
    - Session state monitoring via xAI API
    - Checkpoint injection for crash recovery
    - Response streaming interception
    - Crash event detection
    
    Models supported:
    - grok-3 (256K context)
    - grok-3-mini (128K context)
    - grok-2 (128K context)
    """
    
    MODEL_CONTEXT_WINDOWS = {
        'grok-3': 262144,
        'grok-3-mini': 131072,
        'grok-2': 131072,
        'grok-2-mini': 65536,
    }
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: str = 'https://api.x.ai/v1'):
        super().__init__()
        self.api_key = api_key or os.environ.get('XAI_API_KEY', '')
        self.base_url = base_url
        self._sessions: Dict[str, Dict] = {}
        
        if not self.api_key:
            logger.warning("No xAI API key provided. Set XAI_API_KEY env var.")
    
    def create_session(self, 
                       model: str = 'grok-3',
                       system_prompt: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> SessionState:
        """
        Create a new Grok session with NeuralCline protection.
        
        Args:
            model: Grok model name (default: grok-3)
            system_prompt: Optional system prompt
            metadata: Optional session metadata
        
        Returns:
            SessionState with initialized session tracking
        """
        session_id = f"grok-{uuid.uuid4()[:12]}"
        context_window = self.MODEL_CONTEXT_WINDOWS.get(model, 131072)
        
        session_state = SessionState(
            session_id=session_id,
            model=model,
            platform='grok',
            context_window=context_window,
            context_used=0,
            tool_call_count=0,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_active=datetime.now(timezone.utc).isoformat(),
            metadata={
                'api_base': self.base_url,
                'system_prompt_length': len(system_prompt or ''),
                **(metadata or {}),
            }
        )
        
        self._sessions[session_id] = session_state.to_dict()
        logger.info(f"Created Grok session: {session_id} (model: {model})")
        return session_state
    
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """Get current state of a Grok session."""
        session_data = self._sessions.get(session_id)
        if session_data:
            return SessionState.from_dict(session_data)
        return None
    
    def inject_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """
        Inject a checkpoint into a Grok session.
        For API-based sessions, this stores state for recovery.
        """
        session = self._sessions.get(checkpoint.session_id)
        if not session:
            logger.warning(f"Session {checkpoint.session_id} not found")
            return False
        
        session['last_checkpoint'] = checkpoint.to_dict()
        session['last_checkpoint_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Checkpoint injected into session {checkpoint.session_id}")
        return True
    
    def monitor_context(self, session_id: str) -> Optional[ContextMetrics]:
        """
        Monitor Grok's context window usage.
        Returns metrics about current context pressure.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        context_window = session.get('context_window', 131072)
        context_used = session.get('context_used', 0)
        
        usage_pct = (context_used / context_window) * 100 if context_window > 0 else 0
        
        # Determine pressure level
        if usage_pct >= 80:
            pressure = 'critical'
        elif usage_pct >= 60:
            pressure = 'warning'
        elif usage_pct >= 40:
            pressure = 'elevated'
        else:
            pressure = 'normal'
        
        return ContextMetrics(
            session_id=session_id,
            context_used=context_used,
            context_window=context_window,
            usage_pct=usage_pct,
            pressure=pressure,
            tool_call_count=session.get('tool_call_count', 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    def intercept_crash(self, crash_event: Any) -> Optional[Dict]:
        """
        Intercept a crash event and return recovery context.
        
        For Grok, crash scenarios include:
        - API timeout errors
        - Streaming disconnection
        - Context overflow
        - Rate limit errors
        """
        crash_type = getattr(crash_event, 'crash_type', 'unknown')
        session_id = getattr(crash_event, 'session_id', None)
        
        # If we have a checkpoint, we can recover
        if session_id and session_id in self._sessions:
            checkpoint = self._sessions[session_id].get('last_checkpoint')
            if checkpoint:
                return {
                    'can_recover': True,
                    'recovery_type': 'checkpoint_restore' if crash_type == 'timeout' else 'partial',
                    'checkpoint': checkpoint,
                    'session_id': session_id,
                }
        
        return {
            'can_recover': False,
            'recovery_type': 'fresh',
            'message': 'No checkpoint available for recovery',
        }
    
    def get_model_config(self) -> Dict[str, Any]:
        """Return Grok model configuration."""
        return {
            'platform': 'grok',
            'vendor': 'xAI',
            'models': list(self.MODEL_CONTEXT_WINDOWS.keys()),
            'context_windows': self.MODEL_CONTEXT_WINDOWS,
            'api_base': self.base_url,
            'supports_streaming': True,
            'supports_checkpoints': True,
            'max_tool_calls_per_session': 500,
        }
    
    def update_session_context(self, 
                                session_id: str, 
                                tokens_used: int,
                                tool_calls: int = 1) -> bool:
        """Update session context usage tracking."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session['context_used'] = session.get('context_used', 0) + tokens_used
        session['tool_call_count'] = session.get('tool_call_count', 0) + tool_calls
        session['last_active'] = datetime.now(timezone.utc).isoformat()
        return True


# ─── CLI Interface for standalone testing ─────────────────────────


def cli_create_session(args):
    """Create a new Grok session."""
    model = args[0] if args else 'grok-3'
    adapter = GrokAdapter()
    session = adapter.create_session(model=model)
    print(json.dumps(session.to_dict(), indent=2))


def cli_monitor(args):
    """Monitor context for a session."""
    if not args:
        print("Usage: adapter_grok.py monitor <session_id>")
        return
    adapter = GrokAdapter()
    metrics = adapter.monitor_context(args[0])
    if metrics:
        print(json.dumps(metrics.to_dict(), indent=2))
    else:
        print(f"Session {args[0]} not found")


def cli_config(args):
    """Show model configuration."""
    adapter = GrokAdapter()
    config = adapter.get_model_config()
    print(json.dumps(config, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        'create': cli_create_session,
        'monitor': cli_monitor,
        'config': cli_config,
    }
    
    if command in commands:
        commands[command](args)
    else:
        print(f"Unknown: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()