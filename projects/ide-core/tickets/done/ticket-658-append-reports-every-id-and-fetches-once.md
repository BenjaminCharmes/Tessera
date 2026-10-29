---
agent: codeur
created: 2026-10-28
depends_on: []
estimated_days: 1
id: ticket-658
pr_number: 745
priority: medium
status: done
title: Appending to a queue reports every requested id and fetches the base once per
  request
type: fix
---

# ticket-658 — L'ajout à une file rend compte de chaque id, et ne relit la base qu'une fois

## Objectif
Qu'un `POST /orchestrator/runs/{run_id}/append` réponde vite, et classe chaque id
demandé dans `ajoutes`, `ignores` ou `refuses`.

## Contexte
Signalé le 28/10 par la session Curio (run 3b23c657) :
- un ajout de 15 tickets a dépassé 30 s, mais il a bien été appliqué côté serveur ;
- un second appel, lancé pendant que le premier tournait encore, a renvoyé
  `ajoutes=[]` et `ignores` pour 028 à 038 seulement : 024 à 027 n'étaient dans
  aucune des trois listes.

Deux causes, lues dans le code :
- **lenteur** : `trier_ajouts` (`services/file_vivante.py`) lit chaque ticket absent
  de l'arbre du run par `lecteur_sur_la_base`, et `lire_ticket_sur_la_base`
  (`services/git_workspace/ticket_sur_base.py`) fait un `git fetch` à chaque
  lecture, y compris pour chaque dépendance consultée ;
- **ids perdus** : `trier_ajouts` accepte un id qui n'est pas encore dans la file,
  puis attend des lectures ; pendant ce temps, un appel concurrent l'y ajoute.
  `FileVivante.ajouter` l'écarte alors en silence, et la route ne le rapporte nulle part.

## Solution proposée
- La route range dans `ignores`, avec « déjà dans la file », tout id accepté que
  `ajouter` n'a pas ajouté.
- Le lecteur de repli ne fait qu'un `fetch` par requête d'ajout : la base est lue
  une fois, puis chaque ticket y est cherché sans nouveau `fetch`.

## Critères d'acceptation
- [ ] Un test de la route `append` vérifie que chaque id envoyé figure dans exactement une des listes `ajoutes`, `ignores` ou `refuses`, y compris un id ajouté à la file entre le tri et l'ajout
- [ ] Un test vérifie, avec un double de l'espace git, qu'un ajout de plusieurs tickets absents de l'arbre ne déclenche qu'un seul `fetch`

## Ce que ça ne fait pas
- Ne change pas les règles de tri (déjà dans la file, terminé, introuvable, dépendance manquante).