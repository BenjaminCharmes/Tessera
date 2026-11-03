---
agent: codeur
created: 2026-10-26
depends_on:
- ticket-567
estimated_days: 0.25
id: ticket-580
pr_number: 654
priority: high
status: done
title: The side column is hidden where it has nothing to show, and the bell count
  sits on its icon
type: fix
---

# ticket-580 — Colonne latérale vide masquée, pastille de la cloche sur l'icône

## Objectif
Deux retouches du cadre, relevées par Benjamin le 26/10 sur le Bureau.

## Contexte
- La colonne 2 (`<aside aria-label="Panneau latéral">` de `frontend/src/App.tsx`)
  s'affiche dans tous les onglets. `components/Sidebar/index.tsx` n'a aucun
  contenu pour `supervision` ni pour `running` (« En cours ») : la colonne y
  reste vide et prend de la place au Bureau.
- Le nombre de notifications non lues de la cloche
  (`components/Sidebar/Cloche.tsx`) s'affiche en haut à droite du bouton, loin
  de l'icône : il doit être posé en haut à droite de l'icône.

## Critères d'acceptation
- [ ] Pour les panneaux `supervision` et `running`, la colonne 2 n'est pas rendue et la vue principale prend sa largeur ; un test de `App` le vérifie pour `supervision`
- [ ] Pour le panneau `tickets`, la colonne 2 est toujours rendue, et un test le vérifie
- [ ] Dans `Cloche.tsx`, la pastille du nombre de non-lus est positionnée par rapport à l'icône (même conteneur que le `svg`), et un test vérifie qu'elle est dans ce conteneur
- [ ] Le diff ne modifie aucun fichier de `backend/`