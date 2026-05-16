#!/bin/bash
# PreToolUse hook: validate tags against tags-registry.md
# Warns (exit 2 → feedback to Claude) if unknown tags are used
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

# Only check Edit (Write creates new files, tags may not exist yet)
if [ "$tool_name" != "Edit" ]; then
  exit 0
fi

# Extract the new_string being written
new_string=$(echo "$input" | jq -r '.tool_input.new_string // empty')
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Skip if not a .md file
if [[ "$file_path" != *.md ]]; then
  exit 0
fi

# Skip if new_string doesn't contain tags
if ! echo "$new_string" | grep -q '^tags:'; then
  exit 0
fi

# Extract tags from the new_string — supports inline "tags: [a, b, c]" format
tags_line=$(echo "$new_string" | grep '^tags:' | head -1)
# Strip "tags:" prefix, then surrounding brackets, then quotes
tags_raw=$(echo "$tags_line" | sed -E 's/^tags:[[:space:]]*//; s/^\[//; s/\][[:space:]]*$//' | tr -d '"' | tr -d "'")
# Skip empty tags list (tags: [] or tags:)
if [ -z "$tags_raw" ]; then
  exit 0
fi

# Load valid tags from registry
KB_ROOT=$(echo "$file_path" | sed 's|/[0-9][0-9]-.*||')
REGISTRY="$KB_ROOT/00-fondations/tags-registry.md"

if [ ! -f "$REGISTRY" ]; then
  exit 0
fi

# Extract all valid tags from registry "## Catégories" section only
# (excludes "## Tags retirés" deprecated tags).
# Uses [^`]+ to capture any chars between backticks — accepts accents naturally.
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

# Check each tag (split by comma, trim spaces, fixed-string exact match)
unknown=""
IFS=',' read -ra tag_array <<< "$tags_raw"
for tag in "${tag_array[@]}"; do
  # Trim leading/trailing whitespace
  tag=$(echo "$tag" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  if [ -z "$tag" ]; then
    continue
  fi
  if ! echo "$valid_tags" | grep -Fxq "$tag"; then
    unknown="$unknown $tag"
  fi
done

if [ -n "$unknown" ]; then
  echo "{\"systemMessage\": \"Tags inconnus détectés :$unknown — vérifier dans 00-fondations/tags-registry.md ou les ajouter si légitimes.\"}" >&2
  exit 2
fi

exit 0
