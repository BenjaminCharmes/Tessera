---
agent: codeur
created: 2026-10-15
depends_on: []
estimated_days: 1
id: ticket-460
plan: true
pr_number: null
priority: medium
status: done
title: Every ticket id shown in the app opens that ticket's detail in the Tickets
  tab
type: feat
---

# ticket-460 — Un numéro de ticket ouvre le ticket, partout

## Objectif

Où qu'un ticket apparaisse dans Tessera, un clic sur lui ouvre son détail
dans l'onglet Tickets de son projet.

## Contexte

Demandé par Benjamin le 15/10. Seules la vue Liste (`TicketList`) et le
Kanban ouvrent le détail d'un ticket (`onSelectTicket` dans
`frontend/src/components/CenterView.tsx`). Ailleurs, l'identifiant est un
simple texte :

- les tickets d'une file lancée et ses runs dans Supervision
  (`frontend/src/components/SupervisionView/RunCard.tsx`) ;
- l'en-tête de la vue d'un run (`frontend/src/components/RunView/index.tsx`) ;
- l'Historique (`frontend/src/components/HistoriqueView/TousLesRuns.tsx`,
  `frontend/src/components/HistoriqueView/DetailDuRun.tsx`).

Pour voir le détail, il faut changer d'onglet et chercher le ticket à la
main.

## Solution proposée

- Une action partagée « ouvrir le ticket » (projet + identifiant) : active
  le projet s'il ne l'est pas, passe sur l'onglet Tickets, ouvre le détail
  du ticket (relu par l'API si besoin).
- Un petit composant de lien de ticket (identifiant, et titre quand il est
  connu) qui appelle cette action ; rendu comme un lien (soulignement au
  survol, focus visible, Entrée), selon la charte
  (`projects/ide-core/memory/design.md`).
- Ce composant remplace le texte brut dans les vues ci-dessus.
- Un ticket introuvable (supprimé, renommé) affiche un message, sans
  planter la vue.

## Critères d'acceptation

- [ ] Un test vérifie qu'un clic sur un ticket d'une file dans
      `RunCard.tsx` ouvre le détail de ce ticket dans l'onglet Tickets
- [ ] Un test vérifie la même chose depuis `TousLesRuns.tsx`
- [ ] Un test vérifie la même chose depuis l'en-tête de
      `RunView/index.tsx`
- [ ] Un test vérifie qu'un ticket d'un autre projet active ce projet avant
      d'ouvrir le détail
- [ ] Un test vérifie qu'un ticket introuvable affiche un message, sans
      erreur
- [ ] Le lien est atteignable au clavier (rôle `link` ou `button`, Entrée
      l'active)

## Ce que ça ne fait pas

- Ne change pas l'écran de détail d'un ticket lui-même.