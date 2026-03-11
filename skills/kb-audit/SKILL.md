---
name: kb-audit
description: This skill should be used when the user asks to "audit KB quality", "check KB alignment", "analyze signal/noise", "evaluate AI-first efficiency", "check lexical congruence", "KB semantic audit", "review KB health", "assess KB navigability", or needs a deep semantic and strategic audit beyond structural checks. Orchestrates 5 LLM agents for distributed semantic analysis.
version: 0.2.0
---

# KB Audit — Distributed Semantic Audit

Audit sémantique distribué de la KB hexagonale. 5 agents LLM spécialisés analysent chacun une dimension en parallèle, avec jugement sémantique (pas du keyword matching).

## Architecture

```
/kb-audit (orchestrateur command)
│
├── Phase 1 — Collecte (Python, déterministe)
│   └── kb_collect.py → /tmp/kb-audit-artifacts.json
│       ├── vocab_fingerprints (TF-IDF par layer)
│       ├── structural_metrics (dead-ends, index, orphelins)
│       ├── file_profiles (taille, headers, metadata par fichier)
│       ├── file_samples (échantillons pour routage)
│       ├── fondation_essence (contenu clé L0)
│       └── overlap_candidates (paires fichiers territoire similaire)
│
├── Phase 2 — Analyse sémantique (5 agents LLM en parallèle)
│   ├── audit-alignment    → D1 cohérence avec fondations
│   ├── audit-navigability → D2 qualité du maillage
│   ├── audit-congruence   → D3 séparation registres
│   ├── audit-signal       → D4 densité d'information utile
│   └── audit-ai-first     → D5 optimisation pour LLM
│
└── Phase 3 — Synthèse (orchestrateur)
    └── Croisement des 5 rapports → rapport final + actions prioritaires
```

## Principe fondamental

Les scripts Python collectent les données. Les agents LLM jugent. L'orchestrateur croise et synthétise. Chaque composant fait une seule chose.

- **Scripts** : déterministe, rapide, exhaustif. Produit des artifacts JSON.
- **Agents** : sémantique, qualitatif, échantillonné. Lisent les fichiers eux-mêmes.
- **Orchestrateur** : pur routage de flux. Ne juge jamais.

## Usage

```bash
# Audit complet (5 dimensions en parallèle)
/kb-audit full

# Une seule dimension
/kb-audit alignment
/kb-audit navigability
/kb-audit congruence
/kb-audit signal
/kb-audit ai-first

# Dernier rapport
/kb-audit status
```

## Complémentarité

| Outil | Périmètre | Méthode |
|-------|-----------|---------|
| `obsidian-nav --audit` | Structurel (7 axes) | Script Python déterministe |
| `/kb-audit` | Sémantique (5 dimensions) | Agents LLM + synthèse croisée |
| `agent-review` | Structurel (agent) | LLM sur script obsidian-nav |

Workflow recommandé : `obsidian-nav --audit` (hygiène) → `/kb-audit full` (sémantique).

## Components

### Scripts (`scripts/`)

- **`kb_collect.py`** — Collecteur de données. Produit les artifacts JSON pour les agents.

### Agents (`.claude/agents/`)

- **`audit-alignment.md`** — D1 : lit les fondations + échantillonne les layers, juge le drift sémantique
- **`audit-navigability.md`** — D2 : évalue le routeur, teste des parcours, mesure l'accessibilité
- **`audit-congruence.md`** — D3 : construit les lexiques depuis les données (pas hardcodé), détecte les fuites
- **`audit-signal.md`** — D4 : lit les fichiers, juge la densité d'information, identifie le bruit
- **`audit-ai-first.md`** — D5 : évalue le frontmatter comme routing, le chunking, la redondance

### Command (`.claude/commands/`)

- **`kb-audit.md`** — Orchestrateur pur (modèle `/article`)

### References (`references/`)

- **`dimensions.md`** — Critères détaillés par dimension
