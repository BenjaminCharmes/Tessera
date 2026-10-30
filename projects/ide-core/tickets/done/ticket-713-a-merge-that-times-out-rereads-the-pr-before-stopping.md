---
agent: codeur
created: 2026-10-30
depends_on: []
estimated_days: 0.5
id: ticket-713
pr_number: null
priority: high
status: done
title: A merge request that times out rereads the PR before stopping the delivery
type: fix
---

# ticket-713 — Un merge qui expire relit la PR avant d'arrêter la livraison

## Objectif
Quand l'appel de merge à GitHub expire alors que GitHub a bien mergé, la
livraison doit le constater et finir en « mergée », pas en arrêt.

## Contexte
Le 29/10, sur Curio (`merge_without_ci`), la livraison du ticket-047 s'est
arrêtée sur un `ReadTimeout`, alors que la PR était mergée. Il a fallu la
reprendre à la main. `merge_pull_request`
(`backend/src/tessera/services/github_service.py`) laisse remonter l'erreur
réseau, et `_merger` (`backend/src/tessera/services/livraison.py`) la
transforme en arrêt. `CIWatcher` traite déjà les `httpx.TransportError`
(ticket-405), mais pas ce chemin direct.

## Solution proposée
Sur une `httpx.TransportError` levée par le merge, relire la PR avec
`get_pull_request_status` :
- `merged` : la livraison finit mergée, et l'étape le dit (« mergée — confirmée
  après une erreur réseau ») ;
- un autre état, ou une relecture qui échoue aussi : l'arrêt reste, et son
  message nomme l'erreur réseau.

Un 405 ou un 409 (refus de GitHub) ne change pas : ce n'est pas une erreur
réseau.

## Critères d'acceptation
- [ ] `test_merge_timeout_on_a_merged_pr_ends_merged` (dans `backend/tests/test_livraison.py`) : le merge lève `httpx.ReadTimeout`, la relecture rend `merged`, et la `Livraison` a `merged=True`
- [ ] `test_merge_timeout_on_an_open_pr_stops` : la relecture rend `open`, et la `Livraison` a un `arret` qui nomme l'erreur réseau
- [ ] `test_merge_timeout_and_failed_reread_stops` : la relecture lève aussi, et la `Livraison` a un `arret`, sans exception remontée
- [ ] `test_merge_refusal_is_not_reread` : une `HTTPStatusError` 405 donne l'arrêt existant, sans appel à `get_pull_request_status`

## Ce que ça ne fait pas
- Ne traite pas les tests rouges après rebase du ticket-052 de Curio, qui
  n'ont pas été reproduits à la main : sans cas reproductible, rien à corriger