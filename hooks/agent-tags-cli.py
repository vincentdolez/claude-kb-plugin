#!/usr/bin/env python3
"""
Agent-tags CLI batch mode — classifie des tags inconnus sans appel LLM.

Input  (STDIN)  : JSON {"tags_inconnus": [...], "fichier_source": "...", "titre": "...", "registry_path": "..."}
Output (STDOUT) : JSON {"renames": {}, "maps": {}, "kills": [], "parks": []}

PROMOTE est explicitement interdit ici — seule la skill /tags-promote peut patcher le registry.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path


def load_registry(registry_path: str) -> tuple[set[str], dict[str, str]]:
    """Retourne (tags_valides, retires_map) depuis tags-registry.md."""
    p = Path(registry_path)
    if not p.exists():
        return set(), {}

    content = p.read_text(encoding="utf-8")
    valid_tags: set[str] = set()
    retired_map: dict[str, str] = {}  # ancien_tag -> alternative (vide = kill)

    in_categories = False
    in_retired = False

    for line in content.splitlines():
        if line.startswith("## Catégories"):
            in_categories = True
            in_retired = False
            continue
        if line.startswith("## Tags retirés"):
            in_categories = False
            in_retired = True
            continue
        if line.startswith("## ") and not line.startswith("## Catégories") and not line.startswith("## Tags retirés"):
            in_categories = False
            in_retired = False

        if in_categories:
            for m in re.finditer(r"`([^`]+)`", line):
                valid_tags.add(m.group(1))

        if in_retired:
            # Format: | `ancien` | Raison | `alternative` | ou | `ancien` | Raison | — |
            m = re.match(r"\|\s*`([^`]+)`\s*\|[^|]*\|\s*(?:`([^`]+)`|—)\s*\|", line)
            if m:
                old_tag = m.group(1)
                alt = m.group(2) or ""
                retired_map[old_tag] = alt

    return valid_tags, retired_map


def normalize_tag(tag: str) -> str:
    """Normalise un tag (minuscule, strip) sans toucher aux accents."""
    return tag.strip().lower()


def strip_accents(s: str) -> str:
    """Retire les accents pour comparaison fuzzy."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def classify_tags(
    tags_inconnus: list[str],
    valid_tags: set[str],
    retired_map: dict[str, str],
    file_type: str = "",
    file_status: str = "",
) -> dict:
    """Classifie chaque tag inconnu en rename / map / kill / park."""
    renames: dict[str, str] = {}
    maps: dict[str, str] = {}
    kills: list[str] = []
    parks: list[str] = []

    # Index sans accents pour les renames
    valid_no_accent = {strip_accents(t): t for t in valid_tags}
    retired_no_accent = {strip_accents(t): t for t in retired_map}

    for raw_tag in tags_inconnus:
        tag = normalize_tag(raw_tag)

        # 1. KILL : duplique type ou status du fichier
        if file_type and tag == normalize_tag(file_type):
            kills.append(raw_tag)
            continue
        if file_status and tag == normalize_tag(file_status):
            kills.append(raw_tag)
            continue

        # 2. Déjà valide (ne devrait pas arriver, mais gardons le chemin propre)
        if tag in valid_tags:
            continue

        # 3. RENAME : tag valide sans accent (ex. "securite" -> "sécurité")
        stripped = strip_accents(tag)
        if stripped in valid_no_accent:
            renames[raw_tag] = valid_no_accent[stripped]
            continue

        # 4. MAP / KILL depuis la liste "Tags retirés"
        if tag in retired_map:
            alt = retired_map[tag]
            if alt:
                maps[raw_tag] = alt
            else:
                kills.append(raw_tag)
            continue

        # 4b. "Tags retirés" sans accent
        if stripped in retired_no_accent:
            retired_canonical = retired_no_accent[stripped]
            alt = retired_map[retired_canonical]
            if alt:
                maps[raw_tag] = alt
            else:
                kills.append(raw_tag)
            continue

        # 5. PARK : inconnu et non-mappable mécaniquement
        parks.append(raw_tag)

    return {"renames": renames, "maps": maps, "kills": kills, "parks": parks}


def extract_frontmatter_field(md_path: str, field: str) -> str:
    """Extrait un champ du frontmatter YAML d'un fichier markdown."""
    try:
        content = Path(md_path).read_text(encoding="utf-8")
        if not content.startswith("---"):
            return ""
        end = content.find("---", 3)
        if end == -1:
            return ""
        fm = content[3:end]
        for line in fm.splitlines():
            m = re.match(rf"^{field}:\s*(.+)$", line.strip())
            if m:
                return m.group(1).strip().strip('"').strip("'")
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON invalide: {e}"}), file=sys.stderr)
        sys.exit(1)

    tags_inconnus = data.get("tags_inconnus", [])
    fichier_source = data.get("fichier_source", "")
    registry_path = data.get("registry_path", "00-fondations/tags-registry.md")

    valid_tags, retired_map = load_registry(registry_path)

    file_type = ""
    file_status = ""
    if fichier_source:
        file_type = extract_frontmatter_field(fichier_source, "type")
        file_status = extract_frontmatter_field(fichier_source, "status")

    result = classify_tags(tags_inconnus, valid_tags, retired_map, file_type, file_status)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
