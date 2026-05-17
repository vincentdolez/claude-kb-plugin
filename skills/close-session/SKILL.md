---
name: close-session
description: Clôture de session KB — met à jour le chantier actif, écrit le journal, nettoie. Invoquer en fin de session de travail.
---

# /close-session — Clôture de session

Protocole systématique de fin de session. À invoquer explicitement par Vincent quand le travail est terminé.

## Checklist

Exécuter dans l'ordre :

### 1. Identifier le chantier actif

- Lire `journal/journal.tsv` (dernière ligne) pour le contexte de session
- Identifier le(s) chantier(s) touché(s) dans `01-strategie/chantiers/`
- Si aucun chantier identifiable, passer à l'étape 3

### 2. Mettre à jour le chantier

- Ajouter une entrée dans la section `## Log` du chantier avec la date et un résumé concis de ce qui a été fait
- Mettre à jour les statuts dans les tableaux de suivi (éléments passés de "à faire" à "fait", etc.)
- Mettre à jour le `progress` dans le frontmatter si pertinent
- **Ne PAS créer de fichier "prompt de reprise" séparé** — le chantier EST le prompt de reprise

### 3. Journal

- Vérifier si `journal/journal.tsv` a une entrée pour aujourd'hui
- Si non, ajouter une ligne TSV : `date | contexte | décisions | next | seeds`
- Si oui, vérifier que l'entrée est complète (especially `next` et `seeds`)

### 4. Memory — synchroniser avec le journal

- **Sync obligatoire** : pour chaque memory de type `project` liée au chantier actif, vérifier que son contenu reflète les décisions du journal (`decisions` de la dernière entrée TSV). Si la memory est en retard → la mettre à jour.
- Vérifier si des informations de session méritent une nouvelle memory (feedback, projet, user)
- Nettoyer les memories obsolètes si repérées
- Rappel : la memory est un pont court terme, pas un doublon de la KB. Mais si elle existe, elle doit être exacte — une memory périmée est pire qu'une memory absente.

### 5. Commit

- Proposer un commit avec les changements de session si pas déjà fait
- Le hook `journal-reminder` validera que le journal est à jour

## Ce que ce skill ne fait PAS

- Pas de fichier prompt de reprise (le chantier + journal suffisent)
- Pas de résumé verbeux de la session (le log chantier est concis)
- Pas de push automatique (toujours demander)
