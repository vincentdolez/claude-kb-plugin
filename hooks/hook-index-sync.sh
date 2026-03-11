#!/bin/bash
# PostToolUse hook: regenerate _index.md tables from frontmatter
# Triggers on Edit|Write for .md files in the KB
# Uses <!-- AUTO:BEGIN --> / <!-- AUTO:END --> markers in _index.md
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

# Get parent directory
dir=$(dirname "$file_path")
index_file="$dir/_index.md"

# Skip if no _index.md in parent dir
if [ ! -f "$index_file" ]; then
  exit 0
fi

# Skip if _index.md has no AUTO markers
if ! grep -q '<!-- AUTO:BEGIN -->' "$index_file"; then
  exit 0
fi

# Skip if the edited file IS the _index.md (avoid infinite loop)
if [ "$file_path" = "$index_file" ]; then
  exit 0
fi

# Call the Python generator
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/generate-index-table.py" "$dir" "$index_file"

exit 0
