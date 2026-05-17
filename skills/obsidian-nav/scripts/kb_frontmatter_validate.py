#!/usr/bin/env python3
"""
kb_frontmatter_validate.py — Validator frontmatter KB

Usage:
  python3 kb_frontmatter_validate.py <file.md> [<file2.md> ...]
  python3 kb_frontmatter_validate.py --glob "*.md"
  python3 kb_frontmatter_validate.py --kb-root /path/to/kb --glob "**/*.md"

Exit codes:
  0 — tous les fichiers valides (ou warnings seulement pour archives/templates)
  1 — violations critiques détectées
"""

import sys
import os
import json
import re
import glob as glob_module
import argparse
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML requis — pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
    from jsonschema import validate, ValidationError, SchemaError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# ── Statuts valides ──────────────────────────────────────────────────────────
VALID_STATUSES = {
    "backlog", "draft", "exploration", "actif",
    "en-pause", "terminé", "publié", "abandonné", "archivé", "superseded"
}

# ── Types officiels ──────────────────────────────────────────────────────────
VALID_TYPES = {
    "fondation", "strategie", "marque", "spec", "ops",
    "decision", "chantier", "contenu", "persona", "rapport",
    "prompt", "template", "journal", "index", "note",
    "technique", "mission", "person", "interview", "recherche",
    "copy", "veille", "buffer", "inbox", "document-simule",
    "demo-script", "simulation"
}

# ── Champs obligatoires base ─────────────────────────────────────────────────
BASE_REQUIRED = ["title", "type", "status", "created", "updated"]

# ── Champs additionnels requis par type ──────────────────────────────────────
TYPE_EXTRA_REQUIRED: dict[str, list[str]] = {
    # Aucun type n'a d'extra obligatoire pour l'instant (on reste minimal)
}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def find_schemas_dir(kb_root: Optional[str] = None, file_path: Optional[str] = None) -> Optional[Path]:
    """Remonte l'arborescence pour trouver 00-fondations/schemas/frontmatter/"""
    search_dirs = []

    if kb_root:
        search_dirs.append(Path(kb_root))

    if file_path:
        p = Path(file_path).resolve()
        while p != p.parent:
            p = p.parent
            if (p / "00-fondations").is_dir():
                search_dirs.append(p)
                break

    # Fallback: chercher depuis le répertoire courant
    p = Path.cwd()
    while p != p.parent:
        if (p / "00-fondations").is_dir():
            search_dirs.append(p)
            break
        p = p.parent

    for root in search_dirs:
        schemas_dir = root / "00-fondations" / "schemas" / "frontmatter"
        if schemas_dir.is_dir():
            return schemas_dir

    return None


def load_schema(type_name: str, schemas_dir: Optional[Path]) -> Optional[dict]:
    """Charge le schema JSON pour un type donné"""
    if schemas_dir is None or not HAS_JSONSCHEMA:
        return None

    schema_file = schemas_dir / f"{type_name}.json"
    if not schema_file.exists():
        return None

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Résoudre la $ref vers _base.json (simplification : merge inline)
    if "allOf" in schema:
        base_file = schemas_dir / "_base.json"
        if base_file.exists():
            with open(base_file, "r", encoding="utf-8") as f:
                base_schema = json.load(f)
            # Inline merge: supprimer $ref et merger les propriétés du base
            merged = {k: v for k, v in base_schema.items() if k not in ("$schema", "$id", "title", "description", "allOf")}
            for item in schema.get("allOf", []):
                if "$ref" not in item:
                    for k, v in item.items():
                        if k == "properties":
                            merged.setdefault("properties", {}).update(v)
                        else:
                            merged[k] = v
            # Merger les propriétés spécifiques du schema type
            for k, v in schema.items():
                if k not in ("allOf", "$ref"):
                    if k == "properties":
                        merged.setdefault("properties", {}).update(v)
                    else:
                        merged[k] = v
            return merged
    return schema


def _normalize_frontmatter(fm: dict) -> dict:
    """Normalise les valeurs frontmatter pour la validation :
    - datetime.date / datetime.datetime → str YYYY-MM-DD
    - autres types gardés tels quels"""
    import datetime
    normalized = {}
    for k, v in fm.items():
        if isinstance(v, datetime.date):
            normalized[k] = v.strftime("%Y-%m-%d")
        elif isinstance(v, datetime.datetime):
            normalized[k] = v.strftime("%Y-%m-%d")
        else:
            normalized[k] = v
    return normalized


def parse_frontmatter(filepath: str) -> tuple[Optional[dict], Optional[str]]:
    """Parse le frontmatter YAML d'un fichier Markdown.
    Retourne (frontmatter_dict, error_message)"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return None, f"Impossible de lire le fichier: {e}"

    if not content.startswith("---"):
        return {}, None  # Pas de frontmatter — sera signalé comme violation

    # Extraire le bloc YAML
    end = content.find("\n---", 3)
    if end == -1:
        return None, "Frontmatter non fermé (--- manquant)"

    yaml_block = content[3:end].strip()

    try:
        fm = yaml.safe_load(yaml_block)
        if fm is None:
            return {}, None
        if not isinstance(fm, dict):
            return None, "Frontmatter n'est pas un objet YAML valide"
        return _normalize_frontmatter(fm), None
    except yaml.YAMLError as e:
        return None, f"Erreur YAML: {e}"


def is_archive_or_template(filepath: str) -> bool:
    """Vérifie si le fichier est dans _archives/ ou _templates/"""
    p = Path(filepath)
    parts = p.parts
    return any(part in ("_archives", "_templates") for part in parts)


class Violation:
    def __init__(self, level: str, field: str, message: str):
        self.level = level  # "critical" | "warning"
        self.field = field
        self.message = message

    def __str__(self):
        icon = "✗" if self.level == "critical" else "⚠"
        return f"  {icon} [{self.field}] {self.message}"


def validate_frontmatter(filepath: str, schemas_dir: Optional[Path]) -> list[Violation]:
    """Valide le frontmatter d'un fichier .md.
    Retourne la liste des violations."""
    violations = []
    is_tolerant = is_archive_or_template(filepath)

    fm, parse_error = parse_frontmatter(filepath)

    if parse_error:
        violations.append(Violation(
            "warning" if is_tolerant else "critical",
            "frontmatter",
            f"Parse error: {parse_error}"
        ))
        return violations

    if not fm:
        if is_tolerant:
            violations.append(Violation("warning", "frontmatter", "Frontmatter absent ou vide (toléré: archive/template)"))
        else:
            violations.append(Violation("critical", "frontmatter", "Frontmatter absent ou vide"))
        return violations

    # ── Champs obligatoires ──────────────────────────────────────────────────
    level = "warning" if is_tolerant else "critical"

    for field in BASE_REQUIRED:
        if field not in fm or fm[field] is None or fm[field] == "":
            violations.append(Violation(level, field, f"Champ obligatoire manquant: `{field}`"))

    # ── Validation type ──────────────────────────────────────────────────────
    type_val = fm.get("type", "")
    if type_val and type_val not in VALID_TYPES:
        violations.append(Violation(level, "type",
            f"Type inconnu: `{type_val}` — valeurs autorisées: {', '.join(sorted(VALID_TYPES))}"))
        type_val = None  # Ne pas continuer la validation schema si type invalide

    # ── Validation status ────────────────────────────────────────────────────
    status_val = fm.get("status", "")
    if status_val and status_val not in VALID_STATUSES:
        violations.append(Violation(level, "status",
            f"Statut inconnu: `{status_val}` — valeurs autorisées: {', '.join(sorted(VALID_STATUSES))}"))

    # ── Validation format dates ──────────────────────────────────────────────
    for date_field in ("created", "updated"):
        val = fm.get(date_field)
        if val is not None:
            if not DATE_PATTERN.match(str(val)):
                violations.append(Violation(level, date_field,
                    f"Format date invalide: `{val}` — attendu YYYY-MM-DD"))

    # ── Validation decision: superseded doit avoir replaced_by ──────────────
    if type_val == "decision" and status_val == "superseded":
        if not fm.get("replaced_by"):
            violations.append(Violation(level, "replaced_by",
                "type: decision + status: superseded requiert le champ `replaced_by`"))

    # ── Champs extra par type ────────────────────────────────────────────────
    extra_required = TYPE_EXTRA_REQUIRED.get(type_val or "", [])
    for field in extra_required:
        if field not in fm or fm[field] is None:
            violations.append(Violation(level, field,
                f"Champ requis pour type `{type_val}`: `{field}`"))

    # ── Validation JSON Schema (si disponible) ───────────────────────────────
    if HAS_JSONSCHEMA and type_val and schemas_dir:
        schema = load_schema(type_val, schemas_dir)
        if schema:
            try:
                validate(instance=fm, schema=schema)
            except ValidationError as e:
                # Éviter les doublons avec les vérifications manuelles ci-dessus
                path = ".".join(str(p) for p in e.absolute_path) or e.validator_value if e.absolute_path else e.validator
                msg = e.message
                # Filtrer les violations déjà reportées
                already_reported = any(str(path) in str(v.field) for v in violations)
                if not already_reported:
                    violations.append(Violation(level, str(path) if e.absolute_path else "schema",
                        f"Schema violation: {msg}"))

    return violations


def main():
    parser = argparse.ArgumentParser(
        description="Validate KB frontmatter against type schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file.md
  %(prog)s 00-fondations/positionnement.md 01-strategie/chantiers/*.md
  %(prog)s --glob "**/*.md" --kb-root /path/to/kb
  %(prog)s --summary
        """
    )
    parser.add_argument("files", nargs="*", help="Fichiers .md à valider")
    parser.add_argument("--glob", help="Pattern glob de fichiers à valider")
    parser.add_argument("--kb-root", help="Racine de la KB (pour localiser les schemas)")
    parser.add_argument("--summary", action="store_true", help="Afficher seulement le résumé")
    parser.add_argument("--warnings-as-errors", action="store_true",
                        help="Traiter les warnings comme des erreurs (exit 1)")

    args = parser.parse_args()

    # Collecter les fichiers
    files_to_check = list(args.files) if args.files else []

    if args.glob:
        kb_root = args.kb_root or os.getcwd()
        pattern = os.path.join(kb_root, args.glob)
        files_to_check.extend(glob_module.glob(pattern, recursive=True))

    if not files_to_check:
        parser.print_help()
        sys.exit(0)

    # Filtrer uniquement .md
    files_to_check = [f for f in files_to_check if f.endswith(".md")]

    if not files_to_check:
        print("Aucun fichier .md trouvé.")
        sys.exit(0)

    # Localiser les schemas
    schemas_dir = find_schemas_dir(
        kb_root=args.kb_root,
        file_path=files_to_check[0] if files_to_check else None
    )

    if not HAS_JSONSCHEMA:
        print("⚠ jsonschema non installé — validation schema JSON désactivée (pip3 install jsonschema)")

    # Valider
    total = 0
    total_violations = 0
    total_warnings = 0
    files_with_critical = []
    files_with_warnings = []

    for filepath in sorted(files_to_check):
        if not os.path.isfile(filepath):
            continue

        total += 1
        violations = validate_frontmatter(filepath, schemas_dir)

        criticals = [v for v in violations if v.level == "critical"]
        warnings = [v for v in violations if v.level == "warning"]

        if criticals:
            files_with_critical.append(filepath)
            total_violations += len(criticals)
        if warnings:
            files_with_warnings.append(filepath)
            total_warnings += len(warnings)

        if not args.summary and violations:
            rel_path = os.path.relpath(filepath, args.kb_root or os.getcwd())
            print(f"\n{'✗' if criticals else '⚠'} {rel_path}")
            for v in violations:
                print(str(v))

    # Résumé
    print(f"\n{'─' * 60}")
    print(f"Fichiers validés : {total}")
    print(f"Violations critiques : {total_violations} ({len(files_with_critical)} fichiers)")
    print(f"Warnings : {total_warnings} ({len(files_with_warnings)} fichiers)")

    if files_with_critical and args.summary:
        print(f"\nFichiers avec violations critiques ({len(files_with_critical)}) :")
        for f in files_with_critical:
            rel = os.path.relpath(f, args.kb_root or os.getcwd())
            print(f"  ✗ {rel}")

    if total_violations == 0 and total_warnings == 0:
        print("✓ Tous les fichiers sont valides.")

    # Exit code
    if total_violations > 0:
        sys.exit(1)
    if args.warnings_as_errors and total_warnings > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
