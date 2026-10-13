---
id: ticket-415
title: "A delivery that fails after opening its PR names its cause and still hands the PR to the CI watcher"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-13
plan: true
---

# ticket-415 — Une livraison qui échoue dit pourquoi, et ne lâche pas sa PR

## Objectif

Qu'une exception pendant la phase 1 de livraison laisse un motif lisible, et
qu'une PR déjà ouverte soit quand même confiée au `CIWatcher` au lieu de
rester orpheline.

## Contexte

Le 2026-10-13 à 12:13 UTC, sur `curio` (ticket-008, approuvé) :
`pipeline-log.md` écrit « livraison: arrêt — Livraison interrompue : » —
message **vide** — et l'évènement `livraison_done` porte
`{"arret": "Livraison interrompue : ", "pr_number": null}`. Pourtant la
PR #13 avait bien été ouverte et la branche poussée. Faute de `pr_number`,
la phase 2 (attente CI, merge) n'a jamais démarré : la PR est restée
ouverte jusqu'à un merge manuel.

`routers/orchestrator.py` (fonction `livrer`, vers la ligne 480) attrape
`Exception` et ne garde que `str(exc)` ; une exception sans message
(`asyncio.TimeoutError`, `CancelledError` relayée, certaines erreurs
réseau) donne une chaîne vide, et le `_logger.warning("livraison_echouee")`
n'enregistre ni le type ni la pile. Le PC sortait d'une veille de deux
heures : une coupure réseau ou un délai est plausible, mais rien ne permet
de le savoir.

## Solution proposée

- Un utilitaire `decrire_exception(exc) -> str` : `str(exc)` s'il n'est pas
  vide, sinon le nom du type (`TimeoutError`), toujours préfixé du type quand
  le message ne le contient pas.
- `livrer` l'utilise pour `arret`, et journalise avec `exc_info=True`.
- Si l'exception survient **après** l'ouverture de la PR (le service connaît
  alors son numéro), `Livraison` porte ce `pr_number` et la phase 2 est
  confiée au `CIWatcher` comme pour une livraison réussie. À établir au tour
  de plan : où le numéro de PR est connu dans `livrer_phase_1`
  (`services/livraison.py`) et comment le remonter sans le perdre dans
  l'exception (attribut sur l'exception, ou résultat partiel).

## Critères d'acceptation

- [ ] Un test vérifie que `decrire_exception(TimeoutError())` renvoie une
      chaîne non vide contenant `TimeoutError`
- [ ] Un test vérifie qu'une exception sans message levée par
      `livrer_phase_1` produit un `arret` qui nomme son type
- [ ] Un test vérifie qu'une exception levée après l'ouverture de la PR donne
      une `Livraison` qui porte le `pr_number` de cette PR
- [ ] Un test vérifie que, dans ce cas, la surveillance de phase 2 est
      demandée pour cette PR
- [ ] Le journal `livraison_echouee` est émis avec `exc_info`

## Dépendances

Aucune.
