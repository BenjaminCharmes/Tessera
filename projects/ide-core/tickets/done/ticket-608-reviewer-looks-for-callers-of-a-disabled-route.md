---
agent: codeur
created: 2026-10-27
depends_on: []
estimated_days: 0.25
id: ticket-608
pr_number: 689
priority: medium
status: done
title: The reviewer looks for the callers of any route, export or path the diff disables
  or removes
type: chore
---

# ticket-608 — Le reviewer cherche les appelants de ce que le diff retire

## Objectif

Qu'un diff qui désactive ou supprime une route, un export ou un chemin ne
soit pas approuvé tant qu'un appelant s'en sert encore.

## Contexte

Signalé par la session Kadoomi le 27/10. Le ticket-087 de Kadoomi a mis
`/update-user` dans les `disabledPaths` de l'authentification, alors que
l'écran `/bienvenue` appelait encore `authClient.updateUser` côté client. Le
reviewer et le validateur ont approuvé, et le bug est arrivé en production :
tout premier login par lien magique restait bloqué sur « Ton prénom n'a pas
pu être enregistré ». La faille a été vue par un utilisateur réel, et le
hotfix est parti en urgence (Kadoomi, ticket-114).

`agents/prompts/reviewer.md` dit déjà d'ouvrir un fichier quand « un
appelant modifié » l'exige. Il ne dit pas de **chercher** les appelants de ce
que le diff retire, alors que ceux-là n'apparaissent pas dans le diff.

## Solution proposée

Dans `agents/prompts/reviewer.md`, liste « Bloquant (CHANGES_REQUESTED) » :
ajouter une ligne du type « Le diff désactive, renomme ou supprime une route,
un export ou un chemin, et un appelant hors du diff s'en sert encore — le
chercher avec `Grep` (nom de la route, de la fonction, du chemin) avant de
conclure ».

Rester court : ce prompt part dans chaque revue.

## Critères d'acceptation

- [ ] `agents/prompts/reviewer.md` contient, dans la liste « Bloquant », une ligne qui demande de chercher avec `Grep` les appelants d'une route, d'un export ou d'un chemin que le diff désactive, renomme ou supprime.
- [ ] Un test de `backend/tests/` lit `agents/prompts/reviewer.md` et vérifie que cette consigne y figure (présence de « appelant » et de `Grep` dans la section « Bloquant »).
- [ ] Le diff n'ajoute pas plus de 4 lignes à `agents/prompts/reviewer.md`.

## Dépendances

Aucune.

## Estimation

Un quart de journée.

## Risques

Dix tours d'outils au reviewer : la consigne doit viser une recherche ciblée,
pas une relecture du projet.