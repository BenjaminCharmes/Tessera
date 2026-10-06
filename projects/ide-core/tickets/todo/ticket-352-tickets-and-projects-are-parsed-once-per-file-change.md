---
id: ticket-352
title: "Tickets and projects are parsed once per file change, off the event loop"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-05
---

# ticket-352 — Tickets et projets ne se relisent qu'à leur changement, hors de la boucle

## Objectif

Que lister les tickets ou les projets ne relise plus chaque fichier à chaque
requête, et ne bloque plus le serveur pendant qu'il le fait : l'interface
reste réactive quand plusieurs files tournent.

## Contexte

`TicketService.list_tickets_with_unreadable`
(`backend/src/tessera/services/ticket_service.py`) relit et parse le
frontmatter YAML de **chaque** ticket actif à chaque appel — environ 340
fichiers pour ide-core. Il est appelé par `GET /tickets` (toutes les 30 s
depuis l'interface pendant une file), par le contexte projet, le chat, les
agents, et deux fois par étape de file (`Orchestrator.pick_next_ticket`).
`get_ticket` parcourt aussi tous les dossiers par `_find_file`, à chaque
statut de PR demandé par une carte.

`ProjectLoader.list_projects`
(`backend/src/tessera/services/project_loader.py`) relit `CLAUDE.md` et
parse `agents.json` de chaque projet à chaque requête.

Tout cela tourne en synchrone dans des `async def` : pendant le parsing, la
boucle ne sert ni les autres requêtes ni la WebSocket d'observation.

## Solution proposée

1. **Cache de parsing par fichier**, de niveau module, clé
   `(chemin résolu, st_mtime_ns, st_size)` → `Ticket` ou erreur. Un `stat`
   par fichier reste fait à chaque appel (peu coûteux) ; seul un fichier
   modifié, ajouté ou déplacé est re-parsé. Les entrées des fichiers disparus
   sont purgées au listage suivant.
2. Même principe pour `load_project` : `CLAUDE.md` et `agents.json` d'un
   projet ne sont relus que si l'un des deux a changé (mtime ou taille).
3. Le travail sur disque de `list_tickets_with_unreadable`, `get_ticket` et
   `ProjectLoader.list_projects` passe par `asyncio.to_thread`, pour ne plus
   bloquer la boucle.
4. Aucune écriture ne passe par le cache : `update_status`, `create_ticket`,
   `set_pr_number` écrivent sur disque comme avant, et le changement de mtime
   suffit à invalider.

## Critères d'acceptation

- [ ] Un test de `test_ticket_service.py` montre que deux listages successifs
      sans changement ne parsent chaque fichier qu'une fois (parseur espionné)
- [ ] Un test de `test_ticket_service.py` montre qu'un ticket modifié sur
      disque entre deux listages est rendu avec son nouveau contenu
- [ ] Un test de `test_ticket_service.py` montre qu'un ticket déplacé de
      `todo/` à `done/` est rendu avec son nouveau statut, une seule fois
- [ ] Un test de `test_ticket_service.py` montre qu'un fichier supprimé
      disparaît du listage suivant
- [ ] Un test de `test_project_loader.py` montre qu'un `agents.json` modifié
      est relu au chargement suivant, et qu'il ne l'est pas sans modification
- [ ] `ticket_service.py` et `project_loader.py` appellent
      `asyncio.to_thread` pour leur travail sur disque

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

- Deux écritures dans la même milliseconde avec la même taille donneraient une
  clé identique : `st_mtime_ns` plus la taille rend le cas négligeable pour
  des fichiers écrits à la main ou par un agent.
- Les tests qui réécrivent un fichier dans la même fraction de seconde doivent
  forcer le mtime (`os.utime`) plutôt que d'attendre.
