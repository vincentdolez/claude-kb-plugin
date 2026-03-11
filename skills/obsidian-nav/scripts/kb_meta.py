#!/usr/bin/env python3
"""KB Metadata — Parse frontmatter YAML, query files by metadata fields."""

import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime

FM_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)

EXCLUDE_DIRS = {'.claude', '.git', 'node_modules', '.obsidian'}


def _parse_yaml_value(raw: str):
    """Parse a single YAML value (string, list, bool, number)."""
    raw = raw.strip()
    if raw.startswith('[') and raw.endswith(']'):
        items = raw[1:-1].split(',')
        return [i.strip().strip('"').strip("'") for i in items if i.strip()]
    if raw.lower() in ('true', 'yes'):
        return True
    if raw.lower() in ('false', 'no'):
        return False
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    return raw


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter from markdown text."""
    m = FM_RE.match(text)
    if not m:
        return {}
    meta = {}
    current_key = None
    current_list = None
    for line in m.group(1).split('\n'):
        if line.startswith('  - ') and current_key:
            if current_list is None:
                current_list = []
            current_list.append(line.strip()[2:].strip().strip('"').strip("'"))
            continue
        if current_list is not None and current_key:
            meta[current_key] = current_list
            current_list = None
            current_key = None
        if ':' not in line:
            continue
        key, _, val = line.partition(':')
        key = key.strip()
        val = val.strip()
        if not key or key.startswith('#'):
            continue
        if val == '' or val == '|' or val == '>':
            current_key = key
            current_list = None
            continue
        meta[key] = _parse_yaml_value(val)
        current_key = None
    if current_list is not None and current_key:
        meta[current_key] = current_list
    return meta


def find_kb_root(start: str = None) -> Path:
    """Find KB root by looking for CLAUDE.md + 00-fondations/ upward."""
    p = Path(start) if start else Path.cwd()
    for d in [p] + list(p.parents):
        if (d / 'CLAUDE.md').exists() and (d / '00-fondations').exists():
            return d
    return p


def get_meta(filepath) -> dict:
    """Get frontmatter metadata for a single file."""
    p = Path(filepath)
    if not p.exists() or p.suffix != '.md':
        return {}
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        return {}
    return _parse_frontmatter(text)


def iter_md_files(kb_root: Path):
    """Iterate all .md files in the KB (excluding internal dirs)."""
    for dirpath, dirnames, filenames in os.walk(kb_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith('.md'):
                yield Path(dirpath) / f


def all_files_meta(kb_root: Path) -> list:
    """Return list of {path, **meta} for all .md files."""
    results = []
    for fp in iter_md_files(kb_root):
        meta = get_meta(fp)
        rel = str(fp.relative_to(kb_root))
        results.append({'path': rel, **meta})
    return results


def query_files(kb_root: Path, filters: dict) -> list:
    """Query files matching all filters (key=value).

    For list fields (tags, depends_on), check membership.
    For string fields, check equality (case-insensitive).
    """
    all_meta = all_files_meta(kb_root)
    matched = []
    for entry in all_meta:
        ok = True
        for key, val in filters.items():
            file_val = entry.get(key)
            if file_val is None:
                ok = False
                break
            if isinstance(file_val, list):
                if val not in file_val:
                    ok = False
                    break
            elif isinstance(file_val, str):
                if file_val.lower() != val.lower():
                    ok = False
                    break
            else:
                if str(file_val) != val:
                    ok = False
                    break
        if ok:
            matched.append(entry)
    return matched


def stale_drafts(kb_root: Path, days: int = 30) -> list:
    """Find draft files not updated in more than `days` days."""
    today = datetime.now()
    results = []
    for entry in all_files_meta(kb_root):
        if entry.get('status') != 'draft':
            continue
        updated = entry.get('updated')
        if not updated:
            results.append({**entry, 'days_stale': '?', 'severity': 'warning'})
            continue
        try:
            d = datetime.strptime(str(updated), '%Y-%m-%d')
            delta = (today - d).days
            if delta > days:
                sev = 'critique' if delta > 60 else 'warning'
                results.append({**entry, 'days_stale': delta, 'severity': sev})
        except ValueError:
            results.append({**entry, 'days_stale': '?', 'severity': 'warning'})
    return results


if __name__ == '__main__':
    kb = find_kb_root()
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        print(json.dumps(all_files_meta(kb), indent=2, ensure_ascii=False, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == '--stale':
        d = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        print(json.dumps(stale_drafts(kb, d), indent=2, ensure_ascii=False, default=str))
    else:
        print(f"KB root: {kb}")
        print(f"Total .md files: {len(list(iter_md_files(kb)))}")
