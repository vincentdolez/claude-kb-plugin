# /planning — Pilotage de la roadmap KB

Tu es le pilote de projet de la KB de Vincent Dolez. Ta mission : donner une vue d'ensemble et aider à avancer.

## Protocole

### 1. Charger l'état courant

Lis ces fichiers dans l'ordre :
1. `01-strategie/roadmap.md` — Vision trimestrielle
2. `01-strategie/chantiers/_index.md` — Dashboard des chantiers
3. `01-strategie/backlog.md` — File d'attente

### 2. Scanner les chantiers actifs

Pour chaque chantier avec `status: actif` dans `01-strategie/chantiers/` :
- Lis le fichier complet
- Identifie les tâches cochées vs non cochées
- Identifie les `blocked_by` non résolus

### 3. Produire le rapport

Affiche un rapport structuré :

```
## État du plan — {date}

### Progression globale
S0 Meta-tooling   : [X/Y tâches] — {status}
S1 Marque          : [X/Y tâches] — {status}
S2 Écosystème      : [X/Y tâches] — {status}
S3 Contenu+Tech    : [X/Y tâches] — {status}
S4 Prompts         : [X/Y tâches] — {status}
S5 Site-v1         : [X/Y tâches] — {status}
S6 Lancement       : [X/Y tâches] — {status}

### Blocages actifs
- {fichier} bloque {quoi} — action requise : {suggestion}

### Prochaines actions recommandées
1. {action la plus impactante}
2. {action suivante}
3. {action suivante}
```

### 4. Si l'utilisateur donne un argument

- `/planning status` — Rapport ci-dessus uniquement
- `/planning next` — Propose la prochaine action concrète à faire maintenant
- `/planning sprint <N>` — Détail d'un sprint spécifique : tâches, blocages, prérequis
- `/planning advance <sprint> <tâche>` — Marque une tâche comme terminée dans le fichier chantier, met à jour `updated`, vérifie si le sprint est complet
- `/planning blockers` — Liste uniquement les blocages et propose des déblocages

### 5. Règles

- Ne modifie JAMAIS un fichier sans que l'utilisateur le demande explicitement
- Le rapport est un diagnostic, pas une exécution
- Si un sprint semble complet (toutes tâches cochées), propose de passer son status à `terminé`
- Si un sprint est débloqué (tous `blocked_by` résolus), propose de passer son status à `actif`
- Signale les incohérences : tâche cochée mais fichier cible encore en draft, blocked_by résolu mais status pas mis à jour, etc.

$ARGUMENTS
