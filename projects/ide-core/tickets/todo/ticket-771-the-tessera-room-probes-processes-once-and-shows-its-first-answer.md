---
id: ticket-771
title: "The Tessera room probes processes once per request and shows its first answer"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-767"]
estimated_days: 1
created: 2026-11-03
---

# ticket-771 — La salle Tessera ne sonde les processus qu'une fois par requête, et montre sa première réponse

## Objectif

La salle serveur Tessera, « toujours allumée » (ticket-726), apparaît dès l'ouverture de
« En cours », même sous la charge d'une file.

## Contexte

03/11, captures pour le portfolio : dans un navigateur neuf, la salle Tessera reste absente
d'« En cours » pendant près de 30 s. Mesuré dans la page : `GET /tessera/salle` prend 4 à
11 s sous la charge d'une file, et la vue en relance une à chaque relecture de l'inventaire
(`lueA`, toutes les 5 à 10 s), ce qui annule la précédente.

- Backend : `salle_tessera` (`backend/src/tessera/services/salle_tessera.py`) appelle
  `sonde.processus()` puis `processus_de_tessera`, qui rappelle `sonde.processus()` et
  `sonde.ecouteurs()` : deux sondes complètes des processus du système par requête.
- Frontend : dans `useResource` (`frontend/src/hooks/useResource.ts`), une réponse dont
  l'effet a été annulé est jetée avant `setCached` : elle ne remplit même pas le cache de sa
  clé, si bien que la salle reste à `null` tant qu'aucune réponse n'arrive avant la relance
  suivante.

## Solution proposée

- `salle_tessera` lit `sonde.processus()` et `sonde.ecouteurs()` une seule fois et passe
  ces données à `processus_de_tessera` et `agents_en_cours`.
- `useResource` : une réponse réussie remplit le cache de sa clé même quand son effet a été
  annulé par une relance ; seul l'état de la requête courante l'ignore.

## Critères d'acceptation

- [ ] Un test vérifie, avec une sonde double qui compte ses appels, que `salle_tessera`
      appelle `processus()` une fois et `ecouteurs()` une fois
- [ ] Un test vérifie qu'une réponse arrivée après un changement de `fetcher` (avec clé)
      remplit le cache, et que le hook rend cette donnée tant que la nouvelle requête n'a pas
      répondu
- [ ] Un test vérifie que `SalleTessera` est rendue quand la première réponse arrive après une
      relance de `lueA`

## Dépendances

ticket-767 (même hook).
