#!/bin/bash
# PostToolUse hook: detect structural changes in decisions/ and chantiers/
# Triggers systemMessage when a new file is created or a status changes
# Works for both Edit and Write by comparing file on disk vs last committed version
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')
file_path=""

if [ "$tool_name" = "Edit" ] || [ "$tool_name" = "Write" ]; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
fi

# Skip if no file path or not .md
if [ -z "$file_path" ] || [[ "$file_path" != *.md ]]; then
  exit 0
fi

# Only trigger on decisions/ and chantiers/ — exclude _index.md
basename=$(basename "$file_path")
if [[ "$basename" == "_index.md" ]]; then
  exit 0
fi

is_decision=false
is_chantier=false
if [[ "$file_path" == *"01-strategie/decisions/"* ]]; then
  is_decision=true
elif [[ "$file_path" == *"01-strategie/chantiers/"* ]]; then
  is_chantier=true
fi

if ! $is_decision && ! $is_chantier; then
  exit 0
fi

# Skip if file doesn't exist (deleted)
if [ ! -f "$file_path" ]; then
  exit 0
fi

# Determine file type label
if $is_decision; then
  type_label="décision"
else
  type_label="chantier"
fi

# Extract status from frontmatter (first match of status: in YAML block)
extract_status() {
  local content="$1"
  echo "$content" | awk '/^---$/{if(n++)exit}n' | grep '^status:' | head -1 | sed 's/status: *//'
}

# --- Check 1: New file (not yet tracked by git) ---
if ! git ls-files --error-unmatch "$file_path" >/dev/null 2>&1; then
  cat <<EOF
{"systemMessage": "PROPAGATION STRUCTURANTE — Nouveau fichier $type_label détecté : $basename. Vérifier : (1) l'index 01-strategie/${type_label}s/_index.md référence ce fichier, (2) évaluer si le hot cache CLAUDE.md doit être mis à jour, (3) vérifier les backlinks depuis les fichiers liés (depends_on, related)."}
EOF
  exit 0
fi

# --- Check 2: Status change — compare disk vs last committed version ---
current_content=$(cat "$file_path")
committed_content=$(git show "HEAD:$file_path" 2>/dev/null || echo "")

current_status=$(extract_status "$current_content")
committed_status=$(extract_status "$committed_content")

if [ -n "$current_status" ] && [ -n "$committed_status" ] && [ "$current_status" != "$committed_status" ]; then
  cat <<EOF
{"systemMessage": "PROPAGATION STRUCTURANTE — Transition de statut sur $type_label $basename : $committed_status → $current_status. Vérifier : (1) le contexte de travail est cohérent avec ce nouveau statut, (2) les dépendances aval sont à jour, (3) évaluer si le hot cache CLAUDE.md reflète ce changement."}
EOF
  exit 0
fi

exit 0
