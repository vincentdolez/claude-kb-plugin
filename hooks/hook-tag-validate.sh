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

# Extract tags from the new_string
tags_line=$(echo "$new_string" | grep '^tags:' | head -1)
# Parse [tag1, tag2, tag3] format
tags=$(echo "$tags_line" | sed 's/tags:\s*\[//;s/\]//;s/,/ /g' | tr -d '"' | tr -d "'")

# Load valid tags from registry
KB_ROOT=$(echo "$file_path" | sed 's|/[0-9][0-9]-.*||')
REGISTRY="$KB_ROOT/00-fondations/tags-registry.md"

if [ ! -f "$REGISTRY" ]; then
  exit 0
fi

# Extract all tags from registry (lines starting with - ` in a list)
valid_tags=$(grep -oE '`[a-z0-9-]+`' "$REGISTRY" | tr -d '`' | sort -u)

# Check each tag
unknown=""
for tag in $tags; do
  tag=$(echo "$tag" | tr -d ' ')
  if [ -z "$tag" ]; then
    continue
  fi
  if ! echo "$valid_tags" | grep -qx "$tag"; then
    unknown="$unknown $tag"
  fi
done

if [ -n "$unknown" ]; then
  echo "{\"systemMessage\": \"Tags inconnus détectés :$unknown — vérifier dans 00-fondations/tags-registry.md ou les ajouter si légitimes.\"}" >&2
  exit 2
fi

exit 0
