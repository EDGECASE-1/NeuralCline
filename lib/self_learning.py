#!/usr/bin/env python3
"""
NeuralCline Self-Learning Foresight Engine — Autonomous Memory & Self-Healing
==============================================================================
Purpose: A self-learning organism that maintains persistent memory of all session
parameters, learns from historical patterns, and provides predictive foresight
for self-healing. It stores structured memories across sessions and builds a
knowledge graph of failure patterns, timing trends, and recovery effectiveness.

The organism has three layers:
  1. MEMORY — Stores all parameters with temporal decay and recency weighting
  2. FORESIGHT — Predicts issues before they occur using pattern matching
  3. SELF-HEALING — Auto-adjusts thresholds and recommends corrective actions

Usage: python3 /root/NeuralCline/lib/self_learning.py <command> [args...]
"""

import json
import os
import re
import sys
import math
from datetime import datetime, timezone
from collections import defaultdict, deque
from copy import deepcopy

# Paths
SESSION_DIR = "/root/.session-state"
STATE_FILE = os.path.join(SESSION_DIR, "current-state.json")
MEMORY_FILE = os.path.join(SESSION_DIR, "session-memory.json")
TIMING_HISTORY = os.path.join(SESSION_DIR, "timing-history.json")
FAILURE_POINTS = os.path.join(SESSION_DIR, "failure-points.json")
CRASH_LOG = os.path.join(SESSION_DIR, "crash-log.ndjson")
CHECKPOINT_FILE = os.path.join(SESSION_DIR, "checkpoint.json")

# Constants
MAX_MEMORY_ENTRIES = 1000  # Max memory snapshots to retain
DECAY_HALF_LIFE_HOURS = 24  # Temporal decay half-life for memories
LEARNING_RATE = 0.15  # How fast the organism adapts to new patterns
SELF_HEAL_INTERVAL_CALLS = 10  # Run self-healing every N tool calls


def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_now():
    return datetime.now(timezone.utc).timestamp()


def temporal_decay_weight(timestamp_str, half_life_hours=DECAY_HALF_LIFE_HOURS):
    """Compute a decay weight (0.0–1.0) for a memory based on its age."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age_hours = (datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        return math.pow(0.5, age_hours / half_life_hours)
    except:
        return 0.5


# ===================== ORGANISM CORE =====================

class ForesightOrganism:
    """
    The self-learning organism that maintains memory, generates foresight,
    and performs self-healing.
    """

    def __init__(self):
        self.memory = read_json(MEMORY_FILE, {
            'organism_id': self._gen_organism_id(),
            'born': timestamp(),
            'memories': [],
            'learned_patterns': [],
            'thresholds': {},
            'self_healing_actions': [],
            'foresight_insights': [],
            'evolution': {
                'generations': 1,
                'last_evolved': timestamp(),
                'memory_count': 0,
                'pattern_count': 0,
                'healing_count': 0
            }
        })
        self._ensure_defaults()

    def _gen_organism_id(self):
        import uuid
        return f"NC-ORGANISM-{uuid.uuid4().hex[:12].upper()}"

    def _ensure_defaults(self):
        """Ensure default thresholds exist."""
        if 'thresholds' not in self.memory:
            self.memory['thresholds'] = {}
        thresholds = self.memory['thresholds']
        defaults = {
            'eef_warning': 1.2,
            'eef_elevated': 1.8,
            'eef_critical': 2.5,
            'timeout_proximity_warning': 60,
            'timeout_proximity_danger': 80,
            'crash_proximity_warning': 60,
            'crash_proximity_danger': 80,
            'context_usage_warning': 60,
            'context_usage_danger': 80,
            'rolling_avg_warning_ms': 15000,
            'rolling_avg_danger_ms': 30000,
            'consecutive_failures_warning': 3,
            'consecutive_failures_danger': 5,
            'memory_retention_max': MAX_MEMORY_ENTRIES,
            'learning_rate': LEARNING_RATE,
            'self_heal_interval': SELF_HEAL_INTERVAL_CALLS
        }
        for key, val in defaults.items():
            if key not in thresholds:
                thresholds[key] = val

    def save(self):
        self.memory['evolution']['memory_count'] = len(self.memory['memories'])
        self.memory['evolution']['pattern_count'] = len(self.memory['learned_patterns'])
        self.memory['evolution']['healing_count'] = len(self.memory['self_healing_actions'])
        write_json(MEMORY_FILE, self.memory)

    # ─── MEMORY LAYER ───────────────────────────────────────────────

    def snapshot(self):
        """
        Take a full memory snapshot of all current parameters.
        This is the organism's way of 'remembering' the current state.
        """
        state = read_json(STATE_FILE, {})
        timing = state.get('timing_metrics', {})
        fps = read_json(FAILURE_POINTS, {'failure_points': []})
        cp = read_json(CHECKPOINT_FILE, {})

        snapshot = {
            'timestamp': timestamp(),
            'epoch': epoch_now(),
            'session_id': state.get('session_id', 'unknown'),
            'parameters': {
                'context_usage_pct': state.get('context_usage_pct', 0),
                'tool_call_count': state.get('tool_call_count', 0),
                'last_exit_code': state.get('last_exit_code', 0),
                'last_proximity': state.get('last_proximity', 0),
                'execution_emulation_factor': timing.get('execution_emulation_factor', 1.0),
                'timeout_proximity': timing.get('timeout_proximity', 0),
                'rolling_avg_ms': timing.get('rolling_avg_ms', 0),
                'effective_time_estimate_ms': timing.get('effective_time_estimate_ms', 0),
                'recent_failures': timing.get('recent_failures', 0),
                'complexity': timing.get('complexity', 1),
                'total_crash_events': fps.get('total_crash_events', 0),
                'total_tool_calls': cp.get('total_tool_calls', 0),
                'success_rate': cp.get('success_rate', 100)
            },
            'failure_patterns': [p['pattern'] for p in fps.get('failure_points', [])[:5]],
            'last_command': state.get('last_command', '')[:80]
        }

        # Add to memory with temporal decay
        memories = self.memory['memories']
        memories.append(snapshot)

        # Prune old memories if exceeding max
        if len(memories) > MAX_MEMORY_ENTRIES:
            # Remove oldest memories, keeping the most recent
            memories[:] = memories[-MAX_MEMORY_ENTRIES:]

        # Learn from this snapshot
        self._learn_from_snapshot(snapshot)

        self.save()
        return snapshot

    def _learn_from_snapshot(self, snapshot):
        """
        Extract patterns from a snapshot and update learned patterns.
        This is the organism's learning mechanism.
        """
        params = snapshot['parameters']
        patterns = self.memory['learned_patterns']

        # Pattern 1: EEF + Timeout proximity correlation
        eef = params['execution_emulation_factor']
        timeout_prox = params['timeout_proximity']
        if eef > 1.5 and timeout_prox > 40:
            self._update_pattern('high_eef_with_timeout_risk', {
                'eef': eef,
                'timeout_proximity': timeout_prox,
                'rolling_avg': params['rolling_avg_ms'],
                'success_rate': params['success_rate']
            })

        # Pattern 2: Consecutive failures
        recent_failures = params['recent_failures']
        if recent_failures >= 3:
            self._update_pattern('consecutive_failures', {
                'count': recent_failures,
                'last_exit_code': params['last_exit_code'],
                'tool_calls': params['tool_call_count']
            })

        # Pattern 3: Context pressure + crash proximity
        ctx = params['context_usage_pct']
        prox = params['last_proximity']
        if ctx > 60 and prox > 50:
            self._update_pattern('context_pressure_with_crash_risk', {
                'context_pct': ctx,
                'crash_proximity': prox,
                'success_rate': params['success_rate']
            })

        # Pattern 4: Slow rolling average
        rolling = params['rolling_avg_ms']
        if rolling > 10000:
            self._update_pattern('degraded_performance', {
                'rolling_avg_ms': rolling,
                'eef': eef,
                'timeout_proximity': timeout_prox
            })

        # Pattern 5: Low success rate
        success = params['success_rate']
        if success < 80:
            self._update_pattern('low_success_rate', {
                'success_rate': success,
                'total_crashes': params['total_crash_events'],
                'tool_calls': params['tool_call_count']
            })

    def _update_pattern(self, pattern_name, data):
        """Update or create a learned pattern with temporal weighting."""
        patterns = self.memory['learned_patterns']
        now = timestamp()

        # Find existing pattern
        existing = None
        for p in patterns:
            if p['pattern'] == pattern_name:
                existing = p
                break

        if existing:
            # Update with exponential moving average
            lr = self.memory['thresholds'].get('learning_rate', LEARNING_RATE)
            for key, val in data.items():
                if key in existing.get('data', {}):
                    if isinstance(val, (int, float)):
                        existing['data'][key] = (1 - lr) * existing['data'][key] + lr * val
                else:
                    existing['data'][key] = val
            existing['count'] = existing.get('count', 0) + 1
            existing['last_seen'] = now
            existing['confidence'] = min(1.0, existing.get('count', 0) * 0.1)
        else:
            # Create new pattern
            patterns.append({
                'pattern': pattern_name,
                'data': data,
                'count': 1,
                'first_seen': now,
                'last_seen': now,
                'confidence': 0.1
            })

        # Sort by confidence (most confident first)
        patterns.sort(key=lambda p: p.get('confidence', 0), reverse=True)

        # Keep top 50 patterns
        if len(patterns) > 50:
            patterns[:] = patterns[:50]

    # ─── FORESIGHT LAYER ────────────────────────────────────────────

    def foresee(self):
        """
        Analyze current state and learned patterns to generate foresight
        insights — predictions of what will go wrong and when.
        Returns a list of insights with risk scores and recommended actions.
        """
        state = read_json(STATE_FILE, {})
        timing = state.get('timing_metrics', {})
        patterns = self.memory['learned_patterns']
        insights = []

        # Get current metrics
        eef = timing.get('execution_emulation_factor', 1.0)
        timeout_prox = timing.get('timeout_proximity', 0)
        rolling_avg = timing.get('rolling_avg_ms', 0)
        context_pct = state.get('context_usage_pct', 0)
        recent_failures = timing.get('recent_failures', 0)
        tool_calls = state.get('tool_call_count', 0)
        thresholds = self.memory['thresholds']

        # Foresight 1: EEF Trajectory Analysis
        eef_pattern = self._find_pattern('high_eef_with_timeout_risk')
        eef_trend = self._analyze_trend('execution_emulation_factor')
        if eef_pattern and eef_trend.get('direction', 'stable') == 'rising':
            projected_eef = eef_trend.get('projected_value', eef)
            if projected_eef > thresholds.get('eef_critical', 2.5):
                insights.append({
                    'type': 'EEF_TRAJECTORY_CRITICAL',
                    'risk': 90,
                    'current': eef,
                    'projected': projected_eef,
                    'timeframe': 'next 5-10 tool calls',
                    'message': f'EEF trending toward critical ({projected_eef:.1f}). Historical pattern: {eef_pattern["count"]} occurrences.',
                    'action': 'Fragment all operations. Use timeout 30s wrappers. Paginate output.'
                })
            elif projected_eef > thresholds.get('eef_elevated', 1.8):
                insights.append({
                    'type': 'EEF_TRAJECTORY_ELEVATED',
                    'risk': 70,
                    'current': eef,
                    'projected': projected_eef,
                    'timeframe': 'next 5-10 tool calls',
                    'message': f'EEF rising toward elevated ({projected_eef:.1f}).',
                    'action': 'Monitor timing. Consider reducing scope of operations.'
                })

        # Foresight 2: Timeout Risk Prediction
        if timeout_prox >= 60:
            insights.append({
                'type': 'TIMEOUT_RISK_IMMINENT',
                'risk': timeout_prox,
                'current': timeout_prox,
                'projected': min(100, timeout_prox + 10),
                'timeframe': 'next command',
                'message': f'Timeout proximity at {timeout_prox}/100. Commands at risk of timing out.',
                'action': 'Use timeout 30s wrappers. Pipe output through head -50. Break into smaller steps.'
            })

        # Foresight 3: Failure Cascade Prediction
        if recent_failures >= thresholds.get('consecutive_failures_warning', 3):
            cascade_risk = min(95, 50 + recent_failures * 10)
            insights.append({
                'type': 'FAILURE_CASCADE',
                'risk': cascade_risk,
                'current': recent_failures,
                'projected': recent_failures + 2,
                'timeframe': 'immediate',
                'message': f'{recent_failures} recent failures detected. Cascade risk high.',
                'action': 'Run diagnostic: bash /root/NeuralCline/hooks/diagnose.sh. Generate handoff: bash /root/NeuralCline/hooks/generate-handoff.sh'
            })

        # Foresight 4: Context Pressure Warning
        if context_pct >= 60:
            remaining = 100 - context_pct
            calls_to_full = max(5, remaining * 2)  # rough estimate
            insights.append({
                'type': 'CONTEXT_PRESSURE',
                'risk': min(95, context_pct),
                'current': context_pct,
                'projected': min(100, context_pct + 10),
                'timeframe': f'~{calls_to_full} more tool calls',
                'message': f'Context at {context_pct}%. ~{calls_to_full} calls until critical.',
                'action': 'Truncate/paginate output. Save checkpoint. Consider generating handoff.'
            })

        # Foresight 5: Performance Degradation Trend
        perf_pattern = self._find_pattern('degraded_performance')
        if perf_pattern and rolling_avg > 5000:
            insights.append({
                'type': 'PERFORMANCE_DEGRADATION',
                'risk': min(85, int(rolling_avg / 500)),
                'current': rolling_avg,
                'projected': rolling_avg * 1.2,
                'timeframe': 'ongoing',
                'message': f'Rolling avg {rolling_avg}ms indicates degraded performance.',
                'action': 'Check for background processes: ps aux --sort=-%cpu | head -10. Consider resetting timing history.'
            })

        # Foresight 6: Pattern-based prediction using learned patterns
        for pattern in patterns[:3]:
            if pattern.get('confidence', 0) > 0.5 and pattern.get('count', 0) >= 3:
                insights.append({
                    'type': f'LEARNED_PATTERN_{pattern["pattern"].upper()}',
                    'risk': int(pattern['confidence'] * 80),
                    'current': pattern['data'],
                    'projected': pattern['data'],
                    'timeframe': 'based on historical pattern',
                    'message': f'Learned pattern "{pattern["pattern"]}" (x{pattern["count"]}, confidence={pattern["confidence"]:.0%})',
                    'action': 'Pattern recognized. Apply historical mitigation strategy.'
                })

        # Sort insights by risk (highest first)
        insights.sort(key=lambda i: i.get('risk', 0), reverse=True)

        # Store insights for reference
        self.memory['foresight_insights'] = insights[:10]

        # Check if any insight is critical enough to trigger self-healing
        critical_insights = [i for i in insights if i.get('risk', 0) >= 80]
        if critical_insights:
            self._self_heal(critical_insights)

        self.save()
        return insights

    def _find_pattern(self, pattern_name):
        """Find a learned pattern by name."""
        for p in self.memory['learned_patterns']:
            if p['pattern'] == pattern_name:
                return p
        return None

    def _analyze_trend(self, parameter):
        """
        Analyze the trend of a parameter over recent memories.
        Returns direction (rising/falling/stable), slope, and projected value.
        """
        memories = self.memory['memories']
        if len(memories) < 5:
            return {'direction': 'stable', 'slope': 0, 'projected_value': 0}

        # Take last 10 memories (or fewer)
        recent = memories[-10:]
        values = []
        for m in recent:
            val = m.get('parameters', {}).get(parameter, None)
            if val is not None:
                values.append(val)

        if len(values) < 5:
            return {'direction': 'stable', 'slope': 0, 'projected_value': values[-1] if values else 0}

        # Simple linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # Project 5 steps ahead
        projected = values[-1] + slope * 5

        if slope > 0.05 * y_mean:
            direction = 'rising'
        elif slope < -0.05 * y_mean:
            direction = 'falling'
        else:
            direction = 'stable'

        return {
            'direction': direction,
            'slope': round(slope, 4),
            'projected_value': round(projected, 2),
            'current_value': values[-1]
        }

    # ─── SELF-HEALING LAYER ──────────────────────────────────────────

    def _self_heal(self, critical_insights):
        """
        Autonomous self-healing triggered by critical foresight insights.
        Adjusts thresholds, saves checkpoints, and logs healing actions.
        """
        thresholds = self.memory['thresholds']
        healing_actions = self.memory['self_healing_actions']
        now = timestamp()

        for insight in critical_insights:
            action = {
                'timestamp': now,
                'trigger': insight['type'],
                'risk': insight['risk'],
                'actions_taken': []
            }

            # Healing 1: Reduce EEF thresholds if EEF is rising
            if insight['type'] == 'EEF_TRAJECTORY_CRITICAL':
                # Tighten thresholds proactively
                old_eef_critical = thresholds.get('eef_critical', 2.5)
                thresholds['eef_critical'] = max(1.5, old_eef_critical - 0.3)
                thresholds['eef_elevated'] = max(1.0, thresholds.get('eef_elevated', 1.8) - 0.2)
                action['actions_taken'].append(f'Lowered EEF critical threshold from {old_eef_critical} to {thresholds["eef_critical"]}')
                action['actions_taken'].append('Auto-generated checkpoint for safety')

                # Generate checkpoint
                try:
                    import subprocess
                    subprocess.run(['timeout', '10', 'python3',
                                    '/root/NeuralCline/lib/state_engine.py',
                                    'generate_checkpoint'], capture_output=True)
                except:
                    pass

            # Healing 2: Tighten timeout proximity if timeout risk is high
            elif insight['type'] == 'TIMEOUT_RISK_IMMINENT':
                old_danger = thresholds.get('timeout_proximity_danger', 80)
                thresholds['timeout_proximity_danger'] = max(60, old_danger - 10)
                thresholds['timeout_proximity_warning'] = max(40, thresholds.get('timeout_proximity_warning', 60) - 10)
                action['actions_taken'].append(f'Lowered timeout proximity danger from {old_danger} to {thresholds["timeout_proximity_danger"]}')

            # Healing 3: Increase checkpoint frequency if failures are cascading
            elif insight['type'] == 'FAILURE_CASCADE':
                old_interval = thresholds.get('self_heal_interval', 10)
                thresholds['self_heal_interval'] = max(3, old_interval - 2)
                action['actions_taken'].append(f'Increased self-heal frequency from {old_interval} to {thresholds["self_heal_interval"]} calls')
                action['actions_taken'].append('Auto-generated checkpoint')
                try:
                    import subprocess
                    subprocess.run(['timeout', '10', 'python3',
                                    '/root/NeuralCline/lib/state_engine.py',
                                    'generate_checkpoint'], capture_output=True)
                except:
                    pass

            # Healing 4: Suggest context preservation if context is high
            elif insight['type'] == 'CONTEXT_PRESSURE':
                action['actions_taken'].append('Context pressure detected — recommend generating handoff')
                try:
                    import subprocess
                    subprocess.run(['timeout', '10', 'python3',
                                    '/root/NeuralCline/lib/state_engine.py',
                                    'generate_checkpoint'], capture_output=True)
                except:
                    pass

            healing_actions.append(action)

        # Limit healing log to 100 entries
        if len(healing_actions) > 100:
            healing_actions[:] = healing_actions[-100:]

        # Evolve the organism
        self.memory['evolution']['generations'] += 1
        self.memory['evolution']['last_evolved'] = now

        self.save()

    def heal(self, command=None):
        """
        Public self-healing method. Analyzes current state, generates foresight,
        and applies self-healing if needed. Returns healing recommendations.
        """
        # Take a memory snapshot
        self.snapshot()

        # Generate foresight insights
        insights = self.foresee()

        # Check if self-healing should run (based on interval)
        state = read_json(STATE_FILE, {})
        calls = state.get('tool_call_count', 0)
        interval = self.memory['thresholds'].get('self_heal_interval', SELF_HEAL_INTERVAL_CALLS)

        recommendations = []

        # Add recommendations from insights
        for insight in insights[:3]:
            if insight.get('risk', 0) >= 60:
                recommendations.append({
                    'risk': insight['risk'],
                    'message': insight['message'],
                    'action': insight['action']
                })

        # Check if we need to run self-healing
        recent_heals = self.memory['self_healing_actions']
        last_heal_call = 0
        if recent_heals:
            try:
                last_heal = recent_heals[-1]
                # Find the tool call count at last heal
                for m in reversed(self.memory['memories']):
                    if m['timestamp'] == last_heal.get('timestamp'):
                        last_heal_call = m.get('parameters', {}).get('tool_call_count', 0)
                        break
            except:
                pass

        if calls - last_heal_call >= interval:
            # Time for self-healing
            high_risk = [i for i in insights if i.get('risk', 0) >= 80]
            if high_risk:
                self._self_heal(high_risk)
                recommendations.append({
                    'risk': 99,
                    'message': 'SELF-HEALING TRIGGERED: Critical risks detected',
                    'action': 'Check /root/.session-state/session-memory.json for details'
                })

        return recommendations

    # ─── DIAGNOSTIC / REPORTING ──────────────────────────────────────

    def report(self):
        """Generate a comprehensive report of the organism's state."""
        mem = self.memory
        evo = mem.get('evolution', {})
        thresholds = mem.get('thresholds', {})
        patterns = mem.get('learned_patterns', [])
        heals = mem.get('self_healing_actions', [])
        insights = mem.get('foresight_insights', [])

        print(f"═══ Self-Learning Foresight Organism ═══")
        print(f"Organism ID:     {mem.get('organism_id', 'unknown')}")
        print(f"Born:            {mem.get('born', 'unknown')}")
        print(f"Generations:     {evo.get('generations', 1)}")
        print(f"Last Evolved:    {evo.get('last_evolved', 'never')}")
        print(f"Memories:        {len(mem.get('memories', []))}")
        print(f"Learned Patterns: {len(patterns)}")
        print(f"Self-Healings:   {len(heals)}")
        print(f"Active Insights: {len(insights)}")
        print()

        if patterns:
            print(f"─── Top Learned Patterns ───")
            for p in patterns[:5]:
                print(f"  [{p.get('confidence', 0):.0%}] {p['pattern']} (x{p.get('count', 0)})")
                for k, v in list(p.get('data', {}).items())[:3]:
                    print(f"    {k}={v}")
            print()

        if insights:
            print(f"─── Current Foresight Insights ───")
            for i in insights[:5]:
                risk = i.get('risk', 0)
                if risk >= 80:
                    icon = "🔴"
                elif risk >= 60:
                    icon = "🟡"
                else:
                    icon = "🟢"
                print(f"  {icon} [{risk}/100] {i.get('type', '?')}")
                print(f"     {i.get('message', '')}")
                print(f"     → {i.get('action', '')}")
            print()

        if heals:
            print(f"─── Recent Self-Healing Actions ───")
            for h in heals[-3:]:
                print(f"  [{h.get('timestamp', '?')}] {h.get('trigger', '?')} (risk={h.get('risk', 0)})")
                for a in h.get('actions_taken', []):
                    print(f"    → {a}")
            print()

        print(f"─── Active Thresholds ───")
        for key in sorted(thresholds.keys()):
            print(f"  {key}={thresholds[key]}")


# ===================== COMMAND DISPATCH =====================

def cmd_snapshot(args):
    """Take a memory snapshot of current parameters."""
    org = ForesightOrganism()
    snap = org.snapshot()
    print(f"MEMORY_SNAPSHOT_TAKEN timestamp={snap['timestamp']}")
    print(f"PARAMETERS_RECORDED={len(snap['parameters'])}")
    print(f"TOTAL_MEMORIES={len(org.memory['memories'])}")
    print(f"LEARNED_PATTERNS={len(org.memory['learned_patterns'])}")


def cmd_foresee(args):
    """Generate foresight insights and predictions."""
    org = ForesightOrganism()
    insights = org.foresee()
    print(f"FORESIGHT_INSIGHTS={len(insights)}")
    for i, insight in enumerate(insights[:5]):
        print(f"INSIGHT_{i+1}_TYPE={insight.get('type', '?')}")
        print(f"INSIGHT_{i+1}_RISK={insight.get('risk', 0)}")
        print(f"INSIGHT_{i+1}_MESSAGE={insight.get('message', '')}")
        print(f"INSIGHT_{i+1}_ACTION={insight.get('action', '')}")


def cmd_heal(args):
    """Run self-healing: snapshot + foresee + auto-adjust."""
    command = args[0] if len(args) > 0 else ""
    org = ForesightOrganism()
    recommendations = org.heal(command)
    print(f"HEALING_RECOMMENDATIONS={len(recommendations)}")
    for i, rec in enumerate(recommendations):
        print(f"REC_{i+1}_RISK={rec.get('risk', 0)}")
        print(f"REC_{i+1}_MESSAGE={rec.get('message', '')}")
        print(f"REC_{i+1}_ACTION={rec.get('action', '')}")
    print(f"ORGANISM_GENERATION={org.memory['evolution']['generations']}")
    print(f"LEARNED_PATTERNS={len(org.memory['learned_patterns'])}")
    print(f"SELF_HEALINGS={len(org.memory['self_healing_actions'])}")


def cmd_report(args):
    """Print a comprehensive organism report."""
    org = ForesightOrganism()
    org.report()


def cmd_reset_memory(args):
    """Reset the organism's memory (start fresh, but keep knowledge)."""
    keep_patterns = args[0] == '--keep-patterns' if len(args) > 0 else False
    org = ForesightOrganism()
    old_patterns = org.memory.get('learned_patterns', [])
    old_thresholds = org.memory.get('thresholds', {})

    org.memory = {
        'organism_id': org.memory.get('organism_id', org._gen_organism_id()),
        'born': org.memory.get('born', timestamp()),
        'memories': [],
        'learned_patterns': old_patterns if keep_patterns else [],
        'thresholds': old_thresholds,
        'self_healing_actions': [],
        'foresight_insights': [],
        'evolution': {
            'generations': org.memory['evolution']['generations'] + 1,
            'last_evolved': timestamp(),
            'memory_count': 0,
            'pattern_count': len(old_patterns) if keep_patterns else 0,
            'healing_count': 0
        }
    }
    org.save()
    print(f"MEMORY_RESET generaton={org.memory['evolution']['generations']}")
    print(f"PATTERNS_RETAINED={'yes' if keep_patterns else 'no'}")


def cmd_help(args):
    """Print available commands."""
    print("NeuralCline Self-Learning Foresight Engine — Commands:")
    print("  snapshot                  Take a memory snapshot of current parameters")
    print("  foresee                   Generate foresight insights and predictions")
    print("  heal [command]            Run self-healing: snapshot + foresee + auto-adjust")
    print("  report                    Print comprehensive organism report")
    print("  reset_memory [--keep-patterns]  Reset organism memory (optionally keep patterns)")
    print("  help")


COMMANDS = {
    'snapshot': cmd_snapshot,
    'foresee': cmd_foresee,
    'heal': cmd_heal,
    'report': cmd_report,
    'reset_memory': cmd_reset_memory,
    'help': cmd_help,
}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in COMMANDS:
        try:
            COMMANDS[cmd](args)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        cmd_help([])
        sys.exit(1)