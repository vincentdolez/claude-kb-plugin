#!/usr/bin/env python3
"""KB Links — Resolve wiki-links [[]] and depends_on, compute backlinks."""

import re
import json
import sys
from pathlib import Path

from kb_meta import find_kb_root, iter_md_files, get_meta

WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')


def _resolve_wikilink(link: str, kb_root: Path) -> str | None:
    """Resolve a wiki-link to a relative path, or None if not found."""
    # Try exact match first
    candidate = kb_root / link
    if candidate.exists():
        return str(candidate.relative_to(kb_root))
    # Try with .md extension
    candidate = kb_root / (link + '.md')
    if candidate.exists():
        return str(candidate.relative_to(kb_root))
    # Try filename match across KB
    target_name = Path(link).name
    if not target_name.endswith('.md'):
        target_name += '.md'
    for fp in iter_md_files(kb_root):
        if fp.name == target_name:
            return str(fp.relative_to(kb_root))
    return None


def resolve_links(filepath, kb_root: Path = None) -> dict:
    """Resolve all links (wiki-links + depends_on) in a file.

    Returns {
        'wikilinks': [{'raw': '...', 'resolved': '...' or None}],
        'depends_on': [{'raw': '...', 'resolved': '...' or None}]
    }
    """
    fp = Path(filepath)
    if kb_root is None:
        kb_root = find_kb_root()
    if not fp.is_absolute():
        fp = kb_root / fp

    result = {'wikilinks': [], 'depends_on': []}

    if not fp.exists():
        return result

    text = fp.read_text(encoding='utf-8')

    # Wiki-links
    for match in WIKILINK_RE.finditer(text):
        raw = match.group(1).strip()
        resolved = _resolve_wikilink(raw, kb_root)
        result['wikilinks'].append({'raw': raw, 'resolved': resolved})

    # depends_on from frontmatter
    meta = get_meta(fp)
    deps = meta.get('depends_on', [])
    if isinstance(deps, str):
        deps = [deps]
    if isinstance(deps, list):
        for dep in deps:
            resolved = _resolve_wikilink(dep, kb_root)
            result['depends_on'].append({'raw': dep, 'resolved': resolved})

    return result


def find_all_links(kb_root: Path) -> dict:
    """Build a map of all outgoing links: {source_path: [target_path, ...]}."""
    links = {}
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        resolved = resolve_links(fp, kb_root)
        targets = set()
        for item in resolved['wikilinks'] + resolved['depends_on']:
            if item['resolved']:
                targets.add(item['resolved'])
        if targets:
            links[rel] = sorted(targets)
    return links


def find_backlinks(kb_root: Path, target: str) -> list:
    """Find all files that reference `target` (via wiki-link or depends_on).

    `target` is a relative path from KB root.
    """
    # Normalize target
    target_path = Path(target)
    if not str(target_path).endswith('.md'):
        target_path = Path(str(target_path) + '.md')
    target_str = str(target_path)
    target_name = target_path.stem  # filename without .md

    backlinks = []
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        if rel == target_str:
            continue
        text = fp.read_text(encoding='utf-8')

        # Check wiki-links
        for match in WIKILINK_RE.finditer(text):
            raw = match.group(1).strip()
            resolved = _resolve_wikilink(raw, kb_root)
            if resolved == target_str:
                backlinks.append({'source': rel, 'type': 'wikilink', 'raw': raw})
                break

        # Check depends_on
        meta = get_meta(fp)
        deps = meta.get('depends_on', [])
        if isinstance(deps, str):
            deps = [deps]
        if isinstance(deps, list):
            for dep in deps:
                resolved = _resolve_wikilink(dep, kb_root)
                if resolved == target_str:
                    backlinks.append({'source': rel, 'type': 'depends_on', 'raw': dep})
                    break

    return backlinks


if __name__ == '__main__':
    kb = find_kb_root()
    if len(sys.argv) > 2 and sys.argv[1] == '--backlinks':
        target = sys.argv[2]
        results = find_backlinks(kb, target)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 2 and sys.argv[1] == '--resolve':
        results = resolve_links(sys.argv[2], kb)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == '--all':
        results = find_all_links(kb)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("Usage: kb_links.py --backlinks <file> | --resolve <file> | --all")
