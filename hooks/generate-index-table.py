#!/usr/bin/env python3
"""Generate markdown tables in _index.md from sibling files' frontmatter.

Replaces content between <!-- AUTO:BEGIN --> and <!-- AUTO:END --> markers.
Reads YAML frontmatter from all .md files in the directory (except _index.md).
Groups by `status` field, sorted by priority then name.

Usage: python3 generate-index-table.py <directory> <index_file>
"""

import os
import re
import sys
from collections import defaultdict

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "": 3}
STATUS_ORDER = ["actif", "en-pause", "draft", "exploration", "backlog", "terminé", "superseded", "abandonné", "archivé"]


def parse_frontmatter(filepath: str) -> dict | None:
    """Extract YAML frontmatter as a dict (simple parser, no deps)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    if not content.startswith("---"):
        return None

    end = content.find("\n---", 3)
    if end == -1:
        return None

    fm = {}
    for line in content[4:end].split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Simple key: value parsing (handles quoted strings, lists on same line)
        match = re.match(r'^(\w[\w-]*)\s*:\s*(.*)$', line)
        if match:
            key = match.group(1)
            val = match.group(2).strip().strip('"').strip("'")
            fm[key] = val
    return fm


def detect_file_type(files: list[dict]) -> str:
    """Detect what kind of files we're indexing to choose the right columns."""
    types = {f.get("type", "") for f in files}
    if "chantier" in types:
        return "chantier"
    if "person" in types:
        return "person"
    return "generic"


def generate_chantier_table(files: list[dict], directory: str) -> str:
    """Generate grouped tables for chantiers."""
    grouped = defaultdict(list)
    for f in files:
        status = f.get("status", "backlog")
        grouped[status].append(f)

    lines = []
    for status in STATUS_ORDER:
        group = grouped.get(status, [])
        if not group:
            continue

        # Sort by priority then name
        group.sort(key=lambda x: (
            PRIORITY_ORDER.get(x.get("priority", ""), 3),
            x.get("title", "")
        ))

        label = {
            "actif": "En cours",
            "en-pause": "En pause",
            "draft": "Brouillon",
            "exploration": "Exploration",
            "backlog": "Planifié",
            "terminé": "Terminé",
            "superseded": "Supersédé",
            "abandonné": "Abandonné",
            "archivé": "Archivé",
        }.get(status, status)

        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Chantier | Prio | Cible | Progress | MAJ |")
        lines.append("|---|---|---|---|---|")

        for f in group:
            name = f.get("title", f["_basename"])
            rel_path = os.path.relpath(f["_path"], os.path.dirname(directory))
            # Remove .md extension for wiki-link
            link_path = f["_relpath"].replace(".md", "")
            prio = f.get("priority", "—")
            target = f.get("target", "—")
            progress = f.get("progress", "—")
            if progress not in ("—", ""):
                progress = f"{progress}%"
            updated = f.get("updated", "—")
            lines.append(f"| [[{link_path}]] | {prio} | {target} | {progress} | {updated} |")

        lines.append("")

    return "\n".join(lines)


def generate_person_table(files: list[dict], directory: str) -> str:
    """Generate pipeline-grouped tables for contacts."""
    pipeline_order = ["en-conversation", "qualifie", "contacte", "identifie", "classe"]
    grouped = defaultdict(list)
    for f in files:
        pipeline = f.get("pipeline", "identifie")
        grouped[pipeline].append(f)

    lines = []
    for pipeline in pipeline_order:
        group = grouped.get(pipeline, [])
        if not group:
            continue

        group.sort(key=lambda x: x.get("next_action_date", "9999"))

        label = {
            "en-conversation": "En conversation",
            "qualifie": "Qualifié",
            "contacte": "Contacté",
            "identifie": "Identifié",
            "classe": "Classé",
        }.get(pipeline, pipeline)

        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Nom | Organisation | Prochaine action | Date |")
        lines.append("|---|---|---|---|")

        for f in group:
            link_path = f["_relpath"].replace(".md", "")
            org = f.get("organization", "—")
            action = f.get("next_action", "—")
            date = f.get("next_action_date", "—")
            lines.append(f"| [[{link_path}]] | {org} | {action} | {date} |")

        lines.append("")

    return "\n".join(lines)


def generate_generic_table(files: list[dict], directory: str) -> str:
    """Generate a simple table for any file type."""
    grouped = defaultdict(list)
    for f in files:
        status = f.get("status", "draft")
        grouped[status].append(f)

    lines = []
    for status in STATUS_ORDER:
        group = grouped.get(status, [])
        if not group:
            continue

        group.sort(key=lambda x: x.get("title", x["_basename"]))

        lines.append(f"### {status.capitalize()}")
        lines.append("")
        lines.append("| Fichier | Type | MAJ |")
        lines.append("|---|---|---|")

        for f in group:
            link_path = f["_relpath"].replace(".md", "")
            ftype = f.get("type", "—")
            updated = f.get("updated", "—")
            lines.append(f"| [[{link_path}]] | {ftype} | {updated} |")

        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: generate-index-table.py <directory> <index_file>", file=sys.stderr)
        sys.exit(1)

    directory = sys.argv[1]
    index_file = sys.argv[2]

    # Collect all .md files (not _index.md, not in subdirs for simplicity)
    files = []
    for entry in os.listdir(directory):
        if entry == "_index.md" or entry == "README.md":
            continue
        if not entry.endswith(".md"):
            continue
        filepath = os.path.join(directory, entry)
        if not os.path.isfile(filepath):
            continue

        fm = parse_frontmatter(filepath)
        if fm is None:
            continue

        fm["_path"] = filepath
        fm["_basename"] = entry.replace(".md", "")
        # Compute path relative to KB root for wiki-links
        # Find the KB root (parent of numbered dirs)
        kb_root = directory
        while kb_root and not os.path.exists(os.path.join(kb_root, "CLAUDE.md")):
            parent = os.path.dirname(kb_root)
            if parent == kb_root:
                break
            kb_root = parent
        fm["_relpath"] = os.path.relpath(filepath, kb_root)
        files.append(fm)

    if not files:
        return

    # Detect type and generate appropriate table
    file_type = detect_file_type(files)
    if file_type == "chantier":
        table = generate_chantier_table(files, directory)
    elif file_type == "person":
        table = generate_person_table(files, directory)
    else:
        table = generate_generic_table(files, directory)

    # Read _index.md and replace between markers
    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()

    begin_marker = "<!-- AUTO:BEGIN -->"
    end_marker = "<!-- AUTO:END -->"

    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)

    if begin_idx == -1 or end_idx == -1:
        return

    new_content = (
        content[:begin_idx + len(begin_marker)]
        + "\n"
        + table
        + content[end_idx:]
    )

    # Only write if changed
    if new_content != content:
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(new_content)


if __name__ == "__main__":
    main()
