#!/usr/bin/env python3
"""Test runner kb_query — 6 requêtes types sur la mini KB fixtures.

Usage :
  python3 run_tests.py [--verbose]

Exit code : 0 si tous les tests passent, 1 sinon.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent.parent.parent / 'skills' / 'obsidian-nav' / 'scripts'
KB_ROOT = Path(__file__).parent
VERBOSE = '--verbose' in sys.argv or '-v' in sys.argv


def run(args: list[str]) -> tuple[int, list[str]]:
    """Run kb_query with given args, return (exit_code, output_lines)."""
    cmd = [sys.executable, str(SCRIPTS / 'kb_query.py'), '--kb-root', str(KB_ROOT)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    return result.returncode, lines


def assert_paths(label: str, lines: list[str], expected: list[str], exact: bool = False):
    """Assert that all expected paths appear in output lines."""
    found = set()
    for line in lines:
        for e in expected:
            if e in line:
                found.add(e)
    missing = set(expected) - found
    if missing:
        print(f"  FAIL [{label}]")
        print(f"       Attendu : {sorted(expected)}")
        print(f"       Manquant : {sorted(missing)}")
        print(f"       Output : {lines}")
        return False
    if exact:
        extra = set()
        for line in lines:
            matched = any(e in line for e in expected)
            if not matched:
                extra.add(line)
        if extra:
            print(f"  FAIL [{label}] — lignes inattendues : {sorted(extra)}")
            return False
    if VERBOSE:
        print(f"  OK   [{label}] → {lines}")
    else:
        print(f"  OK   [{label}]")
    return True


def assert_exit(label: str, code: int, expected: int) -> bool:
    if code != expected:
        print(f"  FAIL [{label}] exit={code} (attendu {expected})")
        return False
    return True


def main():
    passed = 0
    failed = 0

    print(f"KB root : {KB_ROOT}")
    print(f"Scripts : {SCRIPTS}\n")

    # ── Q1 : chantiers actifs ─────────────────────────────────────────────────
    code, lines = run(['--where', 'status:actif,type:chantier', '--format', 'list'])
    ok = assert_exit('Q1-exit', code, 0)
    ok &= assert_paths('Q1', lines,
                       ['01-strategie/chantiers/chantier-alpha.md',
                        '01-strategie/chantiers/chantier-beta.md'])
    # chantier-archivé ne doit pas apparaître
    if any('archivé' in l for l in lines):
        print('  FAIL [Q1] — chantier-archivé présent dans le résultat')
        ok = False
    passed += int(ok); failed += int(not ok)

    # ── Q2 : tag meta-tooling, hors archivé ──────────────────────────────────
    code, lines = run(['--tags', 'meta-tooling', '--exclude-status', 'archivé', '--format', 'list'])
    ok = assert_exit('Q2-exit', code, 0)
    ok &= assert_paths('Q2', lines, ['chantier-alpha.md'], exact=True)
    passed += int(ok); failed += int(not ok)

    # ── Q3 : dépendants de positionnement ────────────────────────────────────
    code, lines = run(['--depends-on', '00-fondations/positionnement', '--format', 'list'])
    ok = assert_exit('Q3-exit', code, 0)
    ok &= assert_paths('Q3', lines,
                       ['chantier-alpha.md', 'chantier-beta.md'])
    passed += int(ok); failed += int(not ok)

    # ── Q4 : orphelins de type article ───────────────────────────────────────
    code, lines = run(['--orphans', '--where', 'type:article', '--format', 'list'])
    ok = assert_exit('Q4-exit', code, 0)
    ok &= assert_paths('Q4', lines,
                       ['article-stale-draft.md', 'article-tag-inconnu.md'])
    passed += int(ok); failed += int(not ok)

    # ── Q5 : tags hors registry ───────────────────────────────────────────────
    code, lines = run(['--tags-missing-registry', '--format', 'list'])
    ok = assert_exit('Q5-exit', code, 0)
    ok &= assert_paths('Q5', lines, ['article-tag-inconnu.md'], exact=True)
    passed += int(ok); failed += int(not ok)

    # ── Q6 : drafts stales (updated < 2026-04-01) ────────────────────────────
    code, lines = run(['--where', 'updated<2026-04-01,status:draft', '--format', 'list'])
    ok = assert_exit('Q6-exit', code, 0)
    ok &= assert_paths('Q6', lines, ['article-stale-draft.md'], exact=True)
    passed += int(ok); failed += int(not ok)

    # ── Q7 : exit 1 sur requête sans résultat ────────────────────────────────
    code, lines = run(['--where', 'status:inexistant', '--format', 'list'])
    ok = assert_exit('Q7-exit1', code, 1)
    passed += int(ok); failed += int(not ok)

    # ── Q8 : exit 2 sur syntaxe DSL invalide ─────────────────────────────────
    code, lines = run(['--where', 'status', '--format', 'list'])
    ok = assert_exit('Q8-exit2', code, 2)
    passed += int(ok); failed += int(not ok)

    # ── Résumé ────────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'─' * 40}")
    print(f"Résultat : {passed}/{total} tests passés", end='')
    if failed:
        print(f" — {failed} ÉCHOUÉ(S)")
        sys.exit(1)
    else:
        print(" ✓")
        sys.exit(0)


if __name__ == '__main__':
    main()
