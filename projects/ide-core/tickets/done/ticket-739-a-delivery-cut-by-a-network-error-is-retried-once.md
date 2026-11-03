---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-739
pr_number: null
priority: medium
status: done
title: A delivery cut by a network error is retried once
type: fix
---

# ticket-739 — Une livraison coupée par une erreur réseau est retentée une fois

## Objectif

Une PR approuvée, à CI verte, n'est plus laissée ouverte parce qu'une seule requête
GitHub a perdu sa réponse.

## Contexte

03/11, ticket-702 : `livraison: arrêt — PR #838 non mergée : erreur inattendue :
RemoteProtocolError: Server disconnected without sending a response`. La CI était
verte, la PR CLEAN ; elle a été mergée à la main.

`_surveiller_impl` (`backend/src/tessera/services/ci_watcher.py`) attrape déjà
`httpx.TransportError` et relit la PR (ticket-405) : mergée, c'est un succès. Non
mergée, il conclut aussitôt à l'échec. Or rejouer la phase 2 est sûr : elle relit
la CI, refuse une tête qui n'est plus `pushed_sha`, et le merge est lié à
`pushed_sha` (ADR-039).

## Solution proposée

- Sur `httpx.TransportError` avec une PR relue non mergée, rejouer
  `_livrer_et_emettre` **une** fois, dans le délai restant de la phase 2.
- Une seconde erreur, ou toute autre exception, garde le comportement actuel :
  échec émis, PR laissée ouverte.
- Le journal dit qu'une nouvelle tentative a eu lieu et pourquoi.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles, qu'une `httpx.TransportError` suivie d'une
      PR non mergée relance la phase 2, et que la seconde tentative réussie émet un
      succès sans échec
- [ ] Un test vérifie que deux `httpx.TransportError` de suite émettent l'échec, et
      que la phase 2 n'a été appelée que deux fois
- [ ] Un test vérifie qu'une exception autre que `httpx.TransportError` n'est pas
      retentée
- [ ] Une nouvelle tentative laisse dans le journal du pipeline une ligne qui
      contient « nouvelle tentative »

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- La seconde tentative compte dans `timeout_phase2_s` : elle ne doit pas
  prolonger la surveillance au-delà du délai.