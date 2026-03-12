# /journal — Journal de session KB

Le journal (`journal/journal.tsv`) est le cache de boot inter-sessions. Il porte ce que git ne porte pas : le contexte business, les décisions, le next, les seeds contenu.

## Protocole

### 0. Identifier la racine KB

Cherche le répertoire contenant `CLAUDE.md` + `00-fondations/`. C'est la racine KB.
Le fichier journal est à `journal/journal.tsv` dans cette racine.

### 1. Router selon l'argument

- Pas d'argument → mode **scan** (étape 2)
- `show` → mode **affichage** : affiche les 5 dernières entrées du TSV
- `show <N>` → mode **affichage** : affiche les N dernières entrées du TSV

En mode affichage, formate le TSV en table lisible et arrête-toi là.

### 2. Mode scan — Préparer une entrée

#### 2a. Lire la dernière entrée

Lis `journal/journal.tsv`. Récupère la date de la dernière ligne (colonne `date`).
Si le fichier ne contient que le header, scanne les changements du jour.

#### 2b. Scanner les changements

```bash
# Changements non commités
git diff --name-only HEAD

# Commits depuis la dernière date journalisée
git log --since="<last_date>" --name-only --pretty=format:""
```

Filtre uniquement les `.md` dans la KB (pas dans le plugin, pas dans `.claude/`). Déduplique.

#### 2c. Analyser les changements

Pour chaque fichier touché, lis le frontmatter (premières lignes seulement) :
- Transitions de statut
- Nouveaux fichiers (décisions, chantiers)
- Fichiers core touchés (L0-L1)

#### 2d. Composer la ligne TSV

Colonnes séparées par des tabs réels :

| Colonne | Ce qu'elle porte | Exemple |
|---------|-----------------|---------|
| `date` | YYYY-MM-DD | 2026-03-12 |
| `contexte` | Le pourquoi business de la session (pas le quoi technique — ça c'est git) | Refonte boot agent pour réduire le temps de chargement KB |
| `decisions` | Wiki-links `[[ADR]]` ou choix notables en texte court | `[[01-strategie/decisions/008-meta-framework]]` |
| `next` | Prochaine action concrète | Implémenter hook PreToolUse git commit |
| `seeds` | Idées contenu qui ont émergé (optionnel, vide si rien) | Coaching LinkedIn → article personal branding |

Règles :
- Wiki-links `[[chemin/fichier]]` sans `.md` quand ça pointe vers un fichier KB existant
- Pas de tabs dans les valeurs
- `contexte` = business, pas technique. Git a le technique.
- `next` = actionnable, pas vague

### 3. Validation

Affiche la ligne proposée :

```
## Entrée journal proposée — {date}

**Contexte** : {contexte}
**Décisions** : {decisions}
**Next** : {next}
**Seeds** : {seeds}
```

Demande validation à Vincent via AskUserQuestion :
- "OK" → appender
- Ajustements → modifier puis appender
- "skip" → ne rien écrire

### 4. Appender

Append la ligne au TSV. Si le fichier n'existe pas, créer avec le header :

```
date	contexte	decisions	next	seeds
```

### 5. Règles

- Ne jamais appender sans validation de Vincent
- Une seule ligne par session
- Si une entrée existe déjà pour aujourd'hui, proposer de la compléter (jamais modifier une ligne passée)
- Les wiki-links doivent pointer vers des fichiers existants
- Tabs réels comme séparateurs

$ARGUMENTS
