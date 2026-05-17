#!/bin/bash
# PreToolUse hook: validate tags against tags-registry.md (Option B)
#
# Architecture : service transformateur, pas gatekeeper bloquant.
#   - Tags officiels          → exit 0 (chemin rapide, <100ms)
#   - Tags nettoyables        → exit 2 + stderr avec mapping (RENAME/MAP/KILL)
#   - Tags inconnus (parks)   → exit 0 + append tags-pending.md (side-effect)
#   - Fallback (timeout/err)  → suggestions statiques + exit 2
#
# Garde-fou anti-boucle : KB_HOOK_ATTEMPTS — si ≥2 tentatives avec des
# inconnus résiduels, bloqué en exit 2 ferme.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

if [ "$tool_name" != "Edit" ]; then
  exit 0
fi

new_string=$(echo "$input" | jq -r '.tool_input.new_string // empty')
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [[ "$file_path" != *.md ]]; then
  exit 0
fi

if ! echo "$new_string" | grep -q '^tags:'; then
  exit 0
fi

# ── Extraction des tags ──────────────────────────────────────────────────────
tags_line=$(echo "$new_string" | grep '^tags:' | head -1)
tags_raw=$(echo "$tags_line" | sed -E 's/^tags:[[:space:]]*//; s/^\[//; s/\][[:space:]]*$//' | tr -d '"' | tr -d "'")

if [ -z "$tags_raw" ]; then
  exit 0
fi

# ── Localisation du registry ─────────────────────────────────────────────────
# Remonte jusqu'à la racine KB (dossier contenant 00-fondations/)
KB_ROOT="$file_path"
while [ "$KB_ROOT" != "/" ] && [ ! -d "$KB_ROOT/00-fondations" ]; do
  KB_ROOT=$(dirname "$KB_ROOT")
done

REGISTRY="$KB_ROOT/00-fondations/tags-registry.md"
PENDING="$KB_ROOT/00-fondations/tags-pending.md"
HOOKS_DIR="$(dirname "$0")"
CLI_SCRIPT="$HOOKS_DIR/agent-tags-cli.py"

if [ ! -f "$REGISTRY" ]; then
  exit 0
fi

# ── Chargement des tags valides ───────────────────────────────────────────────
valid_tags=$(awk '
  /^## Catégories/ {capture=1; next}
  /^## Tags retirés/ {capture=0}
  capture {
    while (match($0, /`[^`]+`/)) {
      print substr($0, RSTART+1, RLENGTH-2)
      $0 = substr($0, RSTART+RLENGTH)
    }
  }
' "$REGISTRY" | sort -u)

# ── Vérification rapide : tous officiels ? ────────────────────────────────────
unknown_list=()
IFS=',' read -ra tag_array <<< "$tags_raw"
for tag in "${tag_array[@]}"; do
  tag=$(echo "$tag" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  [ -z "$tag" ] && continue
  if ! echo "$valid_tags" | grep -Fxq "$tag"; then
    unknown_list+=("$tag")
  fi
done

# Chemin rapide : tous officiels
if [ ${#unknown_list[@]} -eq 0 ]; then
  exit 0
fi

# ── Garde-fou anti-boucle ────────────────────────────────────────────────────
attempts="${KB_HOOK_ATTEMPTS:-0}"
if [ "$attempts" -ge 2 ]; then
  unknown_str=$(printf '%s,' "${unknown_list[@]}" | sed 's/,$//')
  echo "{\"systemMessage\": \"[tag-validate] Trop de tentatives ($attempts) sur les tags inconnus : $unknown_str — bloqué. Corriger dans le frontmatter ou vérifier tags-registry.md.\"}" >&2
  exit 2
fi

# ── Délégation à agent-tags-cli.py ──────────────────────────────────────────
if [ -f "$CLI_SCRIPT" ] && command -v python3 &>/dev/null; then
  titre=$(grep '^title:' "$file_path" 2>/dev/null | head -1 | sed 's/^title:[[:space:]]*//' | tr -d '"' | tr -d "'" || echo "")
  date_today=$(date +%Y-%m-%d)

  # Construire JSON des tags inconnus
  unknown_json=$(printf '%s\n' "${unknown_list[@]}" | jq -R . | jq -s .)

  json_input=$(jq -n \
    --argjson tags "$unknown_json" \
    --arg fichier "$file_path" \
    --arg titre "$titre" \
    --arg registry "$REGISTRY" \
    '{tags_inconnus: $tags, fichier_source: $fichier, titre: $titre, registry_path: $registry}')

  cli_result=$(echo "$json_input" | timeout 30 python3 "$CLI_SCRIPT" 2>/dev/null) || {
    # Fallback statique si timeout ou erreur
    unknown_str=$(printf '%s,' "${unknown_list[@]}" | sed 's/,$//')
    echo "{\"systemMessage\": \"[tag-validate] Timeout agent-tags-cli — tags inconnus : $unknown_str. Vérifier dans 00-fondations/tags-registry.md.\"}" >&2
    exit 2
  }

  # Parser les 4 catégories
  renames=$(echo "$cli_result" | jq -r '.renames | to_entries | map("\(.key) → \(.value)") | join(", ")' 2>/dev/null || echo "")
  maps=$(echo "$cli_result" | jq -r '.maps | to_entries | map("\(.key) → \(.value)") | join(", ")' 2>/dev/null || echo "")
  kills=$(echo "$cli_result" | jq -r '.kills | join(", ")' 2>/dev/null || echo "")
  parks_raw=$(echo "$cli_result" | jq -r '.parks[]' 2>/dev/null || echo "")

  has_actionable=false
  msg_parts=()

  [ -n "$renames" ] && { has_actionable=true; msg_parts+=("RENAME: $renames"); }
  [ -n "$maps" ]    && { has_actionable=true; msg_parts+=("MAP: $maps"); }
  [ -n "$kills" ]   && { has_actionable=true; msg_parts+=("SUPPRIMER: $kills"); }

  # ── PARK : append tags-pending.md (side-effect silencieux) ───────────────
  if [ -n "$parks_raw" ] && [ -f "$PENDING" ]; then
    while IFS= read -r ptag; do
      ptag=$(echo "$ptag" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
      [ -z "$ptag" ] && continue
      if ! grep -qF "| $ptag |" "$PENDING" 2>/dev/null; then
        printf "| %s | %s | %s | %s |\n" "$ptag" "$file_path" "$date_today" "$titre" >> "$PENDING"
      fi
    done <<< "$parks_raw"
  fi

  # Seulement des parks → laisser passer
  if [ "$has_actionable" = false ]; then
    if [ -n "$parks_raw" ]; then
      parks_str=$(echo "$parks_raw" | tr '\n' ',' | sed 's/,$//')
      echo "{\"systemMessage\": \"[tag-validate] Tags inconnus parkés pour review : $parks_str → 00-fondations/tags-pending.md\"}" >&2
    fi
    exit 0
  fi

  # Actions nettoyables → exit 2 avec corrections
  IFS=';' read -ra parts_arr <<< "$(printf '%s;' "${msg_parts[@]}")"
  msg=$(printf '%s ' "${msg_parts[@]}")
  echo "{\"systemMessage\": \"[tag-validate] Tags à corriger — $msg. Corriger le frontmatter et relancer.\"}" >&2
  exit 2

else
  # Fallback : pas de Python, mode Option A (gatekeeper basique)
  unknown_str=$(printf '%s,' "${unknown_list[@]}" | sed 's/,$//')
  echo "{\"systemMessage\": \"[tag-validate] Tags inconnus : $unknown_str — vérifier dans 00-fondations/tags-registry.md.\"}" >&2
  exit 2
fi
