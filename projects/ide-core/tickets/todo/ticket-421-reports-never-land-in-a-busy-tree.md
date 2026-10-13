---
id: ticket-421
title: "A report sent while an ide-core run is active waits outside the tree, and is written once the project is free"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-13
---

# ticket-421 — Un signalement n'atterrit jamais dans un arbre occupé par un run

## Objectif

Qu'un signalement (`POST /api/v1/signalements`, ticket-407) ne puisse pas
être emporté dans le commit d'un run ide-core en cours.

## Contexte

Le 2026-10-13, la session affut a déposé le ticket-420 par l'endpoint
pendant qu'une file ide-core tournait (tickets 416-417). Le fichier est
arrivé, non suivi, dans `projects/ide-core/tickets/todo/` de l'arbre dont le
run se sert. `commit_bookkeeping` (`git_workspace.py`) n'exclut que les
fichiers non suivis **au démarrage** du run : un fichier apparu pendant le
run part dans son commit de suivi, puis dans sa PR (déjà vu le 2026-10-05
sur carriere, tickets 062-063). Le ticket-420 a été sorti de l'arbre à la
main.

## Solution proposée

- `routers/signalements.py` : si `RUN_REGISTRY.projet_occupe("ide-core")`,
  le ticket n'est pas écrit dans l'arbre : il est mis en attente dans un
  fichier JSON hors du dépôt (à côté de la base, `settings.ide_db_path`
  parent, `signalements_en_attente.json`), et la réponse est **202** avec
  `{ "en_attente": true, "position": n }`.
- À la fermeture d'un run ide-core (`RUN_REGISTRY.fermer` ou l'évènement de
  fin de run), les signalements en attente sont écrits comme aujourd'hui,
  dans l'ordre d'arrivée, puis retirés de l'attente.
- Projet libre : comportement actuel (201 avec le ticket).

## Critères d'acceptation

- [ ] Un test vérifie qu'un signalement reçu pendant un run ide-core renvoie
      202 avec `en_attente: true` et n'écrit aucun fichier sous
      `tickets/todo/`
- [ ] Un test vérifie qu'à la fin du run, le signalement en attente devient un
      ticket `todo` et quitte l'attente
- [ ] Un test vérifie que deux signalements en attente sont écrits dans
      l'ordre d'arrivée, avec des numéros distincts
- [ ] Un test vérifie qu'un signalement reçu sans run en cours renvoie 201
      comme avant

## Dépendances

Aucune.
