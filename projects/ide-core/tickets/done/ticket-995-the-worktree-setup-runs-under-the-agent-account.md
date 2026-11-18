---
agent: codeur
depends_on: []
id: ticket-995
pr_number: 1153
preuve_reelle: true
priority: critical
status: done
title: The worktree setup runs under the agent account
type: fix
---

## Signalement

- Audit sans contexte du 17/11, constat C1 (CRITICAL). Bloque la release.

## Contexte

`services/pipeline/preparation_worktree.py` lance `worktree.setup` (`npm ci`,
`uv sync`…) par `TestRunnerService(cwd=None, …)`, sans `compte_agent` : la
commande tourne sous le compte du backend, celui de l'utilisateur.
`services/worktrees/run_worktree.py`, `_ajouter`, reprend la branche du ticket
quand elle existe ; un run non approuvé y a commité le travail de l'agent
(ADR-018).

Scénario : au run 1, l'agent (sous `tessera-agent`) ajoute un `preinstall` à
`package.json`, un `.npmrc` (`script-shell`, `node-options`) ou un hook de
build Python. Le run finit `blocked`, commité. Au run suivant, `npm ci`
exécute ce code sous le compte de l'utilisateur : `.env`, coffre, `~/.ssh`.

Vu en vrai le 17/11 : la préparation des runs Serpent `02d9b72d` à `ad42dba3`
a tourné sur la branche reprise `ticket-009-…`, qui portait dix commits
d'agent.

## Ce qu'il faut faire

- Quand le projet déclare `worktree.compte_agent` et que `AGENT_USER` est
  renseigné, la préparation part sous le compte agent, comme les tests
  (`lancer_sous_compte`, ADR-085), sans repli : un échec de lancement met le
  run en `blocked`.
- Le compte doit pouvoir écrire `node_modules` / `.venv` : la préparation
  ouvre et clôt un appel (`ouvrir_appel` / `clore_appel`) comme une étape de
  test.
- `chaine_python.py` : sa docstring dit que le setup tourne sous le compte du
  backend ; la mettre à jour.

## Critères d'acceptation

- [ ] Test : projet `compte_agent` + `AGENT_USER` — la commande de préparation
      passe par le lanceur du compte, jamais par `asyncio.create_subprocess_exec`.
- [ ] Test : échec du lanceur — préparation en échec, run `blocked`, aucun
      repli.
- [ ] Test : projet sans `compte_agent` — comportement inchangé.

## Preuve réelle

Après merge et redémarrage : `npm ci` de Serpent ticket-009 tourne sous
`tessera-agent` (propriétaire des fichiers de `node_modules`).

## Ce que ça ne fait pas

- Ne rejette pas une branche reprise : le travail de l'agent reste relu par
  les portes.