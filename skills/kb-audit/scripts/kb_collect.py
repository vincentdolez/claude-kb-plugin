#!/usr/bin/env python3
"""KB Collect — Data collection for semantic audit. Produces JSON artifacts.

This script collects structural and lexical data from the KB for consumption
by LLM audit agents. It does NOT judge or score — agents do that.

Output: JSON to stdout (or file via --output).
"""

import os
import re
import sys
import json
import math
from pathlib import Path
from collections import defaultdict, Counter

# --- Import obsidian-nav modules ---
OBSIDIAN_NAV = Path(__file__).resolve().parent.parent.parent / 'obsidian-nav' / 'scripts'
sys.path.insert(0, str(OBSIDIAN_NAV))

from kb_meta import find_kb_root, iter_md_files, get_meta, all_files_meta
from kb_links import resolve_links, find_all_links
from kb_graph import build_graph, find_orphans, detect_cycles

FM_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)

LAYER_MAP = {
    '00-fondations': 'L0', '01-strategie': 'L1',
    '02-marque': 'L2', '03-ecosysteme': 'L2',
    '04-contenu': 'L3', '05-technique': 'L3', '08-recherche': 'L3',
    '06-operations': 'L4', '07-prompts': 'L4', '09-missions': 'L4',
}

STOP_WORDS = {
    'cette', 'faire', 'notre', 'leurs', 'entre', 'comme', 'aussi', 'avoir',
    'dans', 'avec', 'pour', 'plus', 'tout', 'mais', 'sont', 'peut', 'être',
    'quand', 'encore', 'alors', 'depuis', 'avant', 'après', 'donc', 'très',
    'chez', 'sans', 'sous', 'vers', 'autres', 'elle', 'elles', 'nous', 'vous',
    'leur', 'même', 'bien', 'fait', 'sera', 'doit', 'cela', 'ceci', 'dont',
    'faut', 'tous', 'quel', 'quelle', 'quels', 'quelles', 'chaque', 'autre',
}

STRUCTURAL_TAGS = {
    'article', 'draft', 'review', 'plan', 'contexte', 'derivation',
    'linkedin', 'publié', 'publie', 'index', 'meta',
}


def _get_layer(rel_path):
    top = rel_path.split('/')[0] if '/' in rel_path else ''
    return top


def _get_body(filepath):
    try:
        text = Path(filepath).read_text(encoding='utf-8')
    except Exception:
        return ''
    m = FM_RE.match(text)
    if m:
        return text[m.end():].strip()
    return text.strip()


def _tokenize(text):
    return re.findall(r'[a-zàâäéèêëïîôùûüÿçœæ-]+', text.lower())


def collect_vocab_fingerprints(kb_root):
    """Extract vocabulary fingerprints per layer using TF-IDF-like approach."""
    layer_docs = defaultdict(list)  # layer -> [body1, body2, ...]
    layer_tf = defaultdict(Counter)  # layer -> Counter of terms
    file_count_per_layer = defaultdict(int)

    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        layer = _get_layer(rel)
        if not layer or layer.startswith('.') or fp.name.startswith('_'):
            continue
        meta = get_meta(fp)
        if meta.get('status') == 'archivé':
            continue

        body = _get_body(fp)
        tokens = _tokenize(body)
        meaningful = [t for t in tokens if len(t) > 4 and t not in STOP_WORDS]
        layer_tf[layer].update(meaningful)
        file_count_per_layer[layer] += 1

    # Compute IDF (how many layers contain each term)
    all_terms = set()
    for counter in layer_tf.values():
        all_terms.update(counter.keys())

    n_layers = len(layer_tf)
    idf = {}
    for term in all_terms:
        doc_freq = sum(1 for counter in layer_tf.values() if term in counter)
        idf[term] = math.log(n_layers / max(doc_freq, 1)) + 1

    # TF-IDF per layer → distinctive terms
    layer_distinctive = {}
    for layer, tf in layer_tf.items():
        total = sum(tf.values())
        if total == 0:
            continue
        scored = {}
        for term, count in tf.items():
            tf_norm = count / total
            scored[term] = tf_norm * idf.get(term, 1)
        # Top 50 most distinctive terms
        top = sorted(scored.items(), key=lambda x: -x[1])[:50]
        layer_distinctive[layer] = [
            {'term': t, 'tfidf': round(s, 6), 'count': tf[t]}
            for t, s in top
        ]

    return {
        'layer_distinctive_terms': layer_distinctive,
        'file_count_per_layer': dict(file_count_per_layer),
        'total_unique_terms': len(all_terms),
    }


def collect_structural_metrics(kb_root):
    """Collect navigability and structural data."""
    all_meta = {e['path']: e for e in all_files_meta(kb_root)}

    # Dead-ends (no outgoing links)
    dead_ends = []
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        if fp.name.startswith('_') or fp.name in ('CLAUDE.md', 'CONTRIBUTING.md', 'README.md'):
            continue
        meta = get_meta(fp)
        if meta.get('status') in ('archivé', 'terminé'):
            continue
        resolved = resolve_links(fp, kb_root)
        outgoing = len([l for l in resolved['wikilinks'] if l['resolved']])
        outgoing += len([l for l in resolved['depends_on'] if l['resolved']])
        if outgoing == 0:
            dead_ends.append(rel)

    # _index.md coverage
    indexed_dirs = 0
    total_dirs = 0
    missing_indexes = []
    for dirpath, dirnames, filenames in os.walk(kb_root):
        dirnames[:] = [d for d in dirnames
                       if d not in {'.claude', '.git', 'node_modules', '.obsidian', '.skills'}]
        dp = Path(dirpath)
        rel_dir = str(dp.relative_to(kb_root))
        if rel_dir.startswith('.'):
            continue
        md_files = [f for f in filenames if f.endswith('.md') and f != '_index.md']
        if md_files:
            total_dirs += 1
            if '_index.md' in filenames:
                indexed_dirs += 1
            else:
                missing_indexes.append(rel_dir)

    # Metadata completeness
    routing_fields = {'type', 'status', 'tags', 'depends_on', 'consumed_by', 'owner'}
    meta_completeness = []
    for path, meta in all_meta.items():
        if Path(path).name.startswith('_'):
            continue
        present = routing_fields & set(meta.keys())
        meta_completeness.append({
            'path': path,
            'present': sorted(present),
            'missing': sorted(routing_fields - present),
            'ratio': round(len(present) / len(routing_fields), 2),
        })

    graph = build_graph(kb_root)
    cycles = detect_cycles(graph)

    return {
        'dead_ends': dead_ends,
        'dead_end_count': len(dead_ends),
        'index_coverage': f"{indexed_dirs}/{total_dirs}",
        'missing_indexes': missing_indexes[:20],
        'orphans': find_orphans(kb_root),
        'meta_completeness_avg': round(
            sum(m['ratio'] for m in meta_completeness) / max(len(meta_completeness), 1), 2
        ),
        'files_with_low_metadata': [
            m['path'] for m in meta_completeness if m['ratio'] < 0.5
        ][:20],
        'cycles': cycles,
        'cycle_count': len(cycles),
    }


def collect_file_profiles(kb_root):
    """Collect per-file content profiles for signal/noise and AI-first analysis."""
    profiles = []
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        if fp.name.startswith('_') or fp.name in ('CLAUDE.md', 'CONTRIBUTING.md', 'README.md'):
            continue
        layer = _get_layer(rel)
        if not layer or layer.startswith('.'):
            continue
        meta = get_meta(fp)
        if meta.get('status') == 'archivé':
            continue

        body = _get_body(fp)
        lines = body.split('\n')
        tokens = _tokenize(body)
        headers = [l for l in lines if re.match(r'^#{1,3}\s+\S', l)]

        profiles.append({
            'path': rel,
            'layer': layer,
            'type': meta.get('type', ''),
            'status': meta.get('status', ''),
            'word_count': len(tokens),
            'line_count': len(lines),
            'header_count': len(headers),
            'has_tags': bool(meta.get('tags')),
            'has_depends_on': bool(meta.get('depends_on')),
            'has_consumed_by': bool(meta.get('consumed_by')),
            'consumed_by': meta.get('consumed_by') if meta.get('consumed_by') else None,
            'empty_body': len(body.strip()) == 0,
        })

    return profiles


def collect_file_samples(kb_root, per_layer=3):
    """Collect actual file content samples for LLM agents to read.

    Returns a dict {layer: [{path, body_preview (first 500 chars)}]}
    Agents will Read full files themselves — this is just for routing.
    """
    samples = defaultdict(list)
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        layer = _get_layer(rel)
        if not layer or layer.startswith('.') or fp.name.startswith('_'):
            continue
        meta = get_meta(fp)
        if meta.get('status') in ('archivé', 'terminé'):
            continue
        if len(samples[layer]) < per_layer:
            body = _get_body(fp)
            if len(body) > 100:  # Skip near-empty files
                samples[layer].append({
                    'path': rel,
                    'preview': body[:300],
                })
    return dict(samples)


def collect_fondation_essence(kb_root):
    """Extract key content from fondations for alignment comparison."""
    essence = {}
    fondations_dir = kb_root / '00-fondations'
    if not fondations_dir.exists():
        return essence
    for fp in fondations_dir.glob('*.md'):
        if fp.name.startswith('_'):
            continue
        meta = get_meta(fp)
        if meta.get('status') == 'archivé':
            continue
        body = _get_body(fp)
        # Keep first 1000 chars as essence (agents will read full files if needed)
        essence[str(fp.relative_to(kb_root))] = {
            'title': meta.get('title', fp.stem),
            'preview': body[:1000],
        }
    return essence


def collect_overlap_candidates(kb_root):
    """Detect pairs of files with overlapping semantic territory."""
    # Collect per-file data
    file_data = []
    for fp in iter_md_files(kb_root):
        rel = str(fp.relative_to(kb_root))
        if fp.name.startswith('_') or fp.name in ('CLAUDE.md', 'CONTRIBUTING.md', 'README.md'):
            continue
        layer = _get_layer(rel)
        if not layer or layer.startswith('.'):
            continue
        meta = get_meta(fp)
        if meta.get('status') == 'archivé':
            continue

        # Semantic tags (exclude structural)
        raw_tags = meta.get('tags', [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(',')]
        semantic_tags = set(t.lower() for t in raw_tags if t.lower() not in STRUCTURAL_TAGS)
        if len(semantic_tags) < 2:
            continue

        # Header words from H1/H2
        body = _get_body(fp)
        headers = re.findall(r'^#{1,2}\s+(.+)$', body, re.MULTILINE)
        header_words = set()
        for h in headers:
            for w in _tokenize(h):
                if len(w) > 4 and w not in STOP_WORDS:
                    header_words.add(w)

        mapped_layer = LAYER_MAP.get(layer, layer)
        parent_dir = str(Path(rel).parent)

        file_data.append({
            'path': rel,
            'layer': layer,
            'mapped_layer': mapped_layer,
            'parent_dir': parent_dir,
            'semantic_tags': semantic_tags,
            'header_words': header_words,
        })

    def _jaccard(a, b):
        if not a and not b:
            return 0.0
        return len(a & b) / len(a | b)

    inter_candidates = []
    intra_candidates = []

    for i in range(len(file_data)):
        for j in range(i + 1, len(file_data)):
            a, b = file_data[i], file_data[j]
            tags_j = _jaccard(a['semantic_tags'], b['semantic_tags'])
            header_j = _jaccard(a['header_words'], b['header_words'])

            same_layer = a['mapped_layer'] == b['mapped_layer']
            same_parent = a['parent_dir'] == b['parent_dir']

            if same_layer and same_parent:
                continue  # Skip files in same directory within same layer

            signal = []
            match = False

            if same_layer:
                # Intra-layer: stricter thresholds
                if tags_j > 0.7:
                    signal.append('tags')
                    match = True
                if header_j > 0.6:
                    signal.append('headers')
                    match = True
            else:
                # Inter-layer
                if tags_j > 0.5:
                    signal.append('tags')
                    match = True
                if header_j > 0.4:
                    signal.append('headers')
                    match = True

            if match:
                entry = {
                    'file_a': a['path'],
                    'file_b': b['path'],
                    'signal': '|'.join(signal) if len(signal) > 1 else signal[0],
                    'tags_jaccard': round(tags_j, 2),
                    'header_overlap': round(header_j, 2),
                    'shared_tags': sorted(a['semantic_tags'] & b['semantic_tags']),
                    'shared_header_words': sorted(a['header_words'] & b['header_words']),
                }
                if same_layer:
                    intra_candidates.append(entry)
                else:
                    inter_candidates.append(entry)

    # Sort by combined score, cap at 20 total
    def _combined_score(c):
        return c['tags_jaccard'] + c['header_overlap']

    inter_candidates.sort(key=_combined_score, reverse=True)
    intra_candidates.sort(key=_combined_score, reverse=True)

    total_cap = 20
    all_sorted = sorted(inter_candidates + intra_candidates, key=_combined_score, reverse=True)[:total_cap]
    inter_candidates = [c for c in all_sorted if c in inter_candidates]
    intra_candidates = [c for c in all_sorted if c in intra_candidates]

    return {
        'inter_layer_candidates': inter_candidates,
        'intra_layer_candidates': intra_candidates,
        'total_candidates': len(inter_candidates) + len(intra_candidates),
    }


def collect_all(kb_root):
    """Run all collectors. Returns full artifact."""
    return {
        'kb_root': str(kb_root),
        'vocab_fingerprints': collect_vocab_fingerprints(kb_root),
        'structural_metrics': collect_structural_metrics(kb_root),
        'file_profiles': collect_file_profiles(kb_root),
        'file_samples': collect_file_samples(kb_root),
        'fondation_essence': collect_fondation_essence(kb_root),
        'overlap_candidates': collect_overlap_candidates(kb_root),
    }


def main():
    kb_root = find_kb_root()
    output_path = None

    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    # Specific collector
    collector = None
    if '--collector' in sys.argv:
        idx = sys.argv.index('--collector')
        if idx + 1 < len(sys.argv):
            collector = sys.argv[idx + 1]

    collectors = {
        'vocab': lambda: collect_vocab_fingerprints(kb_root),
        'structural': lambda: collect_structural_metrics(kb_root),
        'profiles': lambda: collect_file_profiles(kb_root),
        'samples': lambda: collect_file_samples(kb_root),
        'fondations': lambda: collect_fondation_essence(kb_root),
        'overlap': lambda: collect_overlap_candidates(kb_root),
    }

    if collector and collector in collectors:
        data = collectors[collector]()
    else:
        data = collect_all(kb_root)

    output = json.dumps(data, indent=2, ensure_ascii=False, default=str)

    if output_path:
        Path(output_path).write_text(output, encoding='utf-8')
        print(f"Artifacts written to {output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
