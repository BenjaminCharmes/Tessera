---
id: ticket-423
title: "Stopping Tessera only stops Tessera's own server processes, never other projects' apps"
type: fix
status: todo
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-13
---

# ticket-423 — `tessera.ps1 stop` n'arrête que Tessera

## Objectif

Qu'arrêter ou redémarrer Tessera ne tue jamais une autre application de la
machine.

## Contexte

`Stop-Tessera` (`scripts/tessera.ps1`) tue **tout** `python.exe` dont la
ligne de commande contient `uvicorn` et **tout** `node.exe` qui contient
`vite`. Le 2026-10-13, les deux redémarrages du backend (vers 07:45 et
13:55 UTC) ont ainsi tué l'API et le front de vigie, lancés à la main hors
Tessera, et les services des autres projets ; une autre application locale
servie par uvicorn (port 8000) l'aurait été aussi. Le filtre vise le worker
`--reload` orphelin (ticket-056), mais il est bien trop large.

## Solution proposée

- Ne cibler que :
  - un `python.exe` dont la ligne de commande contient `tessera.main:app`
    (le backend, parent ou worker `spawn_main` qui en descend) ;
  - un `node.exe` dont la ligne de commande contient `vite` **et** dont le
    répertoire de travail ou la ligne de commande désigne le dossier
    `frontend` de ce dépôt (chemin absolu de `$Root\frontend`), ou à défaut
    le processus qui écoute le port 5173.
- Pour le worker orphelin (`spawn_main(parent_pid=…)` sans `tessera.main`) :
  le processus qui écoute le port 8100, quel que soit son nom.
- Afficher ce qui est arrêté (PID et début de la ligne de commande) au lieu
  d'un simple compteur.
- La logique de sélection vit dans une fonction pure PowerShell
  (`Select-ProcessusTessera`) testée par un script Pester, **ou** est portée
  en Python (`scripts/arreter_tessera.py`, testé par pytest) et appelée par
  le `.ps1` : au choix du codeur, l'important est d'avoir un test.

## Critères d'acceptation

- [ ] Un test vérifie qu'un `python.exe` lancé par
      `uvicorn app.main:app --port 8025` n'est **pas** sélectionné
- [ ] Un test vérifie qu'un `python.exe` lancé par
      `uvicorn tessera.main:app --port 8100` est sélectionné
- [ ] Un test vérifie qu'un `node.exe … vite` d'un autre dossier n'est pas
      sélectionné, et que celui du `frontend/` de Tessera l'est
- [ ] Un test vérifie que le processus qui écoute 8100 est sélectionné même si
      sa ligne de commande ne cite pas `tessera.main`
- [ ] `Stop-Tessera` affiche le PID de chaque processus arrêté

## Dépendances

Aucune.

## Ce que ça ne fait pas

- Ne touche pas aux services de projet lancés par Tessera : ce sont des
  enfants du backend, qui meurent avec lui (ADR-042) et que la vue « En
  cours » permet d'arrêter.
