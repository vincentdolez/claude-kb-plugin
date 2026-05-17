# Contrat frontmatter — Référence partagée agents producteurs

> Ce bloc est à inclure dans tout agent qui produit des fichiers `.md` dans la KB.
> Les schemas complets sont dans `00-fondations/schemas/frontmatter/`.
> Le hook `hook-quality-check.sh` bloque tout frontmatter invalide (PreToolUse).

---

## Champs obligatoires (tous types)

```yaml
---
title: "Titre lisible"           # string, non vide
type: <type>                     # voir liste officielle ci-dessous
status: <statut>                 # voir liste officielle ci-dessous
created: YYYY-MM-DD              # format strict, ne pas mettre de guillemets
updated: YYYY-MM-DD              # géré par hook-auto-updated.sh — ne pas écrire manuellement
---
```

**Ne jamais écrire `updated` manuellement** : le hook `hook-auto-updated.sh` le gère.

---

## Types officiels

```
fondation  | strategie | marque    | spec     | ops
decision   | chantier  | contenu   | persona  | rapport
prompt     | template  | journal   | index    | note
technique  | mission   | person    | interview| recherche
copy       | veille    | buffer    | inbox    | document-simule
demo-script| simulation
```

---

## Statuts officiels

```
backlog → draft / exploration → actif → terminé / publié → archivé
                                                 ↳ abandonné
                                                 ↳ superseded (decisions)
```

| Statut | Quand |
|---|---|
| `backlog` | Identifié, pas démarré |
| `draft` | En cours, contenu incomplet |
| `exploration` | Spike / investigation |
| `actif` | Source de vérité validée |
| `en-pause` | Suspendu volontairement |
| `terminé` | Livré / objectif atteint |
| `publié` | Diffusé (articles, posts) |
| `abandonné` | Annulé — ne pas modifier |
| `archivé` | Obsolète — ne pas modifier |
| `superseded` | Remplacé (ADR) — requiert `replaced_by` |

---

## Champs recommandés

```yaml
owner: vincent | claude | shared
tags: [tag1, tag2]               # validés contre tags-registry.md
depends_on: [chemin/fichier.md]  # dépendances prérequises
consumed_by: [claude-ai, human]  # consommateurs (voir vocabulaire ci-dessous)
```

### Vocabulaire `consumed_by`

| Valeur | Usage |
|---|---|
| `human` | Lu par Vincent |
| `claude-ai` | Injecté comme contexte dans une conversation Claude |
| `claude-code` | Consommé par un agent Claude Code |
| `article-cadrage` | Input Flow 1 |
| `article-redaction` | Input Flow 2 |
| `article-qualite` | Input Flow 3 |
| `article-derivation` | Input Flow 4 |
| `linkedin` | Publié / dérivé pour LinkedIn |
| `vincentdolez-fr` | Publié / dérivé pour le site |
| `reviewer` | Document de review |

---

## Champs spécifiques par type

### `chantier`

```yaml
priority: P0 | P1 | P2
target: Q2-2026              # format QN-YYYY
progress: 0                  # 0-100
blocked_by: []
deliverables:
  - Livrable attendu
```

### `decision`

```yaml
replaces: chemin/ancien-adr.md    # optionnel
replaced_by: chemin/nouveau.md    # obligatoire si status: superseded
consequences: "..."               # optionnel
```

### `contenu`

```yaml
audience: CEO                     # ou [CEO, sponsor-ops] — libre
pilier: automation                # libre : automation, dette, coulisses, lab...
canal: linkedin                   # linkedin | site | newsletter | talk
```

### `person`

```yaml
organization: "Nom entreprise"
role: "CEO"
relation: prospect | partenaire | reseau | prescripteur | classe
channel: linkedin | email | tel | direct
pipeline: identifie | contacte | en-conversation | qualifie | classe
next_action: "Action concrète"
next_action_date: YYYY-MM-DD
```

### `interview`

```yaml
interviewee: "Prénom Nom"
interview_date: YYYY-MM-DD
```

---

## Exemples conformes

### Exemple minimal (note)

```yaml
---
title: "Ma note"
type: note
status: draft
created: 2026-05-18
updated: 2026-05-18
---
```

### Exemple complet (chantier)

```yaml
---
title: "P1 — Quality harness frontmatter"
type: chantier
status: actif
created: 2026-05-17
updated: 2026-05-18
owner: shared
priority: P0
target: Q2-2026
progress: 80
blocked_by: []
deliverables:
  - Schemas JSON par type
  - Validator CLI
  - Hook PreToolUse
tags: [meta-tooling, gouvernance]
depends_on:
  - 01-strategie/chantiers/chantier-kb-evolution.md
consumed_by: [claude-code, human]
---
```

### Exemple complet (contenu)

```yaml
---
title: "Pourquoi les migrations legacy échouent"
type: contenu
status: draft
created: 2026-05-18
updated: 2026-05-18
owner: claude
audience: CEO
pilier: dette
canal: linkedin
tags: [legacy, article]
depends_on:
  - 04-contenu/pipeline/migrations-legacy/brief.md
consumed_by: [article-redaction, human]
---
```

---

## Tolérance archives / templates

Les fichiers dans `_archives/` et `_templates/` produisent des **warnings** (pas des violations critiques) si le frontmatter est incomplet. L'agent ne doit pas corriger ces fichiers sauf demande explicite.

---

## Validator CLI

```bash
# Valider un fichier
python3 claude-kb-plugin/skills/obsidian-nav/scripts/kb_frontmatter_validate.py chemin/fichier.md

# Valider un dossier entier
python3 claude-kb-plugin/skills/obsidian-nav/scripts/kb_frontmatter_validate.py \
  --kb-root /chemin/vers/kb --glob "**/*.md" --summary
```
