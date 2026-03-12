# claude-kb

Plugin Claude Code pour gérer une Knowledge Base professionnelle avec Obsidian.

## Ce que ça fait

- **Hooks** : mise à jour automatique des dates, synchronisation des index, validation des tags, propagation structurelle
- **Agents** : 20 agents spécialisés (domaine, pipeline article, audit sémantique, review, gouvernance tags)
- **Skills** : navigation structurelle (graphe de dépendances, backlinks, orphelins), audit KB distribué (5 dimensions)
- **Commandes** : `/planning`, `/article`, `/kb-audit`, `/journal`

## Installation

Cloner à côté de votre vault Obsidian :

```
~/projects/
  ma-kb/              # vault Obsidian
  claude-kb-plugin/   # ce repo
```

Lancer Claude Code avec le plugin :

```bash
claude --plugin-dir ../claude-kb-plugin
```

Ou créer un lanceur dans votre projet :

```bash
#!/usr/bin/env bash
PLUGIN="$(dirname "$(cd "$(dirname "$0")" && pwd)")/claude-kb-plugin"
exec claude --plugin-dir "$PLUGIN"
```

## Prérequis

- Claude Code
- Python 3.9+ (stdlib only, pas de pip install)
- Un vault Obsidian avec la structure attendue (voir ci-dessous)

## Structure KB attendue

Le plugin s'attend à une KB organisée en layers avec `_index.md` par dossier :

```
00-fondations/    # L0 — vision, positionnement, principes
01-strategie/     # L1 — offres, roadmap, décisions, chantiers
02-marque/        # L2 — identité, charte éditoriale
03-ecosysteme/    # L2 — site, contacts, canaux
04-contenu/       # L3 — articles, pipeline
05-technique/     # L3 — stack, specs
06-operations/    # L4 — workflows, processus
```

Chaque fichier `.md` a un frontmatter YAML :

```yaml
---
title: "..."
type: ...
status: backlog | draft | actif | terminé | archivé
created: YYYY-MM-DD
updated: YYYY-MM-DD
depends_on: []
tags: []
---
```

Voir `templates/CONTRIBUTING.md` pour les conventions complètes.

## Composants

```
.claude-plugin/
  plugin.json         # manifest + hooks
agents/               # 20 agents (domaine, article, audit, review)
commands/             # /planning, /article, /kb-audit
skills/
  obsidian-nav/       # navigation structurelle + audit 7 axes
  kb-audit/           # audit sémantique distribué (5 agents LLM)
hooks/                # scripts bash/python des hooks
templates/            # CONTRIBUTING.md template
```

## Licence

MIT
