---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 1
id: ticket-513
pr_number: null
priority: medium
status: done
title: A ticket not yet started can be removed from a running queue
type: feat
---

# ticket-513 — Retirer d'une file en cours un ticket pas encore commencé

## Objectif
Pouvoir retirer d'une file vivante un ticket devenu inutile, sans arrêter la
file ni couper le ticket en cours.

## Contexte
Une file vivante accepte des ajouts (`POST /orchestrator/runs/{run_id}/append`,
tickets 478 et 504), mais rien ne permet d'en retirer un ticket. Le seul
levier est l'arrêt (`{"type": "stop"}` sur `WS /orchestrator/observe`), qui
coupe aussi le ticket en cours.

Le 19/10, Kadoomi (file 6cb72880 : 024, 025, 027 absorbés par un kit d'interface
commun) et Devinoo (file 70e47338 : 035 mis en attente de ce kit) ont eu
besoin de retirer des tickets de files déjà lancées.

Passer le ticket en `cancelled` sur la base ne suffit pas de façon sûre :
`Orchestrator._est_termine` (`backend/src/tessera/services/orchestrator.py`)
lit la fiche dans l'arbre de travail local, qui n'a pas forcément récupéré le
merge quand la file atteint le ticket. Le statut `blocked` n'est pas sauté
du tout.

## Solution proposée
- `FileVivante` (`backend/src/tessera/services/file_vivante.py`) gagne
  `retirer(ticket_ids)`, qui enlève les tickets qui ne sont ni en cours ni
  déjà passés, et refuse les autres avec une raison.
- `POST /orchestrator/runs/{run_id}/remove` avec `{"ticket_ids": [...]}`
  renvoie `{retires, ignores, refuses}`, sur le modèle d'`append` : 409 si le
  run n'est pas une file ouverte, `refuses` pour le ticket en cours
  (« en cours : utiliser stop ») ou déjà traité, `ignores` pour un ticket
  absent de la file.
- Chaque retrait écrit une ligne `[<projet>] ticket-XXX retiré de la file`
  dans `memory/pipeline-log.md`.
- La fiche du ticket n'est pas modifiée : retirer n'est pas annuler.

## Critères d'acceptation
- [ ] Dans `file_vivante.py`, `FileVivante.retirer` enlève un ticket pas encore commencé, et un test le vérifie
- [ ] Un test vérifie que le ticket en cours ne peut pas être retiré (refusé, avec sa raison)
- [ ] Un test vérifie qu'un ticket déjà traité par la file ne peut pas être retiré
- [ ] Un test d'API vérifie que `POST /orchestrator/runs/{run_id}/remove` renvoie 409 pour un run inconnu ou terminé
- [ ] Un test vérifie qu'après un retrait, la file enchaîne sur le ticket suivant sans exécuter le ticket retiré
- [ ] `docs/api.md` décrit la route

## Dépendances
Aucune.

## Estimation
Un jour.

## Risques
Concurrence avec la boucle de la file : comme pour `ajouter`, aucun `await`
entre le contrôle et la modification.