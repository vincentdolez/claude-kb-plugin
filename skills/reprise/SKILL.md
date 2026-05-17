---
name: reprise
description: Re-cadrage de session — purge mentale d'une session polluée via brief structuré depuis l'état canonique (CLAUDE.md + memory + journal). Déclencher quand la session a dérivé, qu'on a perdu le fil, ou qu'on repart de zéro sur un sujet.
---

# /reprise — Re-cadrage de session

Purge mentale d'une session qui a dérivé : injecte un brief structuré construit depuis l'état canonique. Pas une purge technique de la conversation (impossible), une mise à plat du cadre en <30 secondes de lecture.

## Déclencheurs

- `/reprise` — re-cadrage générique sans sujet
- `/reprise <sujet>` — re-cadrage centré (ex. `/reprise coaching-linkedin`, `/reprise site-v1`)
- Signaux verbaux : "je me suis perdu", "on repart de zéro", "le contexte est pollué", "on reprend où on en était", "reset"

## Protocole

### 1. Charger l'état canonique (lecture séquentielle, rapide)

| Source | Quoi extraire |
|--------|--------------|
| `CLAUDE.md` | Section **Moi** (Identité) + section **Projets actifs** (P0 et P1 uniquement) + section **Préférences** |
| `~/.claude/projects/-Users-vincentdolez-AI-KB-KB-vincentdolez/memory/MEMORY.md` | Index complet — titres + hooks une ligne |
| `journal/journal.tsv` | 3 à 5 dernières lignes — colonnes : `date | contexte | décisions | next | seeds` |
| `00-fondations/positionnement.md` | Premier § sous `## Posture` uniquement |

### 2. Optionnel : Charger le contexte sujet (si `[sujet]` fourni)

```bash
grep -ri "<sujet>" --include="*.md" -l .
```

Identifier 3 à 5 fichiers les plus pertinents. Pour chacun : lire le frontmatter (`status`, `depends_on`), pas le contenu complet.

### 3. Composer le brief (max 30 lignes utiles)

```
# /reprise — Brief de re-cadrage [sujet si fourni]

## Identité
[1 ligne depuis CLAUDE.md > Moi]

## Positionnement courant
[1-2 lignes depuis positionnement.md > §Posture]

## Projets actifs P0/P1
- Nom · Priorité · description 5 mots · statut

## Dernière session
date · next · seeds (extraits journal.tsv dernière ligne)

## Memory pertinente
- [[memory/fichier]] — hook une ligne
[3 à 5 entrées, filtrées par pertinence au sujet si fourni]

## Sujet du moment
[Section présente uniquement si [sujet] fourni]
- [[chemin/fichier]] — statut | depends_on résumé
[3 à 5 fichiers, pas plus]

---
On part de là ?
```

### 4. Outputter dans la conversation

Produire le brief directement. Aucun fichier créé, aucun commit. Attendre la confirmation de Vincent avant de travailler.

## Contraintes

- **Max 30 lignes utiles** — si trop long, compresser. Un brief qui dépasse n'est pas un re-cadrage, c'est un résumé.
- **Sources primaires uniquement** — CLAUDE.md, positionnement.md, journal.tsv, MEMORY.md. Pas de lecture KB supplémentaire sauf grep sujet.
- **Pas de LLM call / agent délégué** — lecture directe + composition. Simple et déterministe.
- **Read-only** — aucune modification des sources canoniques.
- **Wiki-links pour le détail** — pointer `[[chemin/fichier]]`, ne jamais reproduire le contenu in-line.

## Ce que ce skill ne fait PAS

- Ne purge pas techniquement la conversation
- Ne génère pas de commit
- Ne met pas à jour le journal (c'est `/close-session`)
- Ne charge pas la KB entière
- Ne lance pas d'audit (c'est `/kb-audit`)

## Complémentarité

| Moment | Skill |
|--------|-------|
| Début de session | Règle 1 CLAUDE.md (lecture manuelle CLAUDE.md + journal + memory) |
| Session qui a dérivé | `/reprise` ← ici |
| Fin de session | `/close-session` |
| Drift sémantique profond | `/kb-audit` |
