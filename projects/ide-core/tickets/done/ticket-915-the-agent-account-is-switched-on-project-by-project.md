---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 1
id: ticket-915
plan: true
pr_number: 1036
priority: high
status: done
title: The agent account is switched on project by project, from the worktree declaration
type: feat
---

# ticket-915 — Le compte agent s'active projet par projet, depuis la déclaration `worktree`

## Objectif

Pouvoir faire tourner les agents d'**un seul** projet sous le compte dédié
(ADR-083), les autres restant sous le compte du backend, pour activer
l'isolation progressivement.

## Contexte

`AGENT_USER` (`config.py`, ticket-894) est un réglage global : renseigné, tout
appel du provider `agent_sdk` part sous ce compte (`agent_sdk.py`,
`compte = settings.agent_user`). Or les droits du compte agent ne sont posés
que sur les worktrees (`droits_worktree.py`, ticket-895). Allumer
`AGENT_USER` aujourd'hui ferait tourner ide-core et tous les projets sans
`worktree` sous un compte qui ne peut pas écrire dans leur dossier : tous
leurs runs échoueraient.

Le plan d'activation choisi le 09/11 : d'abord un projet à worktree peu actif,
un run réel vérifié, puis les autres. Il faut pour cela un interrupteur par
projet.

## Solution proposée

- `ConfigWorktree` (`models/worktree_config.py`) gagne un champ
  `compte_agent: bool = False`, validé par `worktree_politique.py` comme les
  autres clés (`_mal_type` sur un non-booléen).
- Le compte agent n'est utilisé que si **les deux** sont vrais :
  `AGENT_USER` renseigné et `worktree.compte_agent` déclaré par le projet du
  run. Sinon, environnement et CLI du compte du backend, exactement comme
  aujourd'hui.
- `accorder_droits_agent` (`run_dans_worktree.py`) suit la même condition.
- Les appels hors run d'un projet à worktree (chat, services de documentation,
  superviseur…) restent sous le compte du backend : au plan de lister ces
  chemins et de dire comment l'information « ce run est isolé » parvient au
  provider (la politique du run, lue une fois à l'ouverture).

## Critères d'acceptation

- [ ] `models/worktree_config.py` déclare `compte_agent` avec `False` pour
      défaut.
- [ ] Un test vérifie qu'une valeur non booléenne de `compte_agent` est
      refusée par la validation de la politique.
- [ ] Un test vérifie, avec des doubles, qu'avec `AGENT_USER` renseigné et un
      projet sans `compte_agent`, les options du provider n'utilisent ni
      l'environnement ni le CLI du compte agent.
- [ ] Un test vérifie, avec des doubles, qu'avec `AGENT_USER` renseigné et
      `compte_agent: true`, les options utilisent l'environnement du compte
      agent et `CLI_PARTAGE`.
- [ ] Un test vérifie qu'avec `AGENT_USER` vide, `compte_agent: true` ne
      change rien.
- [ ] Un test vérifie que `accorder_droits_agent` n'est pas appelé pour un
      projet sans `compte_agent`.

## Ce que ça ne fait pas

- N'active l'isolation sur aucun projet : la déclaration se fait à la main
  dans `agents.json`, qu'aucun agent n'écrit.
- Ne couvre pas les projets sans `worktree` ni ide-core.

## Dépendances

Aucune (894, 895 et 900 sont livrés).

## Estimation

1 jour.

## Risques

Un chemin d'appel qui construit ses options sans connaître le projet
retomberait sur le compte du backend : c'est le sens sûr (comportement
actuel), mais le plan doit les nommer pour qu'aucun ne croie être isolé.