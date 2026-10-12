---
agent: codeur
created: 2026-10-12
depends_on: []
estimated_days: 0.5
id: ticket-405
pr_number: null
priority: medium
status: done
title: 'Delivery phase 2 survives a slow GitHub: late CI checks are awaited, and a
  network error re-reads the PR before giving up'
type: fix
---

# ticket-405 — La phase 2 de livraison résiste à un GitHub lent

## Objectif

Qu'une PR que GitHub finit par passer ou par merger ne soit jamais déclarée
en échec parce que GitHub a répondu lentement.

## Contexte

Deux cas le 2026-10-12, pendant que l'API GitHub renvoyait des 504 :
- **portfolio, ticket-019 (13:18 UTC)** : « PR #16 non mergée : CI none ». La
  CI du dépôt existe et passe, mais ses checks se sont inscrits après les
  120 s du délai de grâce (`_GRACE_CI_S`,
  `backend/src/tessera/services/livraison.py`). `none` est alors devenu un
  verdict final. Il a fallu merger à la main.
- **repo-health, ticket-006 (13:27 UTC)** : « PR #8 non mergée : erreur
  inattendue : » (message vide). L'appel de merge a levé
  `httpx.ReadTimeout`, mais GitHub avait bien mergé la PR. CIWatcher l'a
  pourtant signalée en échec : la PR est mergée, et le journal dit le
  contraire.

## Solution proposée

1. Le délai de grâce devient un réglage `CI_GRACE_S`, défaut 300 s. Avant
   de conclure `none`, la livraison vérifie qu'aucun workflow n'est déclaré
   dans le dépôt (`GET /repos/{repo}/actions/workflows`, `total_count == 0`).
   Si des workflows existent, `none` reste `pending` jusqu'à
   `attente_ci_max_s`.
2. Sur une erreur réseau pendant la phase 2 (`httpx.TransportError`, dont
   `ReadTimeout`), CIWatcher relit l'état de la PR avant de conclure. Une PR
   mergée est un succès (`merged=True`, journal « mergée malgré une erreur
   réseau »).
3. Le message d'échec nomme toujours le type de l'exception
   (`ReadTimeout`), même quand son texte est vide.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_livraison.py` vérifie qu'avec des workflows déclarés, `none` après le délai de grâce reste `pending` et que la livraison attend un verdict
- [ ] Un test de `backend/tests/test_livraison.py` vérifie qu'un dépôt sans aucun workflow conclut `none` après le délai de grâce, comme aujourd'hui
- [ ] Un test de `backend/tests/test_ci_watcher.py` vérifie qu'un `httpx.ReadTimeout` levé pendant le merge, suivi d'une PR lue comme mergée, donne `merged=True` et une ligne de journal qui le dit
- [ ] Un test de `backend/tests/test_ci_watcher.py` vérifie qu'un échec par exception à message vide écrit le nom de l'exception dans le journal

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Ce que ça ne fait pas

- Ne relance pas une CI rouge.