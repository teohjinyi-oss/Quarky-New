"""
Memory v2: Graph Store (Tier 3)

NetworkX-backed knowledge graph for relationship storage and reasoning.
Nodes are concepts/entities, edges are relationships.

Features:
- Relationship storage (A --[relation]--> B)
- Path finding for multi-hop reasoning
- Neighborhood queries (what's related to X?)
- Persistence via GML format
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    nx = None  # type: ignore[assignment]
    _NX_AVAILABLE = False


class GraphStore:
    """
    Tier 3: NetworkX knowledge graph for relationships and reasoning.
    Falls back to a simple dict-of-sets if NetworkX is unavailable.
    """

    def __init__(
        self,
        persist_path: Path | None = None,
        max_nodes: int = 100000,
    ):
        self._path = persist_path
        self._max_nodes = max_nodes
        self._lock = threading.Lock()

        if _NX_AVAILABLE:
            self._graph: nx.DiGraph = nx.DiGraph()  # type: ignore[name-defined]
            if self._path and self._path.exists():
                self._load()
        else:
            # Fallback: adjacency dict
            self._adj: dict[str, dict[str, list[str]]] = {}  # node → {neighbor → [relations]}

    def add_node(self, node_id: str, **attrs) -> None:
        """Add a concept/entity node."""
        with self._lock:
            if _NX_AVAILABLE:
                self._graph.add_node(node_id, **attrs, updated=time.time())
            else:
                if node_id not in self._adj:
                    self._adj[node_id] = {}

    def add_edge(self, source: str, target: str, relation: str, **attrs) -> None:
        """Add a relationship edge between two nodes."""
        with self._lock:
            if _NX_AVAILABLE:
                # Ensure nodes exist
                if source not in self._graph:
                    self._graph.add_node(source, updated=time.time())
                if target not in self._graph:
                    self._graph.add_node(target, updated=time.time())
                self._graph.add_edge(source, target, relation=relation, **attrs, created=time.time())
            else:
                if source not in self._adj:
                    self._adj[source] = {}
                if target not in self._adj[source]:
                    self._adj[source][target] = []
                self._adj[source][target].append(relation)

    def get_neighbors(self, node_id: str, depth: int = 1) -> list[tuple[str, str, dict]]:
        """
        Get neighbors up to N hops from a node.
        Returns list of (neighbor_id, relation, edge_attrs).
        """
        with self._lock:
            if _NX_AVAILABLE:
                if node_id not in self._graph:
                    return []
                result = []
                visited = {node_id}
                frontier = [node_id]
                for _ in range(depth):
                    next_frontier = []
                    for current in frontier:
                        for _, target, data in self._graph.out_edges(current, data=True):
                            if target not in visited:
                                visited.add(target)
                                result.append((target, data.get("relation", ""), data))
                                next_frontier.append(target)
                        for source, _, data in self._graph.in_edges(current, data=True):
                            if source not in visited:
                                visited.add(source)
                                result.append((source, data.get("relation", ""), data))
                                next_frontier.append(source)
                    frontier = next_frontier
                    if not frontier:
                        break
                return result
            else:
                result = []
                for neighbor, relations in self._adj.get(node_id, {}).items():
                    for rel in relations:
                        result.append((neighbor, rel, {}))
                return result

    def infer(self, source: str, target: str) -> list[str]:
        """
        Infer a relationship path between source and target.
        Returns a list of readable relationship descriptions along the path,
        e.g. ["Python is_a language", "language used_for programming"].
        """
        if not _NX_AVAILABLE:
            return []
        with self._lock:
            if source not in self._graph or target not in self._graph:
                return []
            try:
                path = nx.shortest_path(self._graph, source, target)
            except nx.NetworkXNoPath:
                return []
            if len(path) < 2:
                return []
            descriptions = []
            for i in range(len(path) - 1):
                edge_data = self._graph.get_edge_data(path[i], path[i + 1])
                if edge_data:
                    rel = edge_data.get("relation", "related_to")
                    descriptions.append(f"{path[i]} {rel} {path[i + 1]}")
            return descriptions

    def find_path(self, source: str, target: str, max_length: int = 5) -> list[str]:
        """
        Find shortest path between two nodes.
        Returns list of node IDs, or empty list if no path.
        """
        if not _NX_AVAILABLE:
            return []

        with self._lock:
            if source not in self._graph or target not in self._graph:
                return []
            try:
                return list(nx.shortest_path(  # type: ignore[union-attr]
                    self._graph, source, target
                ))[:max_length]
            except nx.NetworkXNoPath:  # type: ignore[union-attr]
                return []

    def search_nodes(self, query: str, top_k: int = 10) -> list[str]:
        """Find nodes whose ID or label contains the query."""
        query_lower = query.lower()
        with self._lock:
            if _NX_AVAILABLE:
                matches = [
                    n for n in self._graph.nodes()
                    if query_lower in str(n).lower()
                ]
            else:
                matches = [n for n in self._adj if query_lower in n.lower()]
        return matches[:top_k]

    def get_related(self, node_id: str, relation: str) -> list[str]:
        """Get all nodes connected by a specific relation type."""
        with self._lock:
            if _NX_AVAILABLE:
                result = []
                for _, target, data in self._graph.out_edges(node_id, data=True):
                    if data.get("relation") == relation:
                        result.append(target)
                return result
            else:
                result = []
                for neighbor, relations in self._adj.get(node_id, {}).items():
                    if relation in relations:
                        result.append(neighbor)
                return result

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges."""
        with self._lock:
            if _NX_AVAILABLE:
                if node_id in self._graph:
                    self._graph.remove_node(node_id)
            else:
                self._adj.pop(node_id, None)
                for neighbors in self._adj.values():
                    neighbors.pop(node_id, None)

    @property
    def node_count(self) -> int:
        if _NX_AVAILABLE:
            return self._graph.number_of_nodes()
        return len(self._adj)

    @property
    def edge_count(self) -> int:
        if _NX_AVAILABLE:
            return self._graph.number_of_edges()
        return sum(len(rels) for neighbors in self._adj.values() for rels in neighbors.values())

    # ── Persistence ─────────────────────────────────────────

    def save(self) -> None:
        """Persist graph to GML file."""
        if not self._path or not _NX_AVAILABLE:
            return

        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            nx.write_gml(self._graph, str(self._path))  # type: ignore[union-attr]

    def _load(self) -> None:
        """Load graph from GML file."""
        if not self._path or not self._path.exists() or not _NX_AVAILABLE:
            return
        try:
            self._graph = nx.read_gml(str(self._path))  # type: ignore[union-attr]
        except Exception:
            self._graph = nx.DiGraph()  # type: ignore[union-attr]

    def clear(self) -> None:
        """Clear the graph."""
        with self._lock:
            if _NX_AVAILABLE:
                self._graph.clear()
            else:
                self._adj.clear()
