---
title: "Gouvernance de la KB"
type: fondation
status: actif
created: 2026-02-17
updated: 2026-02-17
owner: shared
tags: [gouvernance, conventions, meta]
consumed_by: [claude-ai, claude-code, human]
---

# Gouvernance de la base de connaissances

Ce fichier définit les règles d'intervention sur cette KB.
Comme un dépôt de code : format, conventions, cycle de vie, review, hygiène.

---

## Format : Markdown + YAML Frontmatter

Le YAML frontmatter ajoute une couche de métadonnées structurées que les agents AI
peuvent parser programmatiquement. Obsidian le supporte nativement. Git le versionne
proprement. C'est le sweet spot entre lisibilité humaine et exploitabilité machine.

**Alternatives écartées** (voir [[01-strategie/decisions/002-format-kb]]) :
MDX (incompatible Obsidian), JSON+Markdown (overkill), Notion/Coda (pas Git), Markdown pur (pas de métadonnées).

## Schéma frontmatter

```yaml
---
title: "Titre lisible du document"
type: fondation | strategie | marque | spec | ops | decision | prompt | chantier | template | journal | index | person
status: backlog | exploration | draft | actif | en-pause | terminé | superseded | abandonné | archivé
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: vincent | claude | shared
tags: [tag1, tag2]
depends_on: [chemin/relatif/fichier]
replaces: [chemin/relatif/fichier]
replaced_by: [chemin/relatif/fichier]
consumed_by: [claude-ai, claude-code, human]
---
```

### Champs obligatoires

`title`, `type`, `status`, `created`, `updated`

### Champs optionnels

- `owner` : qui maintient ce document
- `tags` : pour la recherche et le filtrage
- `depends_on` : documents prérequis (liens de contexte pour l'IA)
- `replaces` : documents que ce fichier remplace totalement (le remplacé doit passer en `status: superseded` avec `replaced_by` symétrique pointant ici)
- `replaced_by` : documents qui remplacent celui-ci (utilisé conjointement avec `status: superseded`)
- `consumed_by` : qui lit ce document (aide à calibrer le niveau de détail et au routage agent)

**Sémantique `replaces` / `replaced_by`** : usage **strict** pour remplacement total uniquement. Pour les supersedes partiels ou sémantiques (un §, un aspect, une cible), rester en prose dans une section narrative dédiée — ne pas surcharger les champs frontmatter.

### Champs chantier (type: chantier)

- `priority` : P0 | P1 | P2 — urgence et impact
- `target` : trimestre cible (ex: Q1-2026)
- `completed` : YYYY-MM-DD — date de complétion effective (quand status = terminé)
- `progress` : 0-100 — avancement estimé (optionnel, pour les chantiers actifs)
- `blocked_by` : documents ou chantiers bloquants
- `deliverables` : liste des livrables attendus

### Champs contact (type: person)

- `organization` : entreprise ou structure
- `role` : fonction / poste
- `relation` : prescripteur | prospect | partenaire | reseau | classe
- `channel` : linkedin | email | tel | direct
- `pipeline` : identifie | contacte | en-conversation | qualifie | classe
- `next_action` : prochaine action concrète
- `next_action_date` : YYYY-MM-DD

### Vocabulaire `consumed_by`

| Valeur | Sémantique |
|---|---|
| `human` | Lu par Vincent (review, décision, référence) |
| `claude-ai` | Injecté comme contexte dans une conversation Claude |
| `claude-code` | Consommé par un agent Claude Code (skills, commands, agents) |
| `article-cadrage` | Input du Flow 1 — agent cadrage article |
| `article-redaction` | Input du Flow 2 — agent rédaction |
| `article-qualite` | Input du Flow 3 — agent qualité |
| `article-derivation` | Input du Flow 4 — agent dérivation |
| `linkedin` | Publié ou dérivé pour LinkedIn |
| `vincentdolez-fr` | Publié ou dérivé pour le site |

---

## Nommage

- **Fichiers** : kebab-case, en français (`modele-offres.md`, pas `offerModel.md`)
- **Dossiers** : préfixe numérique pour l'ordre (`00-fondations/`, `07-prompts/`)
- **Index** : chaque dossier contient un `_index.md` (ou `README.md` pour les entités)
- **Templates** : dans `_templates/`, avec des placeholders `{{variable}}`

## Liens

- **Internes** : wiki-links Obsidian `[[chemin/fichier]]`
- **Externes** : Markdown standard `[texte](url)`

---

## Cycle de vie d'un document

```
backlog  ─┐
          ├→  exploration  ─┐
          └→  draft  ───────┤→  actif  →  terminé  →  archivé
                            │              │
                            │              └→  superseded  (remplacé par un autre doc spécifique)
                            └→  en-pause / abandonné  (états transverses)
```

| Statut | Signification | Qui peut modifier |
|---|---|---|
| `backlog` | Identifié, pas encore démarré | Tout le monde |
| `exploration` | Délibération ouverte, brainstorm, hypothèses en cours — peut vivre des mois sans pression de livrable | Tout le monde |
| `draft` | Livrable en cours de rédaction, contenu incomplet — pression de finir | Tout le monde |
| `actif` | Source de vérité validée / chantier en cours / décision en vigueur | Avec review |
| `en-pause` | Suspendu volontairement, reprise prévue | Avec review |
| `terminé` | Livré / objectif atteint (chantiers, specs ponctuelles) | Avec review |
| `superseded` | Remplacé par un autre document spécifique (champ `replaced_by` obligatoire) | Ne pas modifier le contenu |
| `abandonné` | Annulé, non pertinent — conservé pour historique | Ne pas modifier |
| `archivé` | Obsolète, conservé pour historique | Ne pas modifier |

### Distinction `exploration` vs `draft`

- **`exploration`** : tu cherches, tu réfléchis à voix haute, tu compares des options, tu n'es pas pressé d'aboutir. Un brainstorm, une délibération pour/contre, une hypothèse de positionnement, une exploration de marché. Vit aussi longtemps que nécessaire.
- **`draft`** : tu sais ce que tu veux livrer, le contenu est en cours de rédaction. Un article, une spec, une ADR en cours de formulation. Existe pour devenir `actif` (ou `terminé` pour un livrable ponctuel).

### Distinction `superseded` vs `archivé`

- **`superseded`** : le doc est remplacé par un successeur **identifié et nommé** (`replaced_by`). Le lien de filiation est explicite.
- **`archivé`** : le doc est obsolète sans successeur précis, conservé pour historique.

### Règles de transition

1. Créer un document futur en `status: backlog` (ou `draft` / `exploration` si le travail commence immédiatement)
2. Démarrer en `exploration` si la délibération est ouverte sans pression de livrable
3. Démarrer en `draft` si le livrable est identifié et la rédaction commence
4. Une `exploration` peut accoucher d'un `draft` (ou plusieurs) puis d'un `actif`
5. Passer en `actif` quand le contenu est fiable et sert de source de vérité
6. Passer en `terminé` quand l'objectif est atteint (pertinent pour chantiers, sprints)
7. Passer en `superseded` quand un autre document spécifique remplace celui-ci totalement : renseigner `replaced_by` côté ancien, `replaces` côté nouveau (symétrie obligatoire)
8. Mettre à jour `updated` à chaque modification significative
9. Archiver (`archivé`) quand le document est obsolète sans successeur identifié

---

## Modèle éditorial

**Vincent** décide, donne les consignes, valide.
**Claude** rédige, structure, maintient, signale les incohérences.

Ce repo n'est pas un wiki passif. C'est un **asset technique vivant** —
le socle de context engineering de tout le projet. Il évolue à chaque conversation,
chaque décision, chaque livraison.

---

## Règles d'intervention

### Protocole agent (obligatoire à chaque session)

```
1. LIRE   CLAUDE.md + CONTRIBUTING.md
2. LIRE   _index.md du domaine concerné
3. LIRE   depends_on des fichiers à modifier
4. ÉCRIRE en respectant le schéma frontmatter
5. MAJ    updated, journal, index impactés
```

Ce protocole s'applique à toute session — conversation Cowork, Claude Code, ou autre agent.
Pas de raccourci. Pas d'exception.

### Pour les agents AI

- **Toujours** exécuter le protocole ci-dessus en premier
- **Ne jamais** modifier un document `archivé`
- **Ne jamais** créer un fichier hors de la structure existante sans en discuter
- **Signaler** les incohérences détectées (liens cassés, infos contradictoires, données obsolètes)
- **Proposer** des mises à jour quand le contenu d'un fichier diverge de la réalité du projet
- **Logger** les changements structurels dans `journal/`

### Pour les humains

- Relire l'`_index.md` du domaine avant d'ajouter un fichier
- Utiliser les templates dans `_templates/` pour tout nouveau document
- Vérifier les liens wiki après modification (graph Obsidian)
- Mettre à jour le journal (`journal/`) pour les changements structurels

---

## Review et hygiène

### Revue périodique

| Fréquence | Quoi | Objectif |
|---|---|---|
| Hebdomadaire | `01-strategie/chantiers/`, `01-strategie/backlog` | Priorisation, avancement |
| Mensuelle | `01-strategie/`, `04-contenu/calendrier` | Actualité des plans |
| Trimestrielle | `02-marque/`, `07-prompts/` | Cohérence voix/prompts |
| Semestrielle | `00-fondations/` | Validité des fondations |
| Continue | `journal/` | Traçabilité |

### Checklist de review

- [ ] Liens wiki tous fonctionnels (graph Obsidian, pas de nœuds orphelins)
- [ ] Pas de fichier `draft` oublié depuis > 1 mois
- [ ] `depends_on` cohérent (les dépendances existent et sont à jour)
- [ ] Pas de contradiction entre fichiers du même domaine
- [ ] Prompts (`07-prompts/`) alignés avec les documents sources
- [ ] `_index.md` de chaque domaine à jour (tous les fichiers listés)

### Évolution de la structure

Ajouter un nouveau domaine (dossier numéroté) est une décision structurelle.
Elle doit être documentée dans une ADR (`01-strategie/decisions/`) et l'`_index.md` racine mis à jour.

---

## Outillage futur

Ce dépôt KB pourra être équipé de :

- **`.claude/`** — Configuration Claude Code pour ce vault (commandes, skills, agents dédiés)
- **Git** — Versioning complet, diff, historique, branches pour les refontes majeures
- **CI** — Vérification automatique (liens cassés, frontmatter valide, fichiers orphelins)
- **Scripts** — Génération d'index, statistiques de couverture, détection d'incohérences

L'objectif à terme : traiter cette KB exactement comme un dépôt de code,
avec la même rigueur et les mêmes outils de qualité.
