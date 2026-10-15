---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 0.5
id: ticket-455
pr_number: 471
priority: high
status: done
title: A PR opened despite a lost response is found again and handed to the CI watcher
type: fix
---

# ticket-455 — Une PR ouverte malgré une réponse perdue est retrouvée

## Objectif

Quand la réponse de GitHub à l'ouverture d'une PR se perd (timeout), Tessera
retrouve la PR par sa branche et la confie au CIWatcher, au lieu de la
laisser orpheline.

## Contexte

make-your-call, 15/10, 11:34:32 : « [ticket-008] livraison : arrêt —
Livraison interrompue : ReadTimeout ». La PR #20
(`ticket-008-a-shared-footer-gives-a-real-contact-address-and`) a pourtant
bien été ouverte. Personne ne la surveille : elle ne se mergera jamais
seule.

`_livraison_interrompue` dans `backend/src/tessera/routers/orchestrator.py`
garde le numéro de PR seulement pour une `LivraisonInterrompue`, levée
**après** l'ouverture connue de la PR (`pr_orpheline`). Une erreur réseau
pendant l'appel d'ouverture lui-même ne porte aucun numéro : la livraison
s'arrête sans PR.

## Solution proposée

Sur une erreur de transport (`httpx.TransportError`, dont `ReadTimeout`)
pendant la phase 1, et sans numéro de PR connu, chercher une PR ouverte dont
la branche de tête est celle du run (`GET /pulls?head=<owner>:<branche>&state=open`).
Si elle existe, la traiter comme une `LivraisonInterrompue` avec son numéro
(`pr_orpheline=True`) : elle passe au CIWatcher. Sinon, comportement actuel.

## Critères d'acceptation

- [ ] Un test simule un `ReadTimeout` à l'ouverture de la PR alors que GitHub
      liste une PR ouverte pour la branche, et vérifie que la livraison
      porte ce `pr_number` avec `pr_orpheline=True`
- [ ] Un test vérifie que, sans PR ouverte pour la branche, la livraison
      reste un arrêt sans `pr_number`
- [ ] Un test vérifie qu'une erreur pendant la recherche elle-même garde
      l'arrêt d'origine, sans lever

## Ce que ça ne fait pas

- Ne rattrape pas la PR #20 de make-your-call (faite à la main).