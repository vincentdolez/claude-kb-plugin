# /inbox — Triage de l'inbox KB

L'inbox (`inbox/`) accueille les captures brutes : articles clippés, idées, transcripts, benchmarks, sources externes. Sans workflow explicite, l'inbox stagne et perd son sens. Cette commande **force le triage** : aucun item ne reste sans décision.

## Principe

Chaque session `/inbox` traite **au moins un item**. Pour chacun, une décision parmi 4 :

| Action | Quand | Destination |
|---|---|---|
| **Route** | L'item a sa place dans un domaine identifié | `02-marque/`, `04-contenu/seeds/`, `08-recherche/`, etc. |
| **Promote** | L'item est suffisamment mature pour vivre comme document KB | Nouveau fichier avec `status: exploration` ou `draft` |
| **Archive** | Référence à conserver mais sans valeur active | `inbox/processed/` ou `_archives/` |
| **Drop** | Capture obsolète, doublon, source biaisée | Suppression |

## Protocole

### 0. Identifier la racine KB

Cherche le répertoire contenant `CLAUDE.md` + `00-fondations/`. L'inbox est `inbox/` dans cette racine.

### 1. Router selon l'argument

- Pas d'argument → mode **scan** (étape 2)
- `show` → mode **affichage** : liste les items d'inbox avec age + 1 ligne de résumé, sans triage
- `<filename>` → mode **focus** : triage uniquement cet item (skip étape 2, va directement à 3)
- `oldest` → mode **focus sur le plus ancien** : triage l'item le plus âgé en premier

### 2. Mode scan — Inventaire de l'inbox

#### 2a. Lister les items

```bash
find inbox/ -maxdepth 2 -name "*.md" -not -path "*/processed/*" -type f
```

Pour chaque fichier, calcule l'age (date du jour - date `created:` du frontmatter, ou date de création fichier en fallback).

#### 2b. Présenter l'inventaire

Format :

```
## Inbox — N items, plus ancien : XX jours

| # | Fichier | Age | Première ligne |
|---|---------|-----|----------------|
| 1 | benchmark-linkedin.md | 43j | Étude positionnement... |
| 2 | these-variance.md | 44j | Hypothèse Congruence... |
```

Trier par age décroissant (le plus ancien en premier).

#### 2c. Recommandation

Si l'inbox dépasse **10 items** ou **30 jours d'age moyen**, signaler que le triage est en retard. Suggérer de traiter au moins 3 items dans cette session.

### 3. Mode focus — Triage d'un item

#### 3a. Lire l'item

Lis le fichier en entier (ou les 100 premières lignes si volumineux). Extrais :
- Sujet principal (titre, premier paragraphe)
- Domaine probable (vocabulaire, références, type de contenu)
- Maturité (note brute / déjà structuré / quasi publiable)

#### 3b. Proposer une décision

Présente à Vincent via `AskUserQuestion` :

```
Item : <filename> (<age> jours)

Sujet : <résumé en 1 phrase>
Domaine probable : <suggestion>
Maturité : <brute | semi-structurée | proche publication>

Recommandation : <action recommandée + destination si applicable>
```

Options à proposer (selon le contexte de l'item) :
1. **Route vers <destination>** — déplacer dans le domaine identifié
2. **Promote en exploration** — créer un nouveau fichier `status: exploration` dans le bon domaine
3. **Archive** — déplacer vers `inbox/processed/` ou `_archives/`
4. **Drop** — supprimer (avec confirmation explicite)

#### 3c. Exécuter

Selon la décision :

**Route** :
- Déplacer le fichier vers la destination (`mv` ou Bash `git mv`)
- Vérifier/ajouter le frontmatter conforme au schéma cible
- Mettre à jour les liens entrants si le fichier était référencé ailleurs

**Promote** :
- Créer un nouveau fichier dans le domaine cible avec :
  ```yaml
  ---
  title: "<titre clarifié>"
  type: <inféré du contenu : exploration|fondation|seed|chantier|...>
  status: exploration
  created: <today>
  updated: <today>
  owner: vincent
  tags: [<tags pertinents du registry>]
  depends_on: [<liens vers fichiers KB existants pertinents>]
  consumed_by: [claude-ai, human]
  ---
  ```
- Copier le contenu de l'item, restructuré si nécessaire
- Supprimer l'item original ou le déplacer en `inbox/processed/`

**Archive** :
- Déplacer vers `inbox/processed/` (référence proche) ou `_archives/` (référence éloignée)
- Conserver le frontmatter `created`/`updated`

**Drop** :
- Demander confirmation **explicite** ("supprimer définitivement ?")
- Si OK, `rm` le fichier (ou `git rm` si tracké)
- Logger dans le journal si l'item était substantiel

### 4. Boucle ou clôture

Après le triage d'un item, demander à Vincent :
- "Suivant" → revenir à étape 3 avec l'item suivant (ordre d'age décroissant)
- "Stop" → conclure la session

### 5. Synthèse de session

À la fin, présenter :

```
## Session /inbox — récap

Traités : N items
- Routés : <list>
- Promus : <list>
- Archivés : <list>
- Droppés : <list>

Inbox restant : M items (plus ancien : XX jours)
```

Si des promotions ont créé des fichiers `exploration`, suggérer de les lier depuis le `_index.md` du domaine d'accueil.

## Règles

- **Toujours** lire l'item avant de proposer une action (pas de tri sur le titre seul)
- **Ne jamais drop** sans confirmation explicite
- **Toujours** conserver le contenu si on doute (archive plutôt que drop)
- **Proposer** la destination la plus précise possible — pas "04-contenu/" mais "04-contenu/seeds/"
- **Vérifier** le frontmatter cible avant un Route (compatibilité de schéma)
- **Logger** dans le journal si la session a traité des items substantiels

## Anti-patterns à éviter

- ❌ Vider l'inbox d'un coup sans lire chaque item
- ❌ Tout promouvoir en exploration (l'exploration doit être motivée par une intention)
- ❌ Archiver pour ne pas avoir à décider (l'archive est aussi une décision, pas un punching-ball)
- ❌ Drop sans avoir vérifié les liens entrants

$ARGUMENTS
