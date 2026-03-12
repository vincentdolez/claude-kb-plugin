#!/bin/bash
# PreToolUse hook: remind to /journal before git commit
# Triggers on Bash tool when command is git commit
# Checks if journal/journal.tsv has an entry for today — if not, reminds
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

# Only trigger on Bash
if [ "$tool_name" != "Bash" ]; then
  exit 0
fi

command=$(echo "$input" | jq -r '.tool_input.command // empty')

# Only trigger on git commit (not git commit --amend, not git log, etc.)
if ! echo "$command" | grep -qE '^git\s+commit\b'; then
  exit 0
fi

# Find KB root — look for CLAUDE.md + 00-fondations/ from cwd upward
cwd=$(echo "$input" | jq -r '.cwd // empty')
KB_ROOT=""
search_dir="${cwd:-$(pwd)}"
while [ "$search_dir" != "/" ]; do
  if [ -f "$search_dir/CLAUDE.md" ] && [ -d "$search_dir/00-fondations" ]; then
    KB_ROOT="$search_dir"
    break
  fi
  search_dir=$(dirname "$search_dir")
done

if [ -z "$KB_ROOT" ]; then
  exit 0
fi

TSV="$KB_ROOT/journal/journal.tsv"

# No TSV yet — remind
if [ ! -f "$TSV" ]; then
  echo '{"systemMessage": "Pas de journal/journal.tsv — penser à /journal pour capturer le contexte de session."}' >&2
  exit 2
fi

today=$(date +%Y-%m-%d)
last_date=$(tail -1 "$TSV" | cut -f1)

# Already journalized today — let commit through
if [ "$last_date" = "$today" ]; then
  exit 0
fi

# Check if there are .md changes in core (L0-L1)
has_core_changes=false
for changed in $(git -C "$KB_ROOT" diff --name-only HEAD 2>/dev/null); do
  if [[ "$changed" == 00-fondations/* ]] || [[ "$changed" == 01-strategie/* ]] || [[ "$changed" == CLAUDE.md ]]; then
    has_core_changes=true
    break
  fi
done

if ! $has_core_changes; then
  # Also check staged changes
  for changed in $(git -C "$KB_ROOT" diff --cached --name-only 2>/dev/null); do
    if [[ "$changed" == 00-fondations/* ]] || [[ "$changed" == 01-strategie/* ]] || [[ "$changed" == CLAUDE.md ]]; then
      has_core_changes=true
      break
    fi
  done
fi

if $has_core_changes; then
  echo '{"systemMessage": "Des fichiers core (L0-L1) ont été modifiés et le journal n'\''a pas d'\''entrée aujourd'\''hui. Penser à /journal avant de committer."}' >&2
  exit 2
fi

exit 0
