---
agent: codeur
created: 2026-10-26
depends_on:
- ticket-580
estimated_days: 0.25
id: ticket-586
pr_number: 669
priority: high
status: done
title: The projects view drops its duplicate side list and takes its import and create
  buttons
type: fix
---

# ticket-586 — La vue Projets perd sa liste latérale en double

## Objectif
Même retouche que le ticket-580 pour Supervision, relevée par Benjamin le
26/10 : dans l'onglet Projets, la colonne 2 répète la grille du milieu.

## Contexte
- La colonne 2 rend `ProjectNav` (`components/Sidebar/ProjectNav.tsx`) pour le
  panneau `projects` : la liste des projets par catégorie, deux boutons
  « Importer un projet » et « Créer un projet » (modales `ImportProjectModal`
  et `CreateProjectModal`), et un point ambre « Un agent attend une réponse »
  (`LigneDeProjet.tsx`, ticket-186, calculé par `projetsEnAttente.ts`).
- Le milieu rend `ProjetsView` (`components/ProjetsView/`) : une carte par
  projet, avec recherche, catégories et tri (`BarreProjets.tsx`). Il n'a ni les
  deux boutons ni le point ambre.
- Le ticket-580 masque la colonne 2 pour `supervision` et `running` ; ce
  ticket ajoute `projects` à cette liste.

## Solution proposée
- La colonne 2 n'est plus rendue pour le panneau `projects`.
- `BarreProjets.tsx` porte « Importer un projet » et « Créer un projet », qui
  ouvrent les modales existantes ; un projet créé ou importé devient le
  projet actif, comme aujourd'hui (`onProjectCreated`).
- `ProjetCarte.tsx` porte le point ambre (même libellé, même calcul
  `projetsEnAttente`), ton `amber` (ADR-026).
- `ProjectNav.tsx` n'a plus d'appelant : il est supprimé avec son test, et
  `LigneDeProjet`, `EnTeteDeCategorie`, `grouperParCategorie` aussi s'ils n'en
  ont plus.

## Critères d'acceptation
- [ ] Pour le panneau `projects`, la colonne 2 n'est pas rendue ; un test de `App` le vérifie
- [ ] La vue Projets affiche les boutons « Importer un projet » et « Créer un projet », qui ouvrent leurs modales ; un test le vérifie pour chacun
- [ ] La carte d'un projet dont un run attend une réponse porte « Un agent attend une réponse », et pas les autres ; un test le vérifie
- [ ] Aucun fichier de `frontend/src` n'importe plus `ProjectNav`
- [ ] Le diff ne modifie aucun fichier de `backend/`