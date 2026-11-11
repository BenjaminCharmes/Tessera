---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 2
id: ticket-934
plan: true
pr_number: 1053
priority: high
status: done
title: Under the dedicated agent account, the test command and the visual-check app
  run under AGENT_USER too
type: fix
---

# ticket-934 — Avec le compte dédié, la commande de test et l'app du contrôle visuel tournent aussi sous `AGENT_USER`

## Objectif

Que le code écrit par un agent ne s'exécute jamais sous le compte du backend
quand le projet a déclaré le compte dédié.

## Contexte

Audit du 11/11, vérifié sur `origin/develop`. Le ticket-915 lance le CLI de
l'agent sous `AGENT_USER` quand `worktree.compte_agent` est vrai
(`backend/src/tessera/models/worktree_config.py`, l. 38 ;
`backend/src/tessera/services/pipeline/assemblage_run.py`, l. 137 ;
`backend/src/tessera/services/providers/transport_agent.py`). Deux processus
du run exécutent pourtant ce code sous le compte du backend :

- **La commande de test** : `_lancer`
  (`backend/src/tessera/services/verification/test_runner.py`, l. 178-200)
  appelle `asyncio.create_subprocess_exec` directement. Un `conftest.py`,
  un `vitest.setup.ts` ou un script `pretest` écrit par le codeur s'exécute
  **avant la revue**, avec les droits du backend : coffre, `~/.claude/`,
  dépôt principal.
- **L'app du contrôle visuel** : `demarrer_processus`
  (`backend/src/tessera/services/verification/app_du_run.py`, l. 79-100),
  même lancement, sur le code du worktree.

`env_du_code_de_projet` retire déjà les secrets de l'environnement
(ticket-888) ; le compte reste celui du backend. La règle proposée de
`contraintes.md` (ADR-083) dit que le CLI part sous `AGENT_USER` et qu'un échec
donne `ProviderIndisponible`, jamais un repli sous le compte du backend : le
même principe vaut ici.

## Solution proposée

À trancher au tour de plan ; piste :

- Quand le run a déclaré le compte dédié et qu'`AGENT_USER` est renseigné,
  `test_runner` et `app_du_run` lancent leur processus par le
  `LanceurAgent` (`backend/src/tessera/services/providers/lanceur_agent.py`,
  `lanceur_windows.py`), environnement bâti de zéro, sans secret.
- Un échec de lancement sous `AGENT_USER` termine l'étape en échec
  d'environnement, jamais par un repli sous le compte du backend.
- Sans compte dédié, rien ne change.
- Le plan dit comment le groupe de processus (arrêt de l'arbre, minuteur,
  sortie capturée) se conserve sous le lanceur, et quels droits le compte
  dédié doit avoir sur `.venv`, `node_modules` et le cache de `uv`.

## Critères d'acceptation

- [ ] Un test vérifie, avec un lanceur double, que `test_runner.py` lance la
      commande par le lanceur du compte dédié quand le run l'a déclaré.
- [ ] Un test vérifie, avec un lanceur double, que `app_du_run.py` lance
      l'app par ce même lanceur quand le run l'a déclaré.
- [ ] Un test vérifie que, sans compte dédié, `test_runner.py` lance la
      commande comme aujourd'hui.
- [ ] Un test vérifie qu'un échec du lanceur ne retombe pas sur un lancement
      sous le compte du backend.
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit quels
      processus du run tournent sous `AGENT_USER`.

## Ce que ça ne fait pas

- Ne rend pas le compte dédié obligatoire : un projet sans
  `worktree.compte_agent` garde le comportement actuel.
- Ne change ni la CI ni les services déclarés du projet (`services`,
  ADR-042), lancés par l'utilisateur.

## Dépendances

Aucune ; s'appuie sur le ticket-915, mergé.

## Estimation

Deux jours.

## Risques

`test_runner.py` fait 519 lignes, au-dessus du plafond de 300 : le lancement
sous le compte dédié doit vivre dans un module voisin, sans faire grossir ce
fichier. Le lanceur Windows ne gère peut-être pas les groupes de processus
comme `options_de_lancement` : une suite qui ne s'arrête pas au délai serait
une régression.