#!/usr/bin/env python3
"""KB Report — Unified CLI for KB navigation: query, backlinks, graph, stats."""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

from kb_meta import find_kb_root, all_files_meta, query_files, stale_drafts, iter_md_files
from kb_links import find_backlinks
from kb_graph import build_graph, get_upstream, get_downstream, detect_cycles, find_orphans
from kb_audit import run_full_audit, format_report


def cmd_query(kb_root: Path, filters: list[str]):
    """Query files by metadata filters (key=value)."""
    parsed = {}
    for f in filters:
        if '=' not in f:
            print(f"Invalid filter: {f} (expected key=value)", file=sys.stderr)
            sys.exit(1)
        k, v = f.split('=', 1)
        parsed[k] = v
    results = query_files(kb_root, parsed)
    if not results:
        print("No matching files.")
        return
    for r in results:
        status = r.get('status', '?')
        title = r.get('title', r['path'])
        print(f"  [{status}] {r['path']}  — {title}")


def cmd_backlinks(kb_root: Path, target: str):
    """Show all files referencing the target."""
    results = find_backlinks(kb_root, target)
    if not results:
        print(f"No backlinks found for {target}")
        return
    print(f"Backlinks for {target} ({len(results)}):")
    for r in results:
        print(f"  [{r['type']}] {r['source']}  (ref: {r['raw']})")


def cmd_graph(kb_root: Path, filepath: str, direction: str):
    """Show dependency graph for a file."""
    graph = build_graph(kb_root)
    if direction in ('both', 'upstream'):
        up = get_upstream(graph, filepath)
        print(f"Upstream ({len(up)} files depend on {filepath}):")
        for f in up:
            print(f"  ← {f}")
    if direction in ('both', 'downstream'):
        down = get_downstream(graph, filepath)
        print(f"Downstream ({filepath} depends on {len(down)} files):")
        for f in down:
            print(f"  → {f}")
    # Check for cycles
    cycles = detect_cycles(graph)
    if cycles:
        print(f"\n⚠ {len(cycles)} cycle(s) detected in graph:")
        for c in cycles:
            print(f"  {' → '.join(c)}")


def cmd_stats(kb_root: Path):
    """Global KB stats per layer."""
    all_meta = all_files_meta(kb_root)
    total = len(all_meta)

    # Per layer
    layers = Counter()
    statuses = Counter()
    types = Counter()
    no_frontmatter = []

    for entry in all_meta:
        path = entry['path']
        layer = path.split('/')[0] if '/' in path else 'root'
        layers[layer] += 1
        s = entry.get('status')
        if s:
            statuses[s] += 1
        else:
            no_frontmatter.append(path)
        t = entry.get('type')
        if t:
            types[t] += 1

    print(f"KB Stats — {total} files\n")
    print("By layer:")
    for layer, count in sorted(layers.items()):
        print(f"  {layer}: {count}")
    print(f"\nBy status:")
    for s, count in sorted(statuses.items()):
        print(f"  {s}: {count}")
    if no_frontmatter:
        print(f"  (no status): {len(no_frontmatter)}")
    print(f"\nBy type:")
    for t, count in sorted(types.items()):
        print(f"  {t}: {count}")


def cmd_orphans(kb_root: Path):
    """Find orphan files with no incoming references."""
    orphans = find_orphans(kb_root)
    if not orphans:
        print("No orphan files found.")
        return
    print(f"Orphan files ({len(orphans)}):")
    for o in orphans:
        print(f"  {o}")


def cmd_stale(kb_root: Path, days: int):
    """Find stale draft files."""
    results = stale_drafts(kb_root, days)
    if not results:
        print(f"No stale drafts (>{days} days).")
        return
    print(f"Stale drafts (>{days} days) — {len(results)} files:")
    for r in results:
        sev = r.get('severity', '?')
        stale = r.get('days_stale', '?')
        print(f"  [{sev}] {r['path']}  — {stale} days")


def main():
    parser = argparse.ArgumentParser(description='KB Navigation — query, backlinks, graph, stats')
    parser.add_argument('--query', action='append', help='Filter by key=value (repeatable)')
    parser.add_argument('--backlinks', metavar='FILE', help='Find files referencing FILE')
    parser.add_argument('--graph', metavar='FILE', help='Show dependency graph for FILE')
    parser.add_argument('--direction', choices=['upstream', 'downstream', 'both'], default='both',
                        help='Graph direction (default: both)')
    parser.add_argument('--stats', action='store_true', help='Global KB stats')
    parser.add_argument('--orphans', action='store_true', help='Find orphan files')
    parser.add_argument('--stale', action='store_true', help='Find stale draft files')
    parser.add_argument('--days', type=int, default=30, help='Stale threshold in days (default: 30)')
    parser.add_argument('--audit', action='store_true', help='Full 7-axis KB audit')
    parser.add_argument('--kb-root', help='KB root directory (auto-detected if omitted)')

    args = parser.parse_args()
    kb_root = Path(args.kb_root) if args.kb_root else find_kb_root()

    if not (kb_root / 'CLAUDE.md').exists():
        print(f"Warning: {kb_root} does not look like a KB root (no CLAUDE.md)", file=sys.stderr)

    if args.audit:
        report = run_full_audit(kb_root, args.days)
        print(format_report(report))
    elif args.query:
        cmd_query(kb_root, args.query)
    elif args.backlinks:
        cmd_backlinks(kb_root, args.backlinks)
    elif args.graph:
        cmd_graph(kb_root, args.graph, args.direction)
    elif args.stats:
        cmd_stats(kb_root)
    elif args.orphans:
        cmd_orphans(kb_root)
    elif args.stale:
        cmd_stale(kb_root, args.days)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
