#!/bin/bash
# PreToolUse hook: validate frontmatter quality on Edit|Write of .md files
#
# Architecture : gatekeeper bloquant (exit 2 avec stderr structuré).
#   - Fichier non-.md          → exit 0 (ignore)
#   - Fichier _archives/       → exit 0 (toléré, validé par --warnings-as-errors=false)
#   - Frontmatter valide       → exit 0
#   - Frontmatter invalide     → exit 2 + message stderr structuré avec violations
#
# Pattern identique à hook-tag-validate.sh.
# Délègue à kb_frontmatter_validate.py (dans skills/obsidian-nav/scripts/).
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

# Ne traiter que Edit et Write
if [ "$tool_name" != "Edit" ] && [ "$tool_name" != "Write" ]; then
  exit 0
fi

# Récupérer le chemin du fichier
if [ "$tool_name" = "Edit" ]; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
else
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
fi

# Uniquement les fichiers .md
if [[ "$file_path" != *.md ]]; then
  exit 0
fi

# Localiser le validator Python
HOOKS_DIR="$(dirname "$0")"
PLUGIN_ROOT="$(dirname "$HOOKS_DIR")"
VALIDATOR="$PLUGIN_ROOT/skills/obsidian-nav/scripts/kb_frontmatter_validate.py"

if [ ! -f "$VALIDATOR" ]; then
  # Fallback: chercher dans PATH
  if ! command -v kb_frontmatter_validate.py &>/dev/null; then
    exit 0  # Validator non disponible — laisser passer silencieusement
  fi
  VALIDATOR="kb_frontmatter_validate.py"
fi

if ! command -v python3 &>/dev/null; then
  exit 0  # Python3 non disponible — laisser passer
fi

# Localiser la KB root (remonte jusqu'à trouver 00-fondations/)
KB_ROOT="$file_path"
while [ "$KB_ROOT" != "/" ] && [ ! -d "$KB_ROOT/00-fondations" ]; do
  KB_ROOT=$(dirname "$KB_ROOT")
done

SCHEMAS_DIR=""
if [ -d "$KB_ROOT/00-fondations/schemas/frontmatter" ]; then
  SCHEMAS_DIR="$KB_ROOT/00-fondations/schemas/frontmatter"
fi

# Pour les fichiers en cours d'écriture, le fichier n'existe peut-être pas encore
# sur disque (Write crée, Edit modifie). On valide le new_string directement si possible.
# Stratégie :
#   - Si le fichier existe (Edit) → valider le fichier sur disque
#   - Si le fichier n'existe pas encore (Write) → écrire dans un tmpfile et valider

if [ "$tool_name" = "Write" ] && [ ! -f "$file_path" ]; then
  # Fichier nouveau : extraire new_content et valider dans un tmpfile
  new_content=$(echo "$input" | jq -r '.tool_input.content // empty')
  if [ -z "$new_content" ]; then
    exit 0
  fi

  # Vérification rapide : contient-il un frontmatter ?
  if ! echo "$new_content" | head -1 | grep -q '^---'; then
    exit 0
  fi

  tmpfile=$(mktemp /tmp/kb-quality-check-XXXXXX.md)
  trap 'rm -f "$tmpfile"' EXIT
  echo "$new_content" > "$tmpfile"
  target_file="$tmpfile"
else
  # Fichier existant (Edit ou Write sur fichier existant)
  if [ ! -f "$file_path" ]; then
    exit 0
  fi
  target_file="$file_path"
fi

# ── Validation ────────────────────────────────────────────────────────────────
if [ -n "$SCHEMAS_DIR" ]; then
  result=$(python3 "$VALIDATOR" --kb-root "$KB_ROOT" "$target_file" 2>&1) || exit_code=$?
else
  result=$(python3 "$VALIDATOR" "$target_file" 2>&1) || exit_code=$?
fi

exit_code="${exit_code:-0}"

if [ "$exit_code" -eq 0 ]; then
  exit 0
fi

# ── Violations détectées → exit 2 avec message structuré ─────────────────────
# Extraire les lignes de violations pour un message compact
violations_summary=$(echo "$result" | grep -E '^\s+[✗⚠]' | head -10 | sed 's/^  //' | tr '\n' ' | ' | sed 's/ | $//')

if [ -z "$violations_summary" ]; then
  violations_summary="$result"
fi

rel_path=$(basename "$file_path")

echo "{\"systemMessage\": \"[quality-check] Frontmatter invalide dans $rel_path — $violations_summary. Corriger le frontmatter et relancer. Schemas: 00-fondations/schemas/frontmatter/\"}" >&2
exit 2
