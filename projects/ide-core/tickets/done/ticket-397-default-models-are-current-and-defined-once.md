---
id: ticket-397
title: "Default models are current and defined once, and ide-core runs its roles on the aligned models"
type: fix
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-12
---

# ticket-397 — Des modèles par défaut à jour, définis une seule fois

## Objectif

Qu'aucun rôle ne retombe sur un modèle périmé quand un `agents.json` ne le
déclare pas, et qu'ide-core tourne sur les modèles décidés le 2026-10-12.

## Contexte

Audit des modèles du 2026-10-12, à partir de `agent_calls` depuis le
2026-10-03 :
- **codeur** : `claude-sonnet-5-5` coûte autant que `claude-sonnet-4-6`
  (1,37 $ contre 1,35 $ par appel). Il demande moins de tours (1,38 contre
  1,51 par run, 69 % d'approbations au premier tour contre 65 %) et va
  environ 2 fois plus vite.
- **documentation sur Ollama** : 0 fichier dans 100 % des runs sur homelab,
  repo-health et démineur, contre environ 25 % sur Haiku (vigie, ide-core).
- **Appel réel** : `claude-sonnet-5-5` et `claude-opus-5-5` répondent sous
  leur nom avec le CLI embarqué 2.1.281. L'avertissement `unrecognized_model`
  n'est que cosmétique.

Plusieurs valeurs par défaut citent encore `claude-sonnet-4-6`, dispersées
dans le code :
- le manifeste par défaut d'un nouveau projet (`project_loader.py`) ;
- `security_auditor.py` et `validator.py` (`_MODEL`) ;
- `documentation.py` et `project_creator.py` (identifiant daté de Haiku) ;
- `project_from_template.py`, qui a ses propres constantes.

## Solution

1. Un module `backend/src/tessera/services/modeles_par_defaut.py` définit
   `MODELE_PRODUCTION` (`claude-sonnet-5-5`) et `MODELE_JUGEMENT`
   (`claude-haiku-4-5`). Tous les défauts ci-dessus l'importent.
2. Dans le manifeste par défaut, les rôles de production (codeur, architect,
   reviewer) ont `MODELE_PRODUCTION`, et les autres `MODELE_JUGEMENT`.
3. `projects/ide-core/agents.json` :
   - codeur et architect sur `claude-sonnet-5-5` ;
   - reviewer sur `claude-opus-5-5`, car ide-core porte tous les projets et
     ses relectures ont laissé passer 8 défauts corrigés à la main les 10 et
     11 octobre ;
   - le repli de project-analyzer sur `claude-sonnet-5-5`.

## Critères d'acceptation

- [x] Un test de `backend/tests/test_modeles_par_defaut.py` vérifie qu'aucun fichier de `backend/src/tessera/services/` hors `cost_calculator.py` ne cite `claude-sonnet-4-6` ni un identifiant daté de modèle
- [x] Un test de `backend/tests/test_modeles_par_defaut.py` vérifie que le manifeste par défaut d'un nouveau projet donne `MODELE_PRODUCTION` au codeur et `MODELE_JUGEMENT` au validateur
- [x] Un test de `backend/tests/test_modeles_par_defaut.py` vérifie que les modèles par défaut de l'audit sécurité et du validateur sont `MODELE_JUGEMENT`

## Ce que ça ne fait pas

- Ne retire pas `claude-sonnet-4-6` de la grille tarifaire : les coûts
  passés restent calculables.
- Ne change pas le validateur sur Ollama des projets qui l'ont choisi.
