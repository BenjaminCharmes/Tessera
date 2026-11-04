---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-767
pr_number: 893
priority: medium
status: done
title: A shared resource sends one request at a time and keeps its last data on error
type: fix
---

# ticket-767 — Une ressource partagée n'envoie qu'une requête à la fois et garde sa dernière donnée en erreur

## Objectif

Plusieurs salles qui lisent la même ressource ne multiplient pas les requêtes, et une
lecture en échec ne fait plus disparaître une salle.

## Contexte

Audit du 30/10 (relecture du 03/11), tickets 683 et 726.
- `useApercuDesProjets` promet « sans relancer la requête », mais `useResource` relance
  l'effet à chaque instance : 3 projets lancés → 5 appels à `api.projects.overview` au
  montage (vérifié). La clé de cache ne regroupe pas les requêtes en vol.
- En erreur, `useResource` rend `initial` (`null`) : la salle Tessera « toujours allumée »
  disparaît jusqu'au tick suivant, et `SalleDeProjet` referme puis rouvre son journal déplié.

## Critères d'acceptation

- [ ] Un test vérifie que trois instances montées ensemble avec la même clé ne font qu'un
      appel
- [ ] Un test vérifie qu'une lecture en échec après une lecture réussie rend la dernière
      donnée, et expose l'erreur à part
- [ ] Un test vérifie que la salle Tessera reste rendue après une lecture en échec