# /lint — Health-check anti-drift KB

Audit périodique de l'intégrité structurelle et sémantique de la KB. Pensé comme un cron hebdo qui détecte les dérives avant qu'elles s'installent.

## Architecture

3 niveaux de profondeur, du plus rapide au plus lent :

| Niveau | Source | Couverture | Coût |
|---|---|---|---|
| **structurel** | `obsidian-nav --audit` (7 axes) | Liens cassés, frontmatter, drafts stale, dépendances, index, orphelins, statuts | Déterministe, secondes |
| **gouvernance** | Inline (checks spécifiques) | Symétrie `replaces`/`replaced_by`, statuts hors registre, tags pirates, inbox stale, `_index.md` sans markers | Déterministe, secondes |
| **sémantique** | `/kb-audit full` (5 agents LLM) | Alignement fondations, navigabilité, congruence, signal/bruit, AI-first | LLM, minutes |

## Protocole

### 1. Parser la commande

Argument attendu : `$ARGUMENTS`

| Arg | Comportement |
|---|---|
| (vide) ou `quick` | Niveaux **structurel + gouvernance** (déterministe, rapide) |
| `full` | Tout : structurel + gouvernance + sémantique |
| `semantic` | Seulement niveau sémantique (équivalent `/kb-audit full`) |
| `supersedes` | Seulement check symétrie `replaces`/`replaced_by` |
| `tags` | Seulement audit tags (registry vs usage réel) |
| `inbox` | Seulement état inbox (volume, age, items stales) |
| `indexes` | Seulement état `_index.md` (markers présents, désynchronisés) |

### 2. Niveau structurel

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/obsidian-nav/scripts"
python3 "$SCRIPTS/kb_report.py" --audit
```

Capture le rapport. Les 7 axes : frontmatter manquants, liens cassés, drafts >30j, dépendances cassées, index obsolètes, orphelins, transitions de statut anormales.

### 3. Niveau gouvernance

#### 3a. Symétrie `replaces` / `replaced_by`

Pour chaque fichier `.md` de la KB :

```bash
# Pseudocode
for f in *.md:
  replaces = parse_yaml_list(f, "replaces")
  replaced_by = parse_yaml_list(f, "replaced_by")
  status = parse_yaml_value(f, "status")

  # Check 1 : si replaces=[X], alors X.replaced_by doit contenir f
  for x in replaces:
    if f not in parse_yaml_list(x, "replaced_by"):
      ASYMMETRIE("replaces vers " + x + " sans réciproque")

  # Check 2 : si replaced_by=[Y], alors Y.replaces doit contenir f
  for y in replaced_by:
    if f not in parse_yaml_list(y, "replaces"):
      ASYMMETRIE("replaced_by depuis " + y + " sans réciproque")

  # Check 3 : si status=superseded, replaced_by doit être non-vide
  if status == "superseded" and not replaced_by:
    INCOHERENCE("status superseded sans replaced_by")

  # Check 4 : si replaced_by non-vide, status doit être superseded
  if replaced_by and status != "superseded":
    INCOHERENCE("replaced_by présent mais status != superseded (status=" + status + ")")
```

Rapporter chaque incohérence avec chemin du fichier et nature du problème.

#### 3b. Statuts hors registre

Liste des statuts valides (cf. `CONTRIBUTING.md`) :
`backlog`, `exploration`, `draft`, `actif`, `en-pause`, `terminé`, `superseded`, `abandonné`, `archivé`

```bash
grep -rh "^status:" --include="*.md" KB/ | sort -u
# Tout statut qui n'est pas dans la liste = anomalie
```

Rapporter les fichiers avec statut hors registre. Exemples connus : `status: superseded-by-010` (bricolage), `status: en-pause` (valide), `status: publié` (à migrer vers `actif`).

#### 3c. Tags pirates

```bash
# Tags actifs du registry (cf. hook-tag-validate.sh)
REGISTRY="KB/00-fondations/tags-registry.md"
valid=$(awk '
  /^## Catégories/ {capture=1; next}
  /^## Tags retirés/ {capture=0}
  capture {
    while (match($0, /`[^`]+`/)) {
      print substr($0, RSTART+1, RLENGTH-2)
      $0 = substr($0, RSTART+RLENGTH)
    }
  }
' "$REGISTRY" | sort -u)

# Tags réellement utilisés en frontmatter
used=$(grep -rh "^tags:" --include="*.md" KB/ | \
       sed -E 's/^tags:[[:space:]]*\[//; s/\][[:space:]]*$//' | \
       tr ',' '\n' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | \
       grep -v '^$' | sort -u)

# Diff
echo "$used" | grep -Fxv -f <(echo "$valid")  # = tags pirates
```

Rapporter top 20 tags pirates par fréquence d'usage. Suggérer pour chacun : `intégrer au registry`, `remplacer par <tag existant>`, ou `kill`.

#### 3d. Inbox stale

```bash
find KB/inbox -maxdepth 1 -name "*.md" -not -name "_index.md" | while read f; do
  age=$(( ($(date +%s) - $(stat -f %B "$f")) / 86400 ))
  echo "$age	$f"
done | sort -rn
```

Rapporter :
- Volume total inbox
- Plus ancien item (en jours)
- Items >30 jours (à trier en priorité)
- Suggestion : lancer `/inbox` si >5 items ou plus ancien >30j

#### 3e. `_index.md` markers

```bash
find KB -name "_index.md" -not -path "*/.git/*" | while read f; do
  if grep -q "AUTO:BEGIN" "$f"; then
    echo "AUTO     $f"
  else
    count=$(find "$(dirname "$f")" -maxdepth 1 -name "*.md" -not -name "_index.md" | wc -l)
    if [ "$count" -ge 5 ]; then
      echo "CANDIDAT $f (≥5 fichiers frères, candidat à markérisation)"
    fi
  fi
done
```

Rapporter les `_index.md` candidats à markérisation (≥5 frères et sans markers).

### 4. Niveau sémantique (si demandé)

Déléguer à `/kb-audit full` qui orchestre les 5 agents LLM. Réutiliser son rapport tel quel.

### 5. Synthèse

Produire un rapport markdown structuré :

```markdown
# /lint — Rapport YYYY-MM-DD

## Synthèse
- N anomalies critiques (rouges)
- N warnings (oranges)
- N suggestions (vertes)

## Structurel (obsidian-nav --audit)
[7 axes, status par axe]

## Gouvernance
### Symétrie supersedes
[liste asymétries / OK]

### Statuts hors registre
[liste / OK]

### Tags pirates (top 20)
[liste avec fréquence et suggestion]

### Inbox
[volume, age, items prioritaires]

### Index markers
[candidats à markérisation]

## Sémantique (si --full)
[résumé /kb-audit]

## Recommandations priorisées
1. [Action la plus urgente]
2. [...]
```

### 6. Persistance

Sauvegarder le rapport dans `journal/lint/YYYY-MM-DD.md`. Permet de comparer entre runs et tracer l'évolution de la santé KB.

## Règles

- **Lecture seule** : `/lint` ne modifie jamais de fichier KB. Il rapporte uniquement.
- **Pas de fix automatique** : les anomalies sont décrites, pas réparées. La décision reste humaine.
- **Une recommandation = un slash command** : si une anomalie peut être traitée par `/inbox`, le rapport le mentionne explicitement.
- **Pas de noise** : si une catégorie est saine, dire "OK" en une ligne. Pas de tableau vide.

## Planification

Pour automatiser un run hebdo, utiliser le skill `schedule` :

```
schedule weekly: "/lint quick" → journal/lint/auto-{date}.md
```

Le run automatique se cantonne à `quick` (déterministe) pour éviter les coûts LLM réguliers. Le `full` reste manuel sur demande.

$ARGUMENTS
