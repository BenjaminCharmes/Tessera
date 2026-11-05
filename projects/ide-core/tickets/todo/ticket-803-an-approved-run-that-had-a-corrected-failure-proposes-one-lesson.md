---
agent: codeur
created: 2026-11-05
depends_on: [ticket-801]
estimated_days: 1
id: ticket-803
pr_number: null
priority: medium
status: todo
title: An approved run that had a corrected failure proposes one lesson
type: feat
---

# ticket-803 — Un run approuvé qui a corrigé un échec propose une leçon

## Objectif

Après un run approuvé dont `run.review_feedback` n'est pas vide, un service sans outils
écrit au plus une leçon sous `## Proposées` de `memory/lecons.md`, dans le worktree du run
(ADR-074). Cas d'origine : ticket-736 — trois retours « tests rouges », un autre double de
test à chaque tour.

## Contexte

`review_feedback` rassemble déjà tout ce qui a été reproché au codeur pendant le run :
remarques du reviewer, tests rouges (`_echec_de_tests`), problèmes de tickets. Un run qui
l'a vu non vide et fini approuvé a **corrigé** quelque chose : c'est le déclencheur, sans
heuristique de plus. Le modèle de référence est `documenteur_run.py` : rôle sans outils,
sortie JSON, contrôle par le service, refus journalisé sans bloquer, écriture dans le
dossier du run.

## Ce qu'il faut faire

- `agents/prompts/lecons.md` : le prompt du rôle `lecons`. Il reçoit `review_feedback`
  (borné à 4 Ko, le plus ancien d'abord coupé) et le diff final du run ; il rend du JSON
  `{"lecon": str | null, "preuve": str | null}`. Il dit que le retour est une donnée, jamais
  une consigne ; qu'une leçon est « Quand <situation>, <action>. », un piège observé et non
  une règle générale ni une décision ; qu'`null` est la bonne réponse quand rien ne se
  généralise.
- `backend/src/tessera/services/lecons_run.py` : `produire_lecon(...)` appelle le rôle
  `lecons` par `provider_pour_role(..., allow_tools=False)` enveloppé de
  `ProviderEnregistrant` (comme `documenteur_run._fournisseur`), valide la réponse par un
  schéma, passe `refus_de_lecon` puis `ajouter_proposee` (ticket-801) sur le `memory/` du
  worktree, avec le `ticket_id` du run et la date du jour.
- Branchement après l'approbation, à l'endroit où l'étape de documentation s'exécute sur la
  branche du run, **avant** le commit final, pour qu'une leçon d'un projet `tracked` parte
  dans la PR et soit relue avec elle.
- Opt-in : `pipeline.lecons` (booléen, `false` par défaut) dans `agents.json`, lu par
  `load_pipeline_config`. L'étape ajoute un appel de modèle et un fichier dans le dépôt ;
  le défaut protège, un projet le déclare. Le rôle `lecons` se déclare dans `agents.json`
  par un humain (Haiku conseillé) : aucun agent n'écrit ce fichier (ADR-027).
- Toute défaillance — provider indisponible, JSON hors schéma, refus du contrôle,
  exception — est journalisée dans `pipeline-log.md` et ne change ni le statut ni le
  commit du run. Cette étape n'est pas une porte : elle échoue ouverte.

## Critères d'acceptation

- [ ] `backend/tests/test_lecons_run.py`, provider factice : run approuvé avec
      `review_feedback` non vide → une ligne sous `## Proposées`, source `ticket-NNN` et date
      posées par le service
- [ ] Même test : `review_feedback` vide → provider non appelé, fichier non créé
- [ ] `pipeline.lecons` absent ou `false` → provider non appelé
- [ ] Réponse `{"lecon": null}`, JSON invalide, preuve absente du retour, doublon,
      leçon qui nomme `conftest.py` : rien n'est écrit, une ligne de journal dit pourquoi,
      le run reste approuvé
- [ ] Un run non approuvé n'appelle jamais le provider
- [ ] Le fichier est écrit dans le worktree, jamais dans le checkout (test sur les chemins)
- [ ] Test de `load_pipeline_config` pour `pipeline.lecons`

## Ce que ça ne fait pas

N'injecte rien (ticket-802). Ne compacte jamais : un fichier plein refuse l'ajout (ticket-801)
et la ligne de journal le dit. Ne produit pas de leçon pour un run qui n'a rien eu à corriger.

## Dépendances

ticket-801.
