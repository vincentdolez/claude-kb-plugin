# /kb-audit — Audit sémantique KB (orchestrateur)

Tu orchestres l'audit sémantique de la KB. Tu **ne juges pas** toi-même — tu collectes les données, délègues le jugement aux 5 agents spécialisés, et synthétises leurs rapports.

## Architecture — 5 agents

| Agent | Dimension | Jugement |
|---|---|---|
| `audit-alignment` | D1 — Alignement fondations | Cohérence sémantique avec le positionnement |
| `audit-navigability` | D2 — Navigabilité | Qualité du maillage, parcours LLM |
| `audit-congruence` | D3 — Congruence lexicale | Séparation registres recherche/business |
| `audit-signal` | D4 — Signal/Bruit | Densité d'information utile |
| `audit-ai-first` | D5 — AI-First Efficiency | Optimisation pour consommation LLM |

## Protocole

### 1. Parser la commande

Argument attendu : `$ARGUMENTS`

Formats acceptés :
- `full` ou vide — Audit complet (5 dimensions)
- `{dimension}` — Une seule dimension (alignment, navigability, congruence, signal, ai-first)
- `status` — Afficher le dernier rapport si existant

### 2. Phase 1 — Collecte de données (déterministe)

Lancer le script de collecte :

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/kb-audit/scripts/kb_collect.py" --output /tmp/kb-audit-artifacts.json
```

Ce script produit les artifacts JSON que les agents consommeront :
- `vocab_fingerprints` — termes distinctifs par layer (TF-IDF)
- `structural_metrics` — dead-ends, couverture index, orphelins, metadata
- `file_profiles` — profil par fichier (taille, headers, metadata)
- `file_samples` — échantillons pour routage
- `fondation_essence` — contenu clé des fondations
- `overlap_candidates` — paires de fichiers avec territoire sémantique similaire

### 3. Phase 2 — Analyse sémantique (agents en parallèle)

Lire le JSON produit, puis lancer les 5 agents **en parallèle** via Agent tool.

Chaque agent reçoit :
- Les données JSON pertinentes pour sa dimension
- La consigne de lire des fichiers lui-même pour le jugement sémantique
- Le format de sortie attendu (JSON structuré)

```
Agent tool (5 appels parallèles):

  # D1 — Alignment
  subagent_type: audit-alignment
  prompt: |
    Audite l'alignement sémantique de la KB.
    KB root: /Users/vincentdolez/AI/KB/KB vincentdolez
    Artifacts: /tmp/kb-audit-artifacts.json
    Lis les fondations (00-fondations/*.md) et échantillonne 3-5 fichiers par layer aval.
    Utilise les vocab_fingerprints et fondation_essence du JSON comme point de départ.
    Utilise overlap_candidates du JSON pour juger les chevauchements sémantiques.
    Pour chaque paire : lis les deux fichiers, classe en projection/redundancy/misplacement.
    Produis ton rapport en JSON dans le format spécifié dans ton prompt système.

  # D2 — Navigability
  subagent_type: audit-navigability
  prompt: |
    Audite la navigabilité de la KB.
    KB root: /Users/vincentdolez/AI/KB/KB vincentdolez
    Artifacts: /tmp/kb-audit-artifacts.json
    Lis CLAUDE.md pour le routeur. Utilise structural_metrics du JSON.
    Teste 5 parcours réalistes. Évalue les _index.md.
    Produis ton rapport en JSON.

  # D3 — Congruence
  subagent_type: audit-congruence
  prompt: |
    Audite la congruence lexicale de la KB.
    KB root: /Users/vincentdolez/AI/KB/KB vincentdolez
    Artifacts: /tmp/kb-audit-artifacts.json
    Utilise vocab_fingerprints pour les termes distinctifs par layer.
    Lis des fichiers 08-recherche/ et des fichiers business pour construire les registres.
    Produis ton rapport en JSON.

  # D4 — Signal
  subagent_type: audit-signal
  prompt: |
    Audite le ratio signal/bruit de la KB.
    KB root: /Users/vincentdolez/AI/KB/KB vincentdolez
    Artifacts: /tmp/kb-audit-artifacts.json
    Utilise file_profiles pour le triage. Lis 15-20 fichiers en profondeur.
    Produis ton rapport en JSON.

  # D5 — AI-First
  subagent_type: audit-ai-first
  prompt: |
    Audite l'efficacité AI-first de la KB.
    KB root: /Users/vincentdolez/AI/KB/KB vincentdolez
    Artifacts: /tmp/kb-audit-artifacts.json
    Utilise file_profiles et structural_metrics.
    Lis 10-15 fichiers pour évaluer le frontmatter comme routing metadata.
    Produis ton rapport en JSON.
```

Si une seule dimension demandée, lancer uniquement l'agent correspondant.

### 4. Phase 3 — Synthèse

Quand les 5 agents ont répondu :

1. **Collecter** les rapports JSON de chaque agent
2. **Agréger** les scores → score global (moyenne pondérée)
3. **Croiser** les findings — un finding qui apparaît dans 2+ dimensions = priorité élevée
4. **Produire** le rapport final :

```markdown
# Audit sémantique KB — {date}

## Score global : {score}/100

| Dimension | Score | Verdict |
|---|---|---|
| D1 Alignement | {n}/100 | {verdict} |
| D2 Navigabilité | {n}/100 | {verdict} |
| D3 Congruence | {n}/100 | {verdict} |
| D4 Signal/Bruit | {n}/100 | {verdict} |
| D5 AI-First | {n}/100 | {verdict} |

## Synthèse croisée
{observations qui émergent du croisement des 5 dimensions}

## Actions prioritaires
### Critique
- {action} — impact sur {dimensions concernées}
### Warning
- {action}

## Rapport détaillé par dimension
{synthèse de chaque agent}
```

5. **Sauvegarder** le rapport dans `journal/audit-kb-{date}.md`

### 5. Règles orchestrateur

- **Pure orchestration** — ne jamais juger le contenu, déléguer aux agents
- **Parallèle** — les 5 agents sont indépendants, les lancer en parallèle
- **Croisement** — la valeur de l'orchestrateur est dans la synthèse croisée que les agents individuels ne peuvent pas faire
- **Artifacts éphémères** — le JSON dans /tmp est jetable, seul le rapport final est persisté
- **Pas de modification** — l'audit est read-only. Les corrections sont un chantier séparé.
- **Si un agent échoue** — signaler, produire le rapport partiel avec les dimensions disponibles

$ARGUMENTS
