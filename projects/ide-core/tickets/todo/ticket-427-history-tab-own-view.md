---
id: ticket-427
title: "The History tab shows the selected run in the centre, or a filterable table of all runs, instead of the tickets list"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: ["ticket-425"]
estimated_days: 1
created: 2026-10-14
---

# ticket-427 — Onglet Historique : sa propre vue

## Objectif

Que l'onglet Historique montre l'historique des runs au centre — le détail
d'un run, ou le tableau de tous — au lieu de la liste des tickets.

## Contexte

Retour de Benjamin le 2026-10-14 : Fichiers et Historique affichent au
centre la même liste de tickets que l'onglet Tickets. Cause :
`components/CenterView.tsx` traite `projects`, `running`, `agents`, `usage`
et `chat`, puis retombe pour tout autre panneau sur `vueDuCentre`, qui
ignore l'onglet. Maquette validée :
`projects/ide-core/design/maquette/Historique.dc.html`.

Existant à réutiliser : `components/StatsView/RunHistorique.tsx` (rejoue un
run terminé en lecture seule à partir de ses événements, ticket-281) et
`GET /api/v1/projects/{id}/runs` (`PipelineRunSummary` : ticket, début, fin,
tours, approuvé, statut final, coût, arrêt). La colonne de gauche
(`components/Sidebar/RunHistory.tsx`) liste déjà les runs, mais un clic
sélectionne le **ticket**, pas le run.

## Solution proposée

- `CenterView` : `panel === "history"` rend `HistoriqueView`
  (`components/HistoriqueView/`).
- Un clic sur un run de la colonne sélectionne **ce run** (état du cockpit,
  à côté du ticket sélectionné).
- En-tête de la vue : titre « Historique » et un sélecteur à deux vues,
  « Détail du run » (défaut) et « Tous les runs », au style du sélecteur de
  l'onglet Tickets.
- **Détail du run** (maquette) : identifiant du ticket et date, titre du
  ticket, verdict et nombre de tours, lien vers la PR si elle existe ; une
  rangée de chiffres (durée, coût, tours) ; puis le fil du run rendu par
  `RunHistorique`. Sans run sélectionné : le plus récent ; sans aucun run :
  « Aucun run sur ce projet ».
- **Tous les runs** : tableau (ticket, titre, verdict, tours, coût, date),
  avec des filtres « Tous », « Approuvés », « Refusés ou bloqués »,
  « Plusieurs tours » ; un clic sur une ligne ouvre son détail.
- Couleurs d'état selon ADR-026 (vert approuvé, ambre plusieurs tours, rouge
  refusé ou bloqué).

## Critères d'acceptation

- [ ] Un test de `CenterView` vérifie que l'onglet Historique rend
      `HistoriqueView` et non la liste des tickets
- [ ] Un test vérifie qu'un clic sur un run de la colonne affiche son détail
      au centre (son ticket et son verdict)
- [ ] Un test vérifie que, sans run sélectionné, le détail montre le run le
      plus récent, et l'état vide sans aucun run
- [ ] Un test vérifie que le sélecteur bascule vers « Tous les runs » et que
      le filtre « Plusieurs tours » ne garde que les runs à `rounds > 1`
- [ ] Un test vérifie qu'un clic sur une ligne du tableau ouvre le détail de
      ce run

## Dépendances

ticket-425 (changer de projet ne réinitialise plus la vue).
