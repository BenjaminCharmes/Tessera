---
id: ticket-788
title: "A PR lost in a timeout is looked for again before the delivery gives up"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-781"]
estimated_days: 1
created: 2026-11-04
---

# ticket-788 — Une PR perdue dans un délai dépassé est recherchée à nouveau avant d'abandonner

## Objectif

Une PR ouverte sur GitHub alors que la réponse s'est perdue est toujours retrouvée et confiée à
CIWatcher, au lieu de rester orpheline.

## Contexte

04/11 vers 11:05 UTC, pendant un incident GitHub, file portfolio 77903268, ticket-023 :
`livraison_done` porte `arret: "Livraison interrompue : ReadTimeout"` et `pr_number: None`. La
PR #24 avait pourtant été créée. CIWatcher ne la connaissait pas : CI verte, PR propre, personne
ne la mergeait ; elle a été mergée à la main.

`_ouvrir_la_pr` (`backend/src/tessera/services/livraison.py`) attrape `httpx.TransportError`
(dont `ReadTimeout`) et appelle `pr_ouverte_malgre` (`backend/src/tessera/services/livraison_apres.py`,
ticket-455) : **une seule** recherche, immédiate. Quand GitHub est lent, la PR n'est pas encore
listée à cet instant ; la recherche rend `None` et l'arrêt part sans numéro. Le ticket-781
ajoute le même recours sur une erreur 5xx : il hérite de la même faiblesse.

## Solution proposée

- `pr_ouverte_malgre` recherche jusqu'à trois fois, avec un court délai croissant entre deux
  essais (délai injectable pour les tests), et s'arrête dès qu'une PR est trouvée.
- Elle ne lève toujours jamais ; une recherche qui échoue compte comme un essai.
- Jamais de second `POST /pulls` tant qu'une recherche n'a pas conclu qu'aucune PR n'existe.

## Critères d'acceptation

- [x] Un test vérifie, avec un double, qu'une PR absente à la première recherche puis présente
      à la deuxième est rendue par `pr_ouverte_malgre`
- [x] Un test vérifie qu'après trois recherches vides `pr_ouverte_malgre` rend `None`, en trois
      appels exactement
- [x] Un test vérifie qu'une recherche qui lève puis une recherche qui trouve rendent la PR
- [x] Un test de `_ouvrir_la_pr` vérifie qu'un `httpx.ReadTimeout` suivi d'une PR trouvée à la
      deuxième recherche lève `LivraisonInterrompue` portant ce numéro de PR, sans second appel
      à `open_pull_request`
