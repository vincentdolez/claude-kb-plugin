#!/usr/bin/env python3
"""
kb_query — DSL CLI pour interroger la KB (frontmatter YAML + tags + depends_on).

Read-only. Réutilisable depuis hooks, agents en mode batch, skills, audits.
Complète les Obsidian Bases (UI) par une voie scriptable.

Exemples :
  kb_query --where "status:actif,type:chantier" --select "title,priority,updated" --format md
  kb_query --tags "meta-tooling" --exclude-status archivé --format list
  kb_query --depends-on "08-recherche/congruence" --format graph
  kb_query --orphans --exclude "_archives/**" --format table
  kb_query --tags-missing-registry --format json
  kb_query --where "updated<2026-04-01,status:draft" --format table

Filtres --where :
  field:value         égalité (case-insensitive)
  field<YYYY-MM-DD    date antérieure à (ou nombre inférieur)
  field>YYYY-MM-DD    date postérieure à (ou nombre supérieur)
  Plusieurs clauses séparées par virgule = AND

Exit codes :
  0   résultats trouvés
  1   aucun match
  2   erreur syntaxe DSL
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Localisation des modules siblings ────────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from kb_meta import find_kb_root, all_files_meta
from kb_graph import find_orphans
from kb_links import resolve_links


# ── Parser DSL --where ────────────────────────────────────────────────────────

_OP_RE = re.compile(r'^([a-zA-Z_]+)\s*([:><])\s*(.+)$')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _parse_where(expr: str) -> list:
    """Parse --where "field:val,field<date" → [(field, op, value), ...]."""
    clauses = []
    for part in expr.split(','):
        part = part.strip()
        if not part:
            continue
        m = _OP_RE.match(part)
        if not m:
            _die(f"Syntaxe --where invalide : '{part}' (attendu: field:val, field<date, field>date)")
        clauses.append((m.group(1), m.group(2), m.group(3).strip()))
    return clauses


def _match_clause(meta: dict, field: str, op: str, value: str) -> bool:
    fval = meta.get(field)
    if fval is None:
        return False
    if op == ':':
        if isinstance(fval, list):
            return value.lower() in [str(v).lower() for v in fval]
        return str(fval).lower() == value.lower()
    # Comparaison date ou nombre
    if _DATE_RE.match(value):
        try:
            ref = datetime.strptime(value, '%Y-%m-%d')
            fdate = datetime.strptime(str(fval), '%Y-%m-%d')
            return fdate < ref if op == '<' else fdate > ref
        except ValueError:
            return False
    try:
        ref_n = float(value)
        fval_n = float(str(fval))
        return fval_n < ref_n if op == '<' else fval_n > ref_n
    except (ValueError, TypeError):
        return False


def _apply_where(entries: list, clauses: list) -> list:
    return [e for e in entries if all(_match_clause(e, f, op, v) for f, op, v in clauses)]


# ── Filtres ───────────────────────────────────────────────────────────────────

def _filter_tags(entries: list, tags: list) -> list:
    result = []
    for e in entries:
        etags = e.get('tags', [])
        if isinstance(etags, str):
            etags = [etags]
        if all(t in etags for t in tags):
            result.append(e)
    return result


def _filter_depends_on(entries: list, target: str, kb_root: Path) -> list:
    """Garde les fichiers dont depends_on résout vers target."""
    # Normalise en chemin .md
    target_p = Path(target)
    candidate = str(target_p) if str(target_p).endswith('.md') else str(target_p) + '.md'
    result = []
    for e in entries:
        fp = kb_root / e['path']
        resolved = resolve_links(fp, kb_root)
        for item in resolved['depends_on']:
            r = item.get('resolved') or ''
            if r == candidate or r.rstrip('.md') == str(target_p):
                result.append(e)
                break
    return result


def _filter_exclude(entries: list, patterns: list) -> list:
    return [e for e in entries
            if not any(fnmatch.fnmatch(e.get('path', ''), pat) for pat in patterns)]


def _filter_exclude_status(entries: list, statuses: list) -> list:
    low = {s.lower() for s in statuses}
    return [e for e in entries if str(e.get('status', '')).lower() not in low]


# ── Tags missing registry ─────────────────────────────────────────────────────

def _load_registry_tags(kb_root: Path) -> set:
    registry = kb_root / '00-fondations' / 'tags-registry.md'
    if not registry.exists():
        return set()
    text = registry.read_text(encoding='utf-8')
    in_section = False
    tags: set = set()
    for line in text.split('\n'):
        if '## Catégories' in line:
            in_section = True
            continue
        if in_section and '## Tags retirés' in line:
            break
        if in_section:
            for m in re.finditer(r'`([^`]+)`', line):
                tags.add(m.group(1))
    return tags


def _find_tags_missing_registry(kb_root: Path) -> list:
    valid = _load_registry_tags(kb_root)
    result = []
    for e in all_files_meta(kb_root):
        etags = e.get('tags', [])
        if isinstance(etags, str):
            etags = [etags]
        unknown = [t for t in etags if t not in valid]
        if unknown:
            entry = dict(e)
            entry['unknown_tags'] = unknown
            result.append(entry)
    return result


# ── Orphans ───────────────────────────────────────────────────────────────────

def _find_orphans_entries(kb_root: Path, all_entries: list) -> list:
    orphan_paths = set(find_orphans(kb_root))
    return [e for e in all_entries if e.get('path', '') in orphan_paths]


# ── Projection --select ───────────────────────────────────────────────────────

_DEFAULT_COLS = ['path', 'title', 'status', 'type', 'updated']
_PREFERRED_COLS = ['path', 'title', 'status', 'type', 'priority', 'updated', 'tags']


def _detect_cols(entries: list, select: list) -> list:
    if select:
        return select
    if not entries:
        return _DEFAULT_COLS
    key_counts: dict = {}
    for e in entries:
        for k in e:
            key_counts[k] = key_counts.get(k, 0) + 1
    cols = [c for c in _PREFERRED_COLS if c in key_counts or c == 'path']
    threshold = max(1, len(entries) // 2)
    for k, cnt in sorted(key_counts.items(), key=lambda x: -x[1]):
        if k not in cols and cnt >= threshold:
            cols.append(k)
    return cols[:8]


def _project(entries: list, cols: list) -> list:
    return [{k: e.get(k, '') for k in cols} for e in entries]


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_list(entries: list) -> str:
    return '\n'.join(e.get('path', str(e)) for e in entries)


def _fmt_json(entries: list) -> str:
    return json.dumps(entries, indent=2, ensure_ascii=False, default=str)


def _fmt_table(entries: list, cols: list) -> str:
    if not entries:
        return '(aucun résultat)'
    rows = [[str(e.get(c, '')) for c in cols] for e in entries]
    widths = [max(len(c), max((len(r[i]) for r in rows), default=0)) for i, c in enumerate(cols)]
    sep = '+-' + '-+-'.join('-' * w for w in widths) + '-+'
    hdr = '| ' + ' | '.join(c.ljust(w) for c, w in zip(cols, widths)) + ' |'
    lines = [sep, hdr, sep]
    for row in rows:
        lines.append('| ' + ' | '.join(v.ljust(w) for v, w in zip(row, widths)) + ' |')
    lines.append(sep)
    return '\n'.join(lines)


def _fmt_md(entries: list, cols: list) -> str:
    if not entries:
        return '*(aucun résultat)*'
    rows = [[str(e.get(c, '')) for c in cols] for e in entries]
    hdr = '| ' + ' | '.join(cols) + ' |'
    sep = '| ' + ' | '.join('---' for _ in cols) + ' |'
    body = '\n'.join('| ' + ' | '.join(r) + ' |' for r in rows)
    return '\n'.join([hdr, sep, body])


def _fmt_graph(entries: list) -> str:
    """Mermaid flowchart LR — fichiers vers leurs depends_on."""
    def _node_id(path: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '_', path)

    lines = ['flowchart LR']
    seen: set = set()

    for e in entries:
        path = e.get('path', '')
        deps = e.get('depends_on', [])
        if isinstance(deps, str):
            deps = [deps]
        nid = _node_id(path)
        label = e.get('title') or Path(path).stem
        if nid not in seen:
            lines.append(f'  {nid}["{label}"]')
            seen.add(nid)
        if isinstance(deps, list):
            for dep in deps:
                did = _node_id(dep)
                if did not in seen:
                    lines.append(f'  {did}["{Path(dep).stem}"]')
                    seen.add(did)
                lines.append(f'  {nid} --> {did}')

    return '```mermaid\n' + '\n'.join(lines) + '\n```'


def _format_output(entries: list, fmt: str, select: list) -> str:
    cols = _detect_cols(entries, select)
    if fmt == 'json':
        return _fmt_json(entries)
    if fmt == 'list':
        return _fmt_list(entries)
    if fmt == 'md':
        return _fmt_md(_project(entries, cols), cols)
    if fmt == 'graph':
        return _fmt_graph(entries)
    return _fmt_table(_project(entries, cols), cols)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _die(msg: str) -> None:
    print(f"[kb-query] Erreur : {msg}", file=sys.stderr)
    sys.exit(2)


def _default_format() -> str:
    return 'table' if sys.stdout.isatty() else 'json'


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='kb-query',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--where', metavar='EXPR',
                   help='Filtres DSL (ex: "status:actif,type:chantier", "updated<2026-04-01")')
    p.add_argument('--tags', metavar='TAGS',
                   help='Tags requis séparés par virgule (AND) — ex: "meta-tooling,audit"')
    p.add_argument('--depends-on', dest='depends_on', metavar='PATH',
                   help='Fichiers dont depends_on pointe vers ce chemin')
    p.add_argument('--orphans', action='store_true',
                   help='Fichiers sans référence entrante')
    p.add_argument('--tags-missing-registry', dest='tags_missing_registry', action='store_true',
                   help='Fichiers avec des tags absents du registry')
    p.add_argument('--exclude', metavar='GLOB', action='append', default=[],
                   help='Exclure les chemins correspondant au glob (répétable) — ex: "_archives/**"')
    p.add_argument('--exclude-status', dest='exclude_status', metavar='STATUTS',
                   help='Statuts à exclure, séparés par virgule — ex: "archivé,terminé"')
    p.add_argument('--select', metavar='CHAMPS',
                   help='Colonnes à afficher, séparées par virgule — ex: "title,status,updated"')
    p.add_argument('--format', metavar='FORMAT', default=None,
                   choices=['table', 'md', 'json', 'list', 'graph'],
                   help='Format de sortie : table (défaut TTY), json (défaut pipe), md, list, graph (Mermaid)')
    p.add_argument('--kb-root', dest='kb_root', metavar='PATH',
                   help='Racine KB (auto-détectée si absent via CLAUDE.md + 00-fondations/)')
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    fmt = args.format or _default_format()
    select = [c.strip() for c in args.select.split(',')] if args.select else []
    kb_root = Path(args.kb_root).resolve() if args.kb_root else find_kb_root()

    # ── Mode tags-missing-registry ────────────────────────────────────────────
    if args.tags_missing_registry:
        entries = _find_tags_missing_registry(kb_root)
        if args.exclude:
            entries = _filter_exclude(entries, args.exclude)
        if not entries:
            sys.exit(1)
        out_select = select or ['path', 'title', 'status', 'unknown_tags']
        print(_format_output(entries, fmt, out_select))
        sys.exit(0)

    # ── Pipeline standard ─────────────────────────────────────────────────────
    if args.orphans:
        all_entries = all_files_meta(kb_root)
        entries = _find_orphans_entries(kb_root, all_entries)
    else:
        entries = all_files_meta(kb_root)

    if args.where:
        clauses = _parse_where(args.where)
        entries = _apply_where(entries, clauses)

    if args.tags:
        tag_list = [t.strip() for t in args.tags.split(',')]
        entries = _filter_tags(entries, tag_list)

    if args.depends_on:
        entries = _filter_depends_on(entries, args.depends_on, kb_root)

    if args.exclude:
        entries = _filter_exclude(entries, args.exclude)

    if args.exclude_status:
        statuses = [s.strip() for s in args.exclude_status.split(',')]
        entries = _filter_exclude_status(entries, statuses)

    if not entries:
        sys.exit(1)

    print(_format_output(entries, fmt, select))
    sys.exit(0)


if __name__ == '__main__':
    main()
