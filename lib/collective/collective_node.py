#!/usr/bin/env python3
"""
NeuralCline Collective Node — P2P Distributed Intelligence Core
=======================================================================
Purpose: A peer in the collective compute organism. Each node shares
learned crash patterns with other nodes via a gossip protocol. The
organism as a whole learns faster than any individual node.

Architecture:
  [Node A] ◄──────► [Node B] ◄──────► [Node C]
      │                                      │
      └──────────────────────────────────────┘
                    Gossip Protocol
                        
    Each node:
    1. Runs peer discovery (mDNS or manual config)
    2. Maintains a peer list with health checks
    3. Gossips new patterns to connected peers
    4. Receives patterns and merges into local memory
    5. Computes consensus thresholds from all peers
"""

import os
import sys
import json
import time
import uuid
import socket
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

# ─── Paths ────────────────────────────────────────────────────────
SESSION_DIR = os.environ.get(
    'NEURALCLINE_SESSION_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 'session-state')
)
COLLECTIVE_DIR = os.path.join(SESSION_DIR, 'collective')
os.makedirs(COLLECTIVE_DIR, exist_ok=True)

logger = logging.getLogger('neuralcline.collective')


@dataclass
class Peer:
    """Represents another node in the collective network."""
    node_id: str
    host: str
    port: int
    version: str = '2.0.0'
    confidence: float = 1.0       # Weight for voting (higher = more trusted)
    last_seen: float = 0.0
    is_alive: bool = True
    crash_count: int = 0
    total_recoveries: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'version': self.version,
            'confidence': self.confidence,
            'last_seen': self.last_seen,
            'is_alive': self.is_alive,
            'crash_count': self.crash_count,
            'total_recoveries': self.total_recoveries,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Peer':
        return cls(
            node_id=data['node_id'],
            host=data['host'],
            port=data['port'],
            version=data.get('version', '2.0.0'),
            confidence=data.get('confidence', 1.0),
            last_seen=data.get('last_seen', 0.0),
            is_alive=data.get('is_alive', True),
            crash_count=data.get('crash_count', 0),
            total_recoveries=data.get('total_recoveries', 0),
        )


@dataclass
class CrashPattern:
    """
    An anonymized crash pattern shared between nodes.
    No identifiable data is included — only statistical aggregates.
    """
    pattern_id: str
    crash_type: str               # 'timeout', 'exit_code', 'hang', 'context_overflow'
    context_usage_range: tuple    # (min_pct, max_pct) of context at crash time
    avg_execution_ms: float       # Average execution time before crash
    recovery_success_rate: float  # 0.0–1.0
    recovery_avg_ms: float        # Average recovery time
    source_node_id: str           # Anonymized source
    source_confidence: float      # Confidence weight of source node
    occurrences: int              # How many times this pattern was observed
    first_seen: str
    last_seen: str
    
    def to_dict(self) -> Dict:
        return {
            'pattern_id': self.pattern_id,
            'crash_type': self.crash_type,
            'context_usage_range': list(self.context_usage_range),
            'avg_execution_ms': self.avg_execution_ms,
            'recovery_success_rate': self.recovery_success_rate,
            'recovery_avg_ms': self.recovery_avg_ms,
            'source_node_id': self.source_node_id,
            'source_confidence': self.source_confidence,
            'occurrences': self.occurrences,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
        }


THRESHOLD_KEYS = [
    'crash_proximity_warning',    # Context % at which to warn
    'crash_proximity_critical',   # Context % at which to force checkpoint
    'timeout_threshold_ms',       # Max execution time before timeout
    'recovery_strategy_shift',    # Context % at which to shift recovery strategy
    'checkpoint_interval',        # Tool calls between checkpoints
]


class CollectiveNode:
    """
    A peer in the collective compute organism.
    
    Features:
    - Peer discovery via mDNS or manual config
    - P2P gossip of crash patterns
    - Weighted threshold consensus
    - Privacy layer for anonymized sharing
    - Automatic peer health monitoring
    """
    
    def __init__(self, 
                 host: str = '0.0.0.0', 
                 port: int = 0,
                 node_id: Optional[str] = None,
                 enable_discovery: bool = True):
        self.node_id = node_id or str(uuid.uuid4())[:12]
        self.host = host
        self.port = port
        self.enable_discovery = enable_discovery
        
        self.peers: Dict[str, Peer] = {}
        self.patterns: Dict[str, CrashPattern] = {}
        self.local_thresholds = self._load_local_thresholds()
        self.global_thresholds = dict(self.local_thresholds)
        
        self._lock = threading.Lock()
        self._running = False
        self._gossip_thread = None
        self._health_thread = None
        
        # Load saved state
        self._load_state()
    
    def _load_local_thresholds(self) -> Dict:
        """Load or create default local thresholds."""
        defaults = {
            'crash_proximity_warning': 60.0,
            'crash_proximity_critical': 80.0,
            'timeout_threshold_ms': 60000.0,
            'recovery_strategy_shift': 70.0,
            'checkpoint_interval': 50.0,
        }
        thresh_path = os.path.join(COLLECTIVE_DIR, 'local-thresholds.json')
        try:
            if os.path.exists(thresh_path):
                with open(thresh_path) as f:
                    saved = json.load(f)
                defaults.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
        return defaults
    
    def _save_local_thresholds(self):
        """Persist local thresholds."""
        thresh_path = os.path.join(COLLECTIVE_DIR, 'local-thresholds.json')
        with open(thresh_path, 'w') as f:
            json.dump(self.local_thresholds, f, indent=2)
    
    def _load_state(self):
        """Load saved peers and patterns."""
        # Load peers
        peers_path = os.path.join(COLLECTIVE_DIR, 'known-peers.json')
        try:
            if os.path.exists(peers_path):
                with open(peers_path) as f:
                    peer_data = json.load(f)
                with self._lock:
                    for p in peer_data:
                        peer = Peer.from_dict(p)
                        self.peers[peer.node_id] = peer
        except (json.JSONDecodeError, IOError):
            pass
        
        # Load patterns
        patterns_path = os.path.join(COLLECTIVE_DIR, 'shared-patterns.json')
        try:
            if os.path.exists(patterns_path):
                with open(patterns_path) as f:
                    pattern_data = json.load(f)
                with self._lock:
                    for p in pattern_data:
                        pattern = CrashPattern(**p)
                        self.patterns[pattern.pattern_id] = pattern
        except (json.JSONDecodeError, IOError, TypeError):
            pass
    
    def _save_state(self):
        """Persist current state."""
        with self._lock:
            # Save peers
            peers_path = os.path.join(COLLECTIVE_DIR, 'known-peers.json')
            with open(peers_path, 'w') as f:
                json.dump([p.to_dict() for p in self.peers.values()], f, indent=2)
            
            # Save patterns
            patterns_path = os.path.join(COLLECTIVE_DIR, 'shared-patterns.json')
            with open(patterns_path, 'w') as f:
                json.dump([p.to_dict() for p in self.patterns.values()], f, indent=2)
    
    def add_peer(self, host: str, port: int, node_id: Optional[str] = None) -> str:
        """Manually add a peer to the collective."""
        peer_id = node_id or f"peer-{host}:{port}"
        peer = Peer(
            node_id=peer_id,
            host=host,
            port=port,
            last_seen=time.time(),
            is_alive=True,
        )
        with self._lock:
            self.peers[peer_id] = peer
        self._save_state()
        logger.info(f"Added peer {peer_id} at {host}:{port}")
        return peer_id
    
    def remove_peer(self, node_id: str) -> bool:
        """Remove a peer from the collective."""
        with self._lock:
            if node_id in self.peers:
                del self.peers[node_id]
                self._save_state()
                return True
        return False
    
    def share_pattern(self, pattern: CrashPattern):
        """
        Gossip a learned pattern to all connected peers.
        This is how the collective learns.
        """
        # First, merge into local memory
        with self._lock:
            existing = self.patterns.get(pattern.pattern_id)
            if existing:
                # Update existing pattern
                existing.occurrences += pattern.occurrences
                existing.last_seen = pattern.last_seen
                existing.recovery_success_rate = (
                    existing.recovery_success_rate * 0.7 + 
                    pattern.recovery_success_rate * 0.3
                )
                existing.source_confidence = max(
                    existing.source_confidence, pattern.source_confidence
                )
            else:
                self.patterns[pattern.pattern_id] = pattern
        
        # Then gossip to peers (non-blocking)
        for peer in self.get_alive_peers():
            try:
                self._send_pattern(peer, pattern)
            except Exception as e:
                logger.debug(f"Failed to gossip to {peer.node_id}: {e}")
                self._mark_peer_dead(peer.node_id)
        
        self._save_state()
    
    def receive_pattern(self, pattern_dict: Dict) -> bool:
        """Receive and incorporate a pattern from another node."""
        try:
            pattern = CrashPattern(**pattern_dict)
            with self._lock:
                existing = self.patterns.get(pattern.pattern_id)
                if existing:
                    # Merge with weight from source confidence
                    w = pattern.source_confidence
                    existing.recovery_success_rate = (
                        existing.recovery_success_rate * (1 - w) +
                        pattern.recovery_success_rate * w
                    )
                    existing.occurrences += pattern.occurrences
                    existing.last_seen = pattern.last_seen
                else:
                    self.patterns[pattern.pattern_id] = pattern
            
            self._save_state()
            return True
        except Exception as e:
            logger.error(f"Failed to receive pattern: {e}")
            return False
    
    def get_global_thresholds(self) -> Dict[str, float]:
        """
        Compute consensus thresholds across all known peers.
        Uses weighted average where peer confidence determines weight.
        """
        with self._lock:
            alive_peers = self.get_alive_peers()
            
            if not alive_peers:
                return dict(self.local_thresholds)
            
            # Start with local thresholds
            thresholds = dict(self.local_thresholds)
            
            # Weighted consensus for each threshold key
            for key in THRESHOLD_KEYS:
                values = [self.local_thresholds.get(key, 0)]
                weights = [1.0]  # Local always has weight 1.0
                
                for peer in alive_peers:
                    peer_thresholds = getattr(peer, 'thresholds', None)
                    if peer_thresholds and key in peer_thresholds:
                        values.append(peer_thresholds[key])
                        weights.append(peer.confidence)
                
                # Weighted average
                if values:
                    total_weight = sum(weights)
                    thresholds[key] = sum(
                        v * w for v, w in zip(values, weights)
                    ) / total_weight
            
            self.global_thresholds = thresholds
            return thresholds
    
    def get_alive_peers(self) -> List[Peer]:
        """Return list of currently alive peers."""
        now = time.time()
        return [
            p for p in self.peers.values()
            if p.is_alive and (now - p.last_seen) < 300  # 5 min timeout
        ]
    
    def join_network(self, discovery_port: int = 8765):
        """
        Join the collective network.
        Starts background threads for gossip and health monitoring.
        """
        if self._running:
            logger.warning("Already part of the collective network")
            return
        
        self._running = True
        
        # Start gossip listener
        self._gossip_thread = threading.Thread(
            target=self._gossip_listener,
            daemon=True,
            name='gossip-listener',
        )
        self._gossip_thread.start()
        
        # Start health monitor
        self._health_thread = threading.Thread(
            target=self._health_monitor,
            daemon=True,
            name='health-monitor',
        )
        self._health_thread.start()
        
        logger.info(f"Joined collective network as node {self.node_id}")
    
    def leave_network(self):
        """Leave the collective network gracefully."""
        self._running = False
        if self._gossip_thread:
            self._gossip_thread.join(timeout=5)
        if self._health_thread:
            self._health_thread.join(timeout=5)
        self._save_state()
        logger.info("Left collective network")
    
    def _gossip_listener(self):
        """Background thread that listens for incoming gossip."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        
        try:
            sock.bind((self.host, self.port))
            self.port = sock.getsockname()[1]  # Get actual port
            sock.listen(5)
            logger.info(f"Gossip listener on {self.host}:{self.port}")
        except OSError as e:
            logger.error(f"Failed to bind gossip listener: {e}")
            self._running = False
            return
        
        while self._running:
            try:
                conn, addr = sock.accept()
                conn.settimeout(5.0)
                data = conn.recv(65536)
                if data:
                    try:
                        msg = json.loads(data.decode('utf-8'))
                        self._handle_gossip_message(msg, addr)
                    except json.JSONDecodeError:
                        pass
                conn.close()
            except socket.timeout:
                continue
            except OSError:
                break
        
        sock.close()
    
    def _handle_gossip_message(self, msg: Dict, addr: tuple):
        """Handle an incoming gossip message from a peer."""
        msg_type = msg.get('type')
        
        if msg_type == 'pattern':
            # Received a crash pattern
            self.receive_pattern(msg.get('pattern', {}))
            
            # Update peer status
            peer_id = msg.get('node_id')
            if peer_id and peer_id in self.peers:
                with self._lock:
                    self.peers[peer_id].last_seen = time.time()
                    self.peers[peer_id].is_alive = True
        
        elif msg_type == 'peer_announce':
            # A new peer is announcing itself
            host = msg.get('host', addr[0])
            port = msg.get('port', 0)
            node_id = msg.get('node_id')
            if node_id and host and port:
                self.add_peer(host, port, node_id)
        
        elif msg_type == 'thresholds':
            # Received threshold update from peer
            with self._lock:
                peer_id = msg.get('node_id')
                if peer_id and peer_id in self.peers:
                    self.peers[peer_id].thresholds = msg.get('thresholds', {})
                    self.peers[peer_id].last_seen = time.time()
    
    def _send_pattern(self, peer: Peer, pattern: CrashPattern):
        """Send a pattern to a specific peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((peer.host, peer.port))
            
            msg = json.dumps({
                'type': 'pattern',
                'node_id': self.node_id,
                'pattern': pattern.to_dict(),
            })
            sock.send(msg.encode('utf-8'))
            sock.close()
            
            with self._lock:
                if peer.node_id in self.peers:
                    self.peers[peer.node_id].last_seen = time.time()
                    
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            raise e
    
    def _mark_peer_dead(self, node_id: str):
        """Mark a peer as dead (not reachable)."""
        with self._lock:
            if node_id in self.peers:
                self.peers[node_id].is_alive = False
                self.peers[node_id].confidence *= 0.95  # Decay confidence
    
    def _health_monitor(self):
        """Background thread that checks peer health periodically."""
        while self._running:
            time.sleep(30)  # Check every 30 seconds
            now = time.time()
            
            with self._lock:
                for peer in self.peers.values():
                    if peer.is_alive and (now - peer.last_seen) > 300:
                        # Haven't heard from peer in 5 minutes
                        peer.is_alive = False
                        peer.confidence *= 0.9
                        logger.info(f"Peer {peer.node_id} marked dead (no heartbeat)")
            
            self._save_state()
    
    def get_stats(self) -> Dict:
        """Return collective node statistics."""
        with self._lock:
            alive = self.get_alive_peers()
            return {
                'node_id': self.node_id,
                'port': self.port,
                'total_peers': len(self.peers),
                'alive_peers': len(alive),
                'shared_patterns': len(self.patterns),
                'local_thresholds': self.local_thresholds,
                'global_thresholds': self.global_thresholds,
            }


# ─── CLI Interface ─────────────────────────────────────────────────


def cmd_join(args):
    """Join the collective network."""
    port = int(args[0]) if args else 0
    node = CollectiveNode(port=port)
    node.join_network()
    print(json.dumps({'node_id': node.node_id, 'port': node.port}, indent=2))
    print(f"Joined collective. Start peers with: "
          f"collective_node.py peer {node.host} {node.port}")


def cmd_status(args):
    """Show collective node status."""
    node = CollectiveNode()
    stats = node.get_stats()
    print(json.dumps(stats, indent=2))


def cmd_peer(args):
    """Add a peer manually."""
    if len(args) < 2:
        print("Usage: collective_node.py peer <host> <port> [node_id]")
        return
    host, port = args[0], int(args[1])
    node_id = args[2] if len(args) > 2 else None
    node = CollectiveNode()
    peer_id = node.add_peer(host, port, node_id)
    print(f"Added peer: {peer_id}")


def cmd_patterns(args):
    """List shared patterns."""
    node = CollectiveNode()
    print(json.dumps(
        [p.to_dict() for p in node.patterns.values()],
        indent=2
    ))


def cmd_thresholds(args):
    """Show global consensus thresholds."""
    node = CollectiveNode()
    global_t = node.get_global_thresholds()
    print("Global Consensus Thresholds:")
    for key, val in global_t.items():
        local = node.local_thresholds.get(key, '?')
        print(f"  {key}: {val:.1f} (local: {local})")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        'join': cmd_join,
        'status': cmd_status,
        'peer': cmd_peer,
        'patterns': cmd_patterns,
        'thresholds': cmd_thresholds,
    }
    
    if command in commands:
        commands[command](args)
    else:
        print(f"Unknown: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()