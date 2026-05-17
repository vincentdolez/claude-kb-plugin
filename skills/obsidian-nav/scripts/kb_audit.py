#!/usr/bin/env python3
"""KB Audit — 7-axis structural audit across all layers. Read-only."""

import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from kb_meta import find_kb_root, iter_md_files, get_meta, all_files_meta, stale_drafts
from kb_links import resolve_links, find_all_links, WIKILINK_RE, _extract_target
from kb_graph import find_orphans, detect_cycles, build_graph

REQUIRED_FIELDS = {'title', 'type', 'status', 'created', 'updated'}
# Statuts officiels du CONTRIBUTING.md (cycle de vie KB)
VALID_STATUSES = {
    'backlog', 'exploration', 'draft', 'actif', 'en-pause',
    'terminé', 'publié', 'superseded', 'abandonné', 'archivé',
}
# Tolérés en plus (legacy ou anglais)
KNOWN_STATUSES = VALID_STATUSES | {'completed'}
EXCLUDE_NAMES = {'_index.md', 'CLAUDE.md', 'CONTRIBUTING.md', 'README.md'}
# Dossiers exemptés du check frontmatter (templates avec placeholders,
# documents simulacres du meta-framework).
EXCLUDE_DIR_PATTERNS = (
    '_templates/',
    '/templates/',
    '/phase1/documents/fake/',
    '/phase1/documents/',
)
# Préfixes de fichier exemptés (simulacres meta-framework cases).
EXCLUDE_FILE_PREFIXES = (
    'mail-', 'relances-', 'extrait-', 'excel-', 'fiche-',
    'facture-', 'arborescence-', 'carnet-',
)


def _is_excluded_for_frontmatter(rel_path: str, file_name: str) -> bool:
    """Return True if a file is exempt from the frontmatter check."""
    rel_norm = '/' + rel_path.replace('\\', '/')
    for pat in EXCLUDE_DIR_PATTERNS:
        if pat in rel_norm:
            return True
    for prefix in EXCLUDE_FILE_PREFIXES:
        if file_name.startswith(prefix):
            return True
    return False


def _severity(level: str, msg: str, path: str = None) -> dict:
    entry = {'severity': level, 'message': msg}
    if path:
        entry['path'] = path
    return entry


def audit_broken_links(kb_root: Path) -> list:
    """Axe 1 — Find wiki-links and depends_on pointing to non-existent files."""
    findings = []
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        resolved = resolve_links(fp, kb_root)
        for item in resolved['wikilinks']:
            if item['resolved'] is None:
                findings.append(_severity(
                    'critique',
                    f"Lien wiki cassé [[{item['raw']}]]",
                    rel
                ))
        for item in resolved['depends_on']:
            if item['resolved'] is None:
                findings.append(_severity(
                    'critique',
                    f"depends_on cassé : {item['raw']}",
                    rel
                ))
    return findings


def audit_frontmatter(kb_root: Path) -> list:
    """Axe 2 — Validate frontmatter: required fields, valid status values."""
    findings = []
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        if fp.name in EXCLUDE_NAMES or fp.name.startswith('_template'):
            continue
        if _is_excluded_for_frontmatter(rel, fp.name):
            continue
        meta = get_meta(fp)
        if not meta:
            findings.append(_severity('warning', 'Pas de frontmatter YAML', rel))
            continue
        missing = REQUIRED_FIELDS - set(meta.keys())
        if missing:
            findings.append(_severity(
                'warning',
                f"Champs obligatoires manquants : {', '.join(sorted(missing))}",
                rel
            ))
        status = meta.get('status')
        if status and status not in KNOWN_STATUSES:
            findings.append(_severity(
                'critique',
                f"Statut invalide : '{status}' (attendu : {', '.join(sorted(VALID_STATUSES))})",
                rel
            ))
        elif status and status not in VALID_STATUSES:
            # Statut connu mais hors registry officiel (ex: 'completed' anglais)
            findings.append(_severity(
                'info',
                f"Statut non-officiel mais toléré : '{status}'",
                rel
            ))
    return findings


def audit_stale_drafts(kb_root: Path, days: int = 30) -> list:
    """Axe 3 — Drafts not updated in more than `days` days."""
    findings = []
    for entry in stale_drafts(kb_root, days):
        d = entry.get('days_stale', '?')
        sev = entry.get('severity', 'warning')
        findings.append(_severity(
            sev,
            f"Draft stale ({d} jours sans mise à jour)",
            entry['path']
        ))
    return findings


def audit_depends_on_coherence(kb_root: Path) -> list:
    """Axe 4 — depends_on targets must exist AND be actif."""
    findings = []
    meta_cache = {e['path']: e for e in all_files_meta(kb_root)}

    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        meta = get_meta(fp)
        deps = meta.get('depends_on', [])
        if isinstance(deps, str):
            deps = [deps]
        if not isinstance(deps, list):
            continue
        for dep in deps:
            # Resolve
            resolved = resolve_links(fp, kb_root)
            for item in resolved['depends_on']:
                if item['raw'] != dep:
                    continue
                if item['resolved'] is None:
                    # Already caught by audit_broken_links
                    break
                target_meta = meta_cache.get(item['resolved'], {})
                target_status = target_meta.get('status')
                if target_status == 'draft':
                    findings.append(_severity(
                        'warning',
                        f"depends_on pointe vers un draft : {item['resolved']}",
                        rel
                    ))
                elif target_status == 'archivé':
                    findings.append(_severity(
                        'warning',
                        f"depends_on pointe vers un fichier archivé : {item['resolved']}",
                        rel
                    ))
                break
    return findings


def audit_index_sync(kb_root: Path) -> list:
    """Axe 5 — Check _index.md lists match actual files on disk."""
    findings = []
    for fp in iter_md_files(kb_root):
        if fp.name != '_index.md':
            continue
        rel = str(fp.relative_to(kb_root))
        parent_dir = fp.parent
        text = fp.read_text(encoding='utf-8')

        # Find all wiki-links in the index
        referenced = set()
        for match in WIKILINK_RE.finditer(text):
            raw = _extract_target(match.group(1))
            referenced.add(raw)

        # Find actual .md files in the same directory (non-recursive, exclude _index.md)
        actual_files = set()
        for child in parent_dir.iterdir():
            if child.is_file() and child.suffix == '.md' and child.name != '_index.md':
                # Build the relative path as it would appear in a wiki-link
                child_rel = str(child.relative_to(kb_root))
                child_noext = child_rel.rsplit('.md', 1)[0]
                actual_files.add(child_noext)

        # Also check subdirectories (their _index.md or README.md)
        for child in parent_dir.iterdir():
            if child.is_dir() and not child.name.startswith('.'):
                sub_index = child / '_index.md'
                sub_readme = child / 'README.md'
                if sub_index.exists():
                    child_rel = str(sub_index.relative_to(kb_root)).rsplit('.md', 1)[0]
                    actual_files.add(child_rel)
                elif sub_readme.exists():
                    child_rel = str(sub_readme.relative_to(kb_root)).rsplit('.md', 1)[0]
                    actual_files.add(child_rel)

        # Files on disk but not referenced in index
        for actual in actual_files:
            found = False
            for ref in referenced:
                if ref == actual or ref.endswith('/' + Path(actual).name) or actual.endswith(ref):
                    found = True
                    break
            if not found:
                findings.append(_severity(
                    'info',
                    f"Fichier non référencé dans l'index : {actual}.md",
                    rel
                ))

    return findings


def audit_orphans(kb_root: Path) -> list:
    """Axe 6 — Files with no incoming reference."""
    findings = []
    orphans = find_orphans(kb_root)
    for o in orphans:
        findings.append(_severity('info', 'Fichier orphelin (aucune référence entrante)', o))
    return findings


def audit_status_coherence(kb_root: Path) -> list:
    """Axe 7 — Status inconsistencies."""
    findings = []
    meta_cache = {e['path']: e for e in all_files_meta(kb_root)}

    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        meta = get_meta(fp)
        status = meta.get('status')
        ftype = meta.get('type')

        # Chantier terminé with unchecked tasks
        if ftype == 'chantier' and status in ('terminé', 'completed'):
            text = fp.read_text(encoding='utf-8')
            unchecked = text.count('- [ ]')
            if unchecked > 0:
                findings.append(_severity(
                    'warning',
                    f"Chantier terminé avec {unchecked} tâche(s) non cochée(s)",
                    rel
                ))

        # Actif file depending on draft
        if status == 'actif':
            deps = meta.get('depends_on', [])
            if isinstance(deps, str):
                deps = [deps]
            if isinstance(deps, list):
                resolved = resolve_links(fp, kb_root)
                for item in resolved['depends_on']:
                    if item['resolved']:
                        target = meta_cache.get(item['resolved'], {})
                        if target.get('status') == 'draft':
                            findings.append(_severity(
                                'warning',
                                f"Fichier actif dépend d'un draft : {item['resolved']}",
                                rel
                            ))

    return findings


def run_full_audit(kb_root: Path, days: int = 30) -> dict:
    """Run all 7 audit axes. Returns structured report."""
    axes = {
        '1-liens-cassés': audit_broken_links(kb_root),
        '2-frontmatter': audit_frontmatter(kb_root),
        '3-drafts-stale': audit_stale_drafts(kb_root, days),
        '4-depends-on': audit_depends_on_coherence(kb_root),
        '5-index-sync': audit_index_sync(kb_root),
        '6-orphelins': audit_orphans(kb_root),
        '7-statut': audit_status_coherence(kb_root),
    }

    # Flatten and count
    all_findings = []
    for axis, findings in axes.items():
        for f in findings:
            f['axis'] = axis
            all_findings.append(f)

    counts = {'critique': 0, 'warning': 0, 'info': 0}
    for f in all_findings:
        counts[f['severity']] = counts.get(f['severity'], 0) + 1

    return {'counts': counts, 'axes': axes, 'all': all_findings}


def format_report(report: dict) -> str:
    """Format audit report as markdown."""
    today = datetime.now().strftime('%Y-%m-%d')
    counts = report['counts']
    lines = [
        f"# Rapport d'audit KB — {today}",
        "",
        "## Résumé",
        f"- Critique : {counts.get('critique', 0)}",
        f"- Warning : {counts.get('warning', 0)}",
        f"- Info : {counts.get('info', 0)}",
        "",
    ]

    for level in ('critique', 'warning', 'info'):
        items = [f for f in report['all'] if f['severity'] == level]
        if not items:
            continue
        lines.append(f"## {level.capitalize()}")
        lines.append("")
        for item in items:
            path = item.get('path', '')
            axis = item.get('axis', '')
            lines.append(f"- [{axis}] {item['message']} — `{path}`")
        lines.append("")

    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    kb = find_kb_root()
    days = 30
    if '--days' in sys.argv:
        idx = sys.argv.index('--days')
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    report = run_full_audit(kb, days)
    print(format_report(report))
