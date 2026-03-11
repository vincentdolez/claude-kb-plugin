#!/bin/bash
# PostToolUse hook: auto-bump `updated` field in frontmatter
# Triggers on Edit|Write for .md files in the KB
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')
file_path=""

if [ "$tool_name" = "Edit" ]; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
elif [ "$tool_name" = "Write" ]; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
fi

# Skip if no file path or not a .md file
if [ -z "$file_path" ] || [[ "$file_path" != *.md ]]; then
  exit 0
fi

# Skip if file doesn't exist
if [ ! -f "$file_path" ]; then
  exit 0
fi

# Skip if file has no frontmatter
if ! head -1 "$file_path" | grep -q '^---$'; then
  exit 0
fi

# Skip if no `updated` field exists (don't add it where it wasn't)
if ! grep -q '^updated:' "$file_path"; then
  exit 0
fi

TODAY=$(date +%Y-%m-%d)
CURRENT=$(grep '^updated:' "$file_path" | head -1 | sed 's/updated: *//')

# Only update if different from today
if [ "$CURRENT" != "$TODAY" ]; then
  # Use sed to update in-place (macOS compatible)
  sed -i '' "s/^updated: .*/updated: $TODAY/" "$file_path"
fi

exit 0
