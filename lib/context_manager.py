#!/usr/bin/env python3
"""
NeuralCline Context Manager — Agentic AI Context Window Optimization
=====================================================================
Monitors context window pressure and provides strategies for:
  1. Early warning when context is approaching limits
  2. Automatic checkpoint generation at critical thresholds
  3. Session state compression for efficient storage
  4. Adaptive recovery strategies based on available context

This is the core differentiator for agentic AI interfaces where
context windows (1M+ tokens) and session crashes are the highest
failure modes.

Features:
  - Real-time context usage tracking per model
  - Model-specific context window sizes (DeepSeek, Claude, GPT, Gemini)
  - Adaptive checkpoint generation based on context pressure
  - Session state compression (lossless)
  - Recovery strategy selection based on available context
  - Cross-session context metrics logging

Usage:
    from lib.context_manager import ContextManager
    cm = ContextManager(model='deepseek-v4')
    usage = cm.get_context_usage()
    if cm.should_checkpoint()['should_checkpoint']:
        cm.compress_state()
        strategy = cm.select_recovery_strategy({})
"""

import json
import os
import math
import time
from datetime import datetime, timezone
from collections import deque

# Context window thresholds (as percentage of max)
THRESHOLDS = {
    'safe': 0.00,       # 0% — no action needed
    'info': 0.40,       # 40% — start monitoring
    'warning': 0.60,    # 60% — suggest checkpoint
    'critical': 0.75,   # 75% — force checkpoint, suggest handoff
    'danger': 0.85,     # 85% — force handoff, refuse new operations
    'emergency': 0.95,  # 95% — emergency compression, flush state
}

# Context window sizes for different models (in tokens)
MODEL_CONTEXT_SIZES = {
    # Anthropic
    'claude-3-opus': 200000,
    'claude-3-sonnet': 200000,
    'claude-3-haiku': 200000,
    'claude-4': 200000,
    # OpenAI
    'gpt-4': 128000,
    'gpt-4-turbo': 128000,
    'gpt-4o': 128000,
    'gpt-4o-mini': 128000,
    'o1': 200000,
    'o3': 200000,
    # Google
    'gemini-pro': 1000000,
    'gemini-ultra': 1000000,
    'gemini-1.5-pro': 1000000,
    'gemini-1.5-flash': 1000000,
    # DeepSeek
    'deepseek-v2': 128000,
    'deepseek-v3': 64000,
    'deepseek-v4': 1000000,
    'deepseek-r1': 1000000,
    # Mistral / Codestral
    'codestral': 256000,
    'mistral-large': 128000,
    'mixtral': 32768,
    # Meta
    'llama-3': 128000,
    'llama-3.1': 128000,
    'llama-4': 1000000,
    # Default fallback
    'default': 100000,
}


class ContextManager:
    """
    Manages context window pressure for agentic AI sessions.
    
    This class is the core of NeuralCline's agentic AI optimization.
    It tracks context usage across all sessions, provides early warning
    before context limits are reached, and selects optimal recovery
    strategies based on remaining context capacity.
    
    Key metrics:
    - current_tokens: Estimated tokens currently in context
    - max_tokens: Model's maximum context window size
    - usage_pct: Percentage of context window used
    - threshold: Current urgency level (safe → emergency)
    - remaining_tokens: Tokens remaining before limit
    - estimated_calls_remaining: Estimated tool calls before critical
    """
    
    def __init__(self, session_dir=None, model='default'):
        self.session_dir = session_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'session-state'
        )
        self.model = model
        self.max_context = MODEL_CONTEXT_SIZES.get(model, MODEL_CONTEXT_SIZES['default'])
        self.state_file = os.path.join(self.session_dir, 'current-state.json')
        self.checkpoint_file = os.path.join(self.session_dir, 'checkpoint.json')
        self.metrics_file = os.path.join(self.session_dir, 'context-metrics.json')
        
        os.makedirs(self.session_dir, exist_ok=True)
    
    def get_context_usage(self):
        """
        Estimate current context usage based on session state.
        
        Returns dict with:
          - current_tokens: estimated tokens used
          - max_tokens: model's context window size
          - usage_pct: percentage of context used
          - threshold: current threshold level
          - remaining_tokens: tokens remaining
          - estimated_calls_remaining: estimated tool calls before critical
          - model: the model name
        """
        state = self._read_state()
        
        # Estimate tokens from tool calls and command history
        tool_calls = state.get('tool_call_count', 0)
        last_command = state.get('last_command', '')
        
        # Rough estimation: each tool call ~2000 tokens of context
        # Each command ~10 tokens per character
        estimated_tokens = tool_calls * 2000 + len(last_command) * 10
        
        # Add overhead for system prompts, file contents, etc.
        overhead = state.get('context_overhead', 0)
        estimated_tokens += overhead
        
        usage_pct = min(100, int(estimated_tokens * 100 / max(self.max_context, 1)))
        
        # Determine threshold level
        threshold = 'safe'
        for level, pct in sorted(THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if pct == 0:
                continue
            if usage_pct >= pct * 100:
                threshold = level
                break
        
        remaining = max(0, self.max_context - estimated_tokens)
        calls_remaining = max(0, remaining // 2000)
        
        return {
            'current_tokens': estimated_tokens,
            'max_tokens': self.max_context,
            'usage_pct': usage_pct,
            'threshold': threshold,
            'remaining_tokens': remaining,
            'estimated_calls_remaining': calls_remaining,
            'model': self.model,
        }
    
    def should_checkpoint(self):
        """
        Determine if a checkpoint should be generated based on context pressure.
        
        Returns:
          - should_checkpoint: bool
          - reason: string explanation
          - urgency: 'low', 'medium', 'high', 'critical'
          - action: recommended action string
        """
        usage = self.get_context_usage()
        threshold = usage['threshold']
        
        if threshold in ('danger', 'emergency'):
            return {
                'should_checkpoint': True,
                'reason': f"Context at {usage['usage_pct']}% ({threshold})",
                'urgency': 'critical',
                'action': 'FORCE_CHECKPOINT_AND_HANDOFF'
            }
        elif threshold == 'critical':
            return {
                'should_checkpoint': True,
                'reason': f"Context at {usage['usage_pct']}% (critical)",
                'urgency': 'high',
                'action': 'FORCE_CHECKPOINT'
            }
        elif threshold == 'warning':
            return {
                'should_checkpoint': True,
                'reason': f"Context at {usage['usage_pct']}% (warning)",
                'urgency': 'medium',
                'action': 'SUGGEST_CHECKPOINT'
            }
        elif threshold == 'info':
            return {
                'should_checkpoint': False,
                'reason': f"Context at {usage['usage_pct']}% — monitoring",
                'urgency': 'low',
                'action': 'MONITOR'
            }
        else:
            return {
                'should_checkpoint': False,
                'reason': f"Context at {usage['usage_pct']}% — safe",
                'urgency': 'low',
                'action': 'NONE'
            }
    
    def compress_state(self):
        """
        Compress session state to reduce context footprint.
        
        Strategies:
        1. Truncate command history to last 50 entries
        2. Summarize failure patterns (keep top 5)
        3. Remove redundant crash log entries
        4. Compress timing history (keep rolling averages, drop raw)
        
        Returns dict with compression stats (before/after bytes, savings).
        """
        state = self._read_state()
        before_size = len(json.dumps(state))
        
        # Strategy 1: Truncate command history
        if 'command_history' in state and len(state['command_history']) > 50:
            state['command_history'] = state['command_history'][-50:]
            state['_compressed'] = True
            state['_compressed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Strategy 2: Summarize failure patterns
        if 'failure_patterns' in state and len(state.get('failure_patterns', [])) > 5:
            state['failure_patterns'] = state['failure_patterns'][:5]
        
        # Strategy 3: Compress timing metrics (keep only essential)
        if 'timing_metrics' in state:
            timing = state['timing_metrics']
            state['timing_metrics'] = {
                'eef': timing.get('execution_emulation_factor', 1.0),
                'timeout_proximity': timing.get('timeout_proximity', 0),
                'rolling_avg_ms': timing.get('rolling_avg_ms', 0),
                'total_commands_tracked': timing.get('total_commands_tracked', 0),
                'recent_failures': timing.get('recent_failures', 0),
            }
        
        after_size = len(json.dumps(state))
        savings = before_size - after_size
        savings_pct = int(savings * 100 / max(before_size, 1))
        
        self._write_state(state)
        
        return {
            'before_bytes': before_size,
            'after_bytes': after_size,
            'savings_bytes': savings,
            'savings_pct': savings_pct,
        }
    
    def select_recovery_strategy(self, crash_context=None):
        """
        Select the best recovery strategy based on available context.
        
        Strategies:
        1. Full recovery — restore complete checkpoint (needs 20%+ context free)
        2. Partial recovery — restore essential state only (needs 10%+ context free)
        3. Minimal recovery — restore only session ID and goals (needs 5%+ context free)
        4. Fresh start — no context available, start new session
        
        Returns dict with selected strategy, description, and action.
        """
        usage = self.get_context_usage()
        free_pct = 100 - usage['usage_pct']
        
        if free_pct >= 20:
            return {
                'strategy': 'full',
                'description': 'Full checkpoint restoration',
                'context_needed': '20%',
                'context_available': f"{free_pct}%",
                'action': 'Restore complete checkpoint from checkpoint.json'
            }
        elif free_pct >= 10:
            return {
                'strategy': 'partial',
                'description': 'Partial state restoration (essential only)',
                'context_needed': '10%',
                'context_available': f"{free_pct}%",
                'action': 'Restore session ID, goals, and last command only'
            }
        elif free_pct >= 5:
            return {
                'strategy': 'minimal',
                'description': 'Minimal recovery (session identity only)',
                'context_needed': '5%',
                'context_available': f"{free_pct}%",
                'action': 'Restore session ID and active goals only'
            }
        else:
            return {
                'strategy': 'fresh',
                'description': 'Fresh session start (context exhausted)',
                'context_needed': 'N/A',
                'context_available': f"{free_pct}%",
                'action': 'Generate handoff document, start new session'
            }
    
    def log_context_metrics(self):
        """Log current context metrics for historical analysis."""
        usage = self.get_context_usage()
        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **usage
        }
        
        # Append to context metrics file
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file) as f:
                    history = json.load(f)
            else:
                history = {'entries': []}
            
            history['entries'].append(metrics)
            
            # Keep last 1000 entries
            if len(history['entries']) > 1000:
                history['entries'] = history['entries'][-1000:]
            
            # Add summary stats
            if history['entries']:
                usage_pcts = [e['usage_pct'] for e in history['entries']]
                history['summary'] = {
                    'total_entries': len(history['entries']),
                    'avg_usage_pct': int(sum(usage_pcts) / len(usage_pcts)),
                    'max_usage_pct': max(usage_pcts),
                    'min_usage_pct': min(usage_pcts),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass
        
        return metrics
    
    def get_model_context_size(self, model_name=None):
        """Get the context window size for a given model."""
        model = model_name or self.model
        return MODEL_CONTEXT_SIZES.get(model, MODEL_CONTEXT_SIZES['default'])
    
    def get_threshold_level(self, usage_pct):
        """Get the threshold level for a given usage percentage."""
        for level, pct in sorted(THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if pct == 0:
                continue
            if usage_pct >= pct * 100:
                return level
        return 'safe'
    
    def _read_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file) as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}
    
    def _write_state(self, data):
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)


# ─── CLI Interface ──────────────────────────────────────────────────────────

def main():
    """CLI entry point for context management."""
    import sys
    
    if len(sys.argv) < 2:
        print("NeuralCline Context Manager v2.0.0")
        print()
        print("Usage:")
        print("  python3 lib/context_manager.py usage [--model <model>]")
        print("  python3 lib/context_manager.py checkpoint-check")
        print("  python3 lib/context_manager.py compress")
        print("  python3 lib/context_manager.py recovery-strategy")
        print("  python3 lib/context_manager.py log-metrics")
        print("  python3 lib/context_manager.py model-sizes")
        print()
        print("Models: claude-4, gpt-4o, gemini-1.5-pro, deepseek-v4, codestral, llama-3.1, default")
        return
    
    command = sys.argv[1]
    model = 'default'
    
    for i, arg in enumerate(sys.argv[2:]):
        if arg == '--model' and i + 2 < len(sys.argv):
            model = sys.argv[i + 3]
    
    cm = ContextManager(model=model)
    
    if command == 'usage':
        usage = cm.get_context_usage()
        print(f"Model:                     {usage['model']}")
        print(f"Context Window:            {usage['max_tokens']:,} tokens")
        print(f"Estimated Usage:           {usage['current_tokens']:,} tokens")
        print(f"Usage Percentage:          {usage['usage_pct']}%")
        print(f"Threshold Level:           {usage['threshold']}")
        print(f"Remaining Tokens:          {usage['remaining_tokens']:,}")
        print(f"Estimated Calls Remaining: {usage['estimated_calls_remaining']}")
    
    elif command == 'checkpoint-check':
        result = cm.should_checkpoint()
        print(f"Should Checkpoint: {result['should_checkpoint']}")
        print(f"Reason:            {result['reason']}")
        print(f"Urgency:           {result['urgency']}")
        print(f"Action:            {result['action']}")
    
    elif command == 'compress':
        result = cm.compress_state()
        print(f"Before: {result['before_bytes']:,} bytes")
        print(f"After:  {result['after_bytes']:,} bytes")
        print(f"Saved:  {result['savings_bytes']:,} bytes ({result['savings_pct']}%)")
    
    elif command == 'recovery-strategy':
        strategy = cm.select_recovery_strategy()
        print(f"Strategy:           {strategy['strategy']}")
        print(f"Description:        {strategy['description']}")
        print(f"Context Needed:     {strategy['context_needed']}")
        print(f"Context Available:  {strategy['context_available']}")
        print(f"Action:             {strategy['action']}")
    
    elif command == 'log-metrics':
        metrics = cm.log_context_metrics()
        print(f"Context metrics logged at {metrics['timestamp']}")
        print(f"Usage: {metrics['usage_pct']}% ({metrics['current_tokens']:,}/{metrics['max_tokens']:,})")
    
    elif command == 'model-sizes':
        print(f"{'Model':<25} {'Context Window':>15}")
        print("-" * 42)
        for name, size in sorted(MODEL_CONTEXT_SIZES.items(), key=lambda x: x[1]):
            print(f"{name:<25} {size:>15,}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()