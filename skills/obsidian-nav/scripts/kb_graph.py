#!/usr/bin/env python3
"""KB Graph — Dependency graph from depends_on + wiki-links. Cycles, upstream/downstream."""

import json
import sys
from pathlib import Path
from collections import defaultdict

from kb_meta import find_kb_root, iter_md_files, get_meta
from kb_links import find_all_links, WIKILINK_RE


def build_graph(kb_root: Path) -> dict:
    """Build adjacency lists: {node: [dependency_targets]}.

    Returns {'downstream': {A: [B, C]}, 'upstream': {B: [A], C: [A]}}
    where A depends on B means A -> B in downstream.
    """
    all_links = find_all_links(kb_root)
    downstream = defaultdict(list)  # file -> files it links to
    upstream = defaultdict(list)    # file -> files that link to it

    for source, targets in all_links.items():
        downstream[source] = targets
        for t in targets:
            upstream[t].append(source)

    return {
        'downstream': dict(downstream),
        'upstream': dict(upstream),
    }


def get_upstream(graph: dict, filepath: str, visited: set = None) -> list:
    """Get all files that (transitively) depend on filepath."""
    if visited is None:
        visited = set()
    if filepath in visited:
        return []
    visited.add(filepath)
    direct = graph.get('upstream', {}).get(filepath, [])
    result = list(direct)
    for dep in direct:
        result.extend(get_upstream(graph, dep, visited))
    return sorted(set(result))


def get_downstream(graph: dict, filepath: str, visited: set = None) -> list:
    """Get all files that filepath (transitively) depends on."""
    if visited is None:
        visited = set()
    if filepath in visited:
        return []
    visited.add(filepath)
    direct = graph.get('downstream', {}).get(filepath, [])
    result = list(direct)
    for dep in direct:
        result.extend(get_downstream(graph, dep, visited))
    return sorted(set(result))


def detect_cycles(graph: dict) -> list:
    """Detect cycles in the dependency graph. Returns list of cycles."""
    downstream = graph.get('downstream', {})
    all_nodes = set(downstream.keys())
    for targets in downstream.values():
        all_nodes.update(targets)

    visited = set()
    rec_stack = set()
    cycles = []

    def _dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in downstream.get(node, []):
            if neighbor not in visited:
                _dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
        path.pop()
        rec_stack.discard(node)

    for node in all_nodes:
        if node not in visited:
            _dfs(node, [])

    return cycles


def find_orphans(kb_root: Path) -> list:
    """Find .md files with no incoming references (not linked by any other file).

    Excludes: _index.md, CLAUDE.md, CONTRIBUTING.md, README.md
    """
    exclude_names = {'_index.md', 'CLAUDE.md', 'CONTRIBUTING.md', 'README.md'}
    graph = build_graph(kb_root)
    upstream = graph.get('upstream', {})

    # All files in KB
    all_files = set()
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        if fp.name not in exclude_names:
            all_files.add(rel)

    # Files with at least one incoming link
    referenced = set(upstream.keys())

    orphans = sorted(all_files - referenced)
    return orphans


if __name__ == '__main__':
    kb = find_kb_root()
    if len(sys.argv) > 2 and sys.argv[1] == '--graph':
        filepath = sys.argv[2]
        direction = 'both'
        if len(sys.argv) > 4 and sys.argv[3] == '--direction':
            direction = sys.argv[4]
        graph = build_graph(kb)
        result = {}
        if direction in ('both', 'upstream'):
            result['upstream'] = get_upstream(graph, filepath)
        if direction in ('both', 'downstream'):
            result['downstream'] = get_downstream(graph, filepath)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == '--cycles':
        graph = build_graph(kb)
        cycles = detect_cycles(graph)
        if cycles:
            print(f"Found {len(cycles)} cycle(s):")
            for c in cycles:
                print(f"  {' -> '.join(c)}")
        else:
            print("No cycles detected.")
    elif len(sys.argv) > 1 and sys.argv[1] == '--orphans':
        orphans = find_orphans(kb)
        print(json.dumps(orphans, indent=2, ensure_ascii=False))
    else:
        print("Usage: kb_graph.py --graph <file> [--direction upstream|downstream|both] | --cycles | --orphans")
