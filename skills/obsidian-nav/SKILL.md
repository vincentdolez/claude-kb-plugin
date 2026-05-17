---
name: obsidian-nav
description: Navigation structurelle dans la KB. Utiliser systématiquement pour se repérer avant d'agir — explorer le graphe de dépendances, localiser les fichiers par statut/type/tags, identifier les backlinks, détecter les orphelins et les liens cassés. Permet de comprendre la topologie de la KB (qui dépend de quoi, qu'est-ce qui est impacté par un changement) avant de modifier quoi que ce soit. Utiliser aussi pour les audits structurels périodiques.
---

# Obsidian Nav — Navigation structurelle KB

Se repérer dans la KB par son graphe de dépendances, ses métadonnées et ses liens. Tous les scripts sont read-only, stdlib only (Python 3.9+).

## Quand utiliser

- **Avant de modifier un fichier** : explorer son graphe upstream/downstream pour mesurer l'impact
- **Avant de travailler sur un layer** : vérifier l'état des dépendances amont
- **Pour localiser** : trouver les fichiers par statut, type, tags, owner
- **Pour diagnostiquer** : orphelins, liens cassés, drafts stale, index désynchronisés
- **En audit** : rapport structurel 7 axes

## CLI — `kb_report.py`

Point d'entrée unique. Exécuter depuis la racine KB.

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/obsidian-nav/scripts"

# Graphe de dépendances — qui dépend de quoi
python3 $SCRIPTS/kb_report.py --graph 01-strategie/roadmap.md
python3 $SCRIPTS/kb_report.py --graph 01-strategie/roadmap.md --direction upstream

# Backlinks — qui référence ce fichier
python3 $SCRIPTS/kb_report.py --backlinks 00-fondations/positionnement.md

# Localiser par métadonnées
python3 $SCRIPTS/kb_report.py --query "status=draft"
python3 $SCRIPTS/kb_report.py --query "type=chantier" --query "status=actif"
python3 $SCRIPTS/kb_report.py --query "tags=contenu"

# État global
python3 $SCRIPTS/kb_report.py --stats
python3 $SCRIPTS/kb_report.py --orphans
python3 $SCRIPTS/kb_report.py --stale
python3 $SCRIPTS/kb_report.py --stale --days 60

# Audit structurel complet (7 axes)
python3 $SCRIPTS/kb_report.py --audit
```

## CLI — `kb_query.py` (DSL requêtes déclaratives)

Complète `kb_report.py` par une couche requête déclarative. Read-only, même données que les Obsidian Bases (P3). Réutilisable depuis hooks, agents, audits batch.

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/obsidian-nav/scripts"

# Chantiers actifs avec sélection de colonnes
python3 $SCRIPTS/kb_query.py --where "status:actif,type:chantier" \
  --select "title,priority,updated" --format md

# Fichiers tagués meta-tooling, hors archivé
python3 $SCRIPTS/kb_query.py --tags "meta-tooling" --exclude-status archivé --format list

# Qui dépend de ce fichier ?
python3 $SCRIPTS/kb_query.py --depends-on "08-recherche/congruence" --format graph

# Orphelins (hors archives)
python3 $SCRIPTS/kb_query.py --orphans --exclude "_archives/**" --format table

# Tags hors registry (utilisé par /lint 3c)
python3 $SCRIPTS/kb_query.py --tags-missing-registry --format json

# Drafts stales depuis plus de 45 jours
python3 $SCRIPTS/kb_query.py --where "updated<2026-04-01,status:draft" --format table
```

**Flags** : `--where EXPR`, `--tags TAGS`, `--depends-on PATH`, `--orphans`, `--tags-missing-registry`, `--exclude GLOB`, `--exclude-status STATUTS`, `--select CHAMPS`, `--format {table,md,json,list,graph}`, `--kb-root PATH`

**Opérateurs `--where`** : `field:value` (égalité), `field<YYYY-MM-DD` (date antérieure), `field>YYYY-MM-DD` (date postérieure). Virgule = AND.

**Format** : `table` si TTY, `json` si pipe (override possible avec `--format`).

**Exit codes** : 0 = résultats, 1 = aucun match, 2 = erreur DSL.

## Modules (usage programmatique par agents)

| Module | Rôle | Fonctions clés |
|--------|------|----------------|
| `kb_meta.py` | Frontmatter YAML | `query_files()`, `get_meta()`, `stale_drafts()` |
| `kb_links.py` | Wiki-links + depends_on | `find_backlinks()`, `resolve_links()` |
| `kb_graph.py` | Graphe de dépendances | `build_graph()`, `upstream()`, `downstream()`, `find_orphans()` |
| `kb_audit.py` | Audit structurel 7 axes | `run_full_audit()`, `format_report()` |

## Les 7 axes d'audit

1. **Liens cassés** — wiki-links et depends_on vers des fichiers inexistants
2. **Frontmatter invalide** — champs obligatoires manquants, statuts non autorisés
3. **Drafts stale** — drafts non mis à jour depuis >30j (warning) ou >60j (critique)
4. **Cohérence depends_on** — cibles en draft ou archivé au lieu d'actif
5. **Index désynchronisés** — fichiers absents de leur `_index.md`
6. **Orphelins** — aucune référence entrante
7. **Incohérences de statut** — chantier terminé avec dépendances incomplètes

## Design

- **Stdlib only** — pas de pip install, Python 3.9+
- **Read-only** — aucune modification de fichier
- **Chemins relatifs** — toute sortie relative à la racine KB
- **Auto-détection** — remonte depuis cwd en cherchant `CLAUDE.md` + `00-fondations/`
