#!/bin/bash
# Test runner pour hook-tag-validate Option B
# Teste agent-tags-cli.py directement (unitaire, déterministe, pas de LLM)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$REPO_ROOT/hooks/agent-tags-cli.py"
FIXTURES="$REPO_ROOT/tests/fixtures/hook-tag-validate"
# La KB est un sibling du repo plugin (fonctionne depuis worktree et repo principal)
_PLUGIN_GIT=$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2>/dev/null || echo "")
if [ -n "$_PLUGIN_GIT" ]; then
  _PLUGIN_MAIN=$(dirname "$_PLUGIN_GIT")  # /path/to/claude-kb-plugin
  KB_ROOT="$(dirname "$_PLUGIN_MAIN")/KB vincentdolez"
else
  KB_ROOT="$(dirname "$REPO_ROOT")/KB vincentdolez"
fi
REGISTRY="$KB_ROOT/00-fondations/tags-registry.md"
PENDING_ORIG="$KB_ROOT/00-fondations/tags-pending.md"

PASS=0
FAIL=0

check_registry_exists() {
  if [ ! -f "$REGISTRY" ]; then
    echo "SKIP — registry non trouvé : $REGISTRY"
    echo "       Lancer les tests depuis le contexte KB."
    exit 0
  fi
}

run_cli() {
  local json_input="$1"
  echo "$json_input" | python3 "$CLI"
}

assert_field_empty() {
  local result="$1" field="$2" label="$3"
  local val
  val=$(echo "$result" | jq -r ".$field | length")
  if [ "$val" -eq 0 ]; then
    echo "  PASS — $label : $field vide"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : $field devrait être vide, got: $(echo "$result" | jq -r ".$field")"
    FAIL=$((FAIL + 1))
  fi
}

assert_field_nonempty() {
  local result="$1" field="$2" label="$3"
  local val
  val=$(echo "$result" | jq -r ".$field | length")
  if [ "$val" -gt 0 ]; then
    echo "  PASS — $label : $field non vide : $(echo "$result" | jq -r ".$field")"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : $field devrait être non vide"
    FAIL=$((FAIL + 1))
  fi
}

assert_rename_key() {
  local result="$1" key="$2" expected="$3" label="$4"
  local got
  got=$(echo "$result" | jq -r ".renames[\"$key\"] // empty")
  if [ "$got" = "$expected" ]; then
    echo "  PASS — $label : rename $key → $expected"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : rename $key attendu $expected, got: $got"
    FAIL=$((FAIL + 1))
  fi
}

assert_map_key() {
  local result="$1" key="$2" expected="$3" label="$4"
  local got
  got=$(echo "$result" | jq -r ".maps[\"$key\"] // empty")
  if [ "$got" = "$expected" ]; then
    echo "  PASS — $label : map $key → $expected"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : map $key attendu $expected, got: $got"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains_kill() {
  local result="$1" tag="$2" label="$3"
  if echo "$result" | jq -r '.kills[]' | grep -qF "$tag"; then
    echo "  PASS — $label : kills contient '$tag'"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : kills devrait contenir '$tag', got: $(echo "$result" | jq -r '.kills')"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains_park() {
  local result="$1" tag="$2" label="$3"
  if echo "$result" | jq -r '.parks[]' | grep -qF "$tag"; then
    echo "  PASS — $label : parks contient '$tag'"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : parks devrait contenir '$tag', got: $(echo "$result" | jq -r '.parks')"
    FAIL=$((FAIL + 1))
  fi
}

assert_registry_unchanged() {
  local before_md5="$1" label="$2"
  local after_md5
  after_md5=$(md5 -q "$REGISTRY" 2>/dev/null || md5sum "$REGISTRY" | cut -d' ' -f1)
  if [ "$before_md5" = "$after_md5" ]; then
    echo "  PASS — $label : registry inchangé (PROMOTE interdit en CLI)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL — $label : registry modifié — PROMOTE est interdit en mode CLI !"
    FAIL=$((FAIL + 1))
  fi
}

# ─────────────────────────────────────────────────────────────────────────────

check_registry_exists

REGISTRY_MD5=$(md5 -q "$REGISTRY" 2>/dev/null || md5sum "$REGISTRY" | cut -d' ' -f1)

echo ""
echo "=== Cas 1 — Tags officiels (tous dans le registry) ==="
INPUT=$(jq -n \
  --argjson tags '["meta-tooling", "gouvernance", "audit"]' \
  --arg fichier "$FIXTURES/case-1-officiel.md" \
  --arg titre "Cas test 1" \
  --arg registry "$REGISTRY" \
  '{tags_inconnus: $tags, fichier_source: $fichier, titre: $titre, registry_path: $registry}')
RESULT=$(run_cli "$INPUT")
assert_field_empty "$RESULT" "renames" "cas-1"
assert_field_empty "$RESULT" "maps"    "cas-1"
assert_field_empty "$RESULT" "kills"   "cas-1"
assert_field_empty "$RESULT" "parks"   "cas-1"

echo ""
echo "=== Cas 2 — RENAME (securite → sécurité) ==="
INPUT=$(jq -n \
  --argjson tags '["securite"]' \
  --arg fichier "$FIXTURES/case-2-rename.md" \
  --arg titre "Cas test 2" \
  --arg registry "$REGISTRY" \
  '{tags_inconnus: $tags, fichier_source: $fichier, titre: $titre, registry_path: $registry}')
RESULT=$(run_cli "$INPUT")
assert_rename_key "$RESULT" "securite" "sécurité" "cas-2"
assert_field_empty "$RESULT" "maps"  "cas-2"
assert_field_empty "$RESULT" "kills" "cas-2"
assert_field_empty "$RESULT" "parks" "cas-2"

echo ""
echo "=== Cas 3 — MAP (contenu → editorial) ==="
INPUT=$(jq -n \
  --argjson tags '["agents"]' \
  --arg fichier "$FIXTURES/case-3-map.md" \
  --arg titre "Cas test 3" \
  --arg registry "$REGISTRY" \
  '{tags_inconnus: $tags, fichier_source: $fichier, titre: $titre, registry_path: $registry}')
RESULT=$(run_cli "$INPUT")
assert_map_key "$RESULT" "agents" "orchestration" "cas-3"
assert_field_empty "$RESULT" "renames" "cas-3"
assert_field_empty "$RESULT" "kills"   "cas-3"
assert_field_empty "$RESULT" "parks"   "cas-3"

echo ""
echo "=== Cas 4 — KILL (chantier = tag retiré sans alternative) ==="
INPUT=$(jq -n \
  --argjson tags '["chantier"]' \
  --arg fichier "$FIXTURES/case-4-kill.md" \
  --arg titre "Cas test 4" \
  --arg registry "$REGISTRY" \
  '{tags_inconnus: $tags, fichier_source: $fichier, titre: $titre, registry_path: $registry}')
RESULT=$(run_cli "$INPUT")
assert_contains_kill "$RESULT" "chantier" "cas-4"
assert_field_empty "$RESULT" "renames" "cas-4"
assert_field_empty "$RESULT" "maps"    "cas-4"
assert_field_empty "$RESULT" "parks"   "cas-4"

echo ""
echo "=== Cas 5 — PARK (truc-novel-xyz inconnu) + PROMOTE interdit ==="
# Utiliser un pending temporaire pour ne pas polluer la KB réelle
PENDING_TMP=$(mktemp)
cat "$PENDING_ORIG" > "$PENDING_TMP" 2>/dev/null || printf "| Tag | Fichier | Date | Titre |\n|---|---|---|---|\n" > "$PENDING_TMP"

INPUT=$(jq -n \
  --argjson tags '["truc-novel-xyz"]' \
  --arg fichier "$FIXTURES/case-5-park.md" \
  --arg titre "Cas test 5" \
  --arg registry "$REGISTRY" \
  '{tags_inconnus: $tags, fichier_source: $fichier, titre: $titre, registry_path: $registry}')
RESULT=$(run_cli "$INPUT")
assert_contains_park "$RESULT" "truc-novel-xyz" "cas-5"
assert_field_empty "$RESULT" "renames" "cas-5"
assert_field_empty "$RESULT" "maps"    "cas-5"
assert_field_empty "$RESULT" "kills"   "cas-5"
# Vérifier que le registry n'a pas été modifié (PROMOTE interdit)
assert_registry_unchanged "$REGISTRY_MD5" "cas-5"

rm -f "$PENDING_TMP"

echo ""
echo "══════════════════════════════════"
echo "Résultat : $PASS PASS / $FAIL FAIL"
echo "══════════════════════════════════"

[ "$FAIL" -eq 0 ]
