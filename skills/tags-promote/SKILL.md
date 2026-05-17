---
name: tags-promote
description: Promotion manuelle des tags depuis le buffer tags-pending.md — review des tags inconnus accumulés, décision PROMOTE/KILL par Vincent, patch registry et purge frontmatters. Invoquer quand le buffer n'est pas vide.
---

# /tags-promote — Promotion manuelle des tags en attente

Skill délibérée. La promotion d'un tag dans le registry est un acte intentionnel sur une vue cross-fichiers, jamais une réaction à un edit isolé.

## Prérequis

- `00-fondations/tags-pending.md` doit exister et contenir des entrées
- `00-fondations/tags-registry.md` doit être chargé comme source de vérité

## Processus

### 1. Lire le buffer

Lis `00-fondations/tags-pending.md`. Si la table est vide (seulement l'en-tête), informer Vincent et arrêter.

### 2. Analyser les tags en attente

Pour chaque tag unique dans le buffer :
- Compter les occurrences (dans combien de fichiers il apparaît)
- Identifier les fichiers source (colonne `Fichier`)
- Calculer les co-occurrences avec les tags officiels dans ces fichiers (lire les frontmatters des fichiers source)
- Évaluer si le tag est légitime : pertinent pour le filtrage, pas doublon de type/status, singulier, kebab-case, accentué

### 3. Présenter le tableau de décisions à Vincent

```
## Tags en attente de promotion

| Tag | Occ | Co-tags officiels | Recommandation | Décision Vincent |
|-----|-----|-------------------|----------------|------------------|
| truc-novel | 3 | meta-tooling, gouvernance | PROMOTE (Domaine) | ? |
| foo | 1 | spike | KILL (singleton, trop spécifique) | ? |
```

Recommandations possibles :
- `PROMOTE (Catégorie)` — tag légitime, à ajouter dans la catégorie X
- `KILL` — tag trop générique, singleton sans valeur, ou doublon
- `IGNORE` — laisser en pending, pas assez de recul

Demander à Vincent de valider chaque ligne.

### 4. Appliquer les décisions

#### Pour chaque PROMOTE validé

1. Demander la catégorie si non déterminable : Domaine / Projet / Canal / Audience / Pipeline / Écosystème / Technique / Type
2. Demander une description (une ligne, format du registry)
3. Ajouter le tag dans `00-fondations/tags-registry.md` dans la bonne section
4. Committer immédiatement : `feat(tags-registry): promote tag '<tag>' → catégorie <cat>`

#### Pour chaque KILL validé

1. Identifier tous les fichiers source dans le buffer
2. Pour chaque fichier : retirer le tag du frontmatter `tags:` (Edit ciblé)
3. Committer en lot : `fix(frontmatters): retire tag '<tag>' (kill depuis tags-pending)`

### 5. Vider le buffer

Retirer du tableau de `tags-pending.md` les entrées dont le tag a été traité (PROMOTE ou KILL). Laisser les IGNORE.

Commit final : `chore(tags-pending): purge entrées traitées`

### 6. Résumé

Informer Vincent du bilan :
- N tags promus
- M tags supprimés des frontmatters (M fichiers impactés)
- K tags laissés en pending

## Règles

1. **Jamais de PROMOTE en batch aveugle** — chaque tag est soumis à Vincent explicitement
2. **Un tag promu = une description dans le registry** — pas de tag orphelin sans doc
3. **KILL = sweep des fichiers source** — pas d'entrée dans le registry pour un tag retiré
4. **Max 10 tags par session** — au-delà, proposer de prioriser
5. **Conserver l'ordre chronologique dans tags-pending.md** — ne pas réorganiser le tableau, seulement supprimer les lignes traitées

## Anti-patterns

- Promouvoir un singleton (1 occurrence) sauf si le tag est clairement stratégique
- Promouvoir un tag qui répète un type ou un status
- Merger tags-pending dans le registry sans validation explicite de Vincent
