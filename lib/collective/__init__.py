"""
NeuralCline Collective Compute Organism — P2P Distributed Intelligence
=======================================================================
Purpose: Every node that integrates NeuralCline becomes a peer in a
distributed compute network. The organism learns across ALL machines,
not just one. Crash patterns discovered on one node protect all nodes.

This is the entry point for the collective module.

Usage:
  from lib.collective import CollectiveNode
  node = CollectiveNode()
  node.join_network()
  node.share_pattern(pattern)
"""

from .collective_node import CollectiveNode
from .peer_discovery import PeerDiscovery
from .gossip_protocol import GossipProtocol
from .consensus import ThresholdConsensus
from .privacy import PrivacyLayer

__all__ = [
    'CollectiveNode',
    'PeerDiscovery',
    'GossipProtocol',
    'ThresholdConsensus',
    'PrivacyLayer',
]