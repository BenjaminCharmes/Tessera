---
id: ticket-336
title: "A ticket added on the base is found even when the repo still sits on the last delivered branch"
type: fix
status: done
pr_number: 254
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-05
---

# ticket-336 — Un ticket ajouté sur la base se retrouve après une file

## Objectif

Qu'un ticket ajouté sur la base pendant ou après une file se lance, même si
le dépôt est resté sur la branche du dernier ticket livré.

## Contexte

Constaté sur démineur le 2026-10-05 : après une file, le dépôt reste sur
`ticket-XXX-…` (la PR est mergée en fond par le CIWatcher). Un ticket ajouté
sur la base entre-temps n'existe pas dans l'arbre, et `POST /orchestrator/run`
échoue avec `run_interrompu: Ticket introuvable : ticket-040`.

Le ticket-329 sait restaurer un ticket absent depuis la base
(`restaurer_ticket_depuis_base`), mais seulement si `_base_ref` est connu.
L'orchestrateur est instancié à chaque requête (ADR-008) : au moment où le
ticket est lu, rien n'a encore initialisé `_base_ref`, et la restauration
rendait `False` sans rien chercher.

Ramener le checkout sur la base à la main produisait en plus un conflit de
`stash pop` sur `pipeline-log.md` ; ce geste n'est plus nécessaire, et les
lignes écrites après la livraison suivent le run suivant (ticket-331).

## Solution proposée

`restaurer_ticket_depuis_base`, sans `_base_ref`, l'aligne d'abord sur la base
distante (`initialiser_base_ref`, ticket-285) avant de chercher. Revenir sur la
base après la livraison est écarté : le merge se fait en fond, pendant que le
ticket suivant de la file peut déjà tourner.

## Critères d'acceptation

- [x] Un test sur un dépôt relié à un distant vérifie qu'un workspace neuf,
      resté sur la branche d'un ticket livré, restaure un ticket ajouté sur la
      base distante
- [x] Un test vérifie que, sans base déclarée, rien n'est restauré

## Dépendances

Aucune.

## Estimation

0,5 jour.
