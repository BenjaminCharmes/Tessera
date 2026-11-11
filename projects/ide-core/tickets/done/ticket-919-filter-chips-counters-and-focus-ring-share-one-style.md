---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-919
pr_number: null
priority: low
status: done
title: Filter chips, counter badges and the focus ring each share one style
type: refactor
---

# ticket-919 — Puces de filtre, pastilles de compteur et anneau de focus : un style chacun

## Objectif

Que trois petits éléments répétés partout aient chacun un seul gabarit.

## Contexte

Relevé à l'audit du 11/11 :

- puces de filtre : `components/HistoriqueView/TousLesRuns.tsx`
  (`py-1 text-xs`) et `components/ProjetsView/BarreProjets.tsx`
  (`py-0.5 text-micro`), même rôle, deux gabarits ;
- pastilles de compteur recopiées : `components/Sidebar/Cloche.tsx`,
  `components/Sidebar/Pastille.tsx`, `components/BureauView/Dossiers.tsx` ;
- anneau de focus `focus-visible:outline-2 … outline-violet-500` recopié à la
  main dans huit fichiers, avec ou sans `outline-offset-2`.

## Solution proposée

- Un composant `design/ui/PuceFiltre.tsx` (bouton à bascule, `aria-pressed`)
  pour les deux barres de filtre.
- Un composant `design/ui/Compteur.tsx` pour les trois pastilles.
- Une utilité `focus-violet` déclarée par `@utility` dans `index.css`, que les
  fichiers concernés emploient.

## Critères d'acceptation

- [ ] `TousLesRuns.tsx` et `BarreProjets.tsx` importent `PuceFiltre`, et un
      test de `PuceFiltre` vérifie `aria-pressed`.
- [ ] `Cloche.tsx`, `Pastille.tsx` et `Dossiers.tsx` importent `Compteur`.
- [ ] `index.css` déclare `@utility focus-violet`, et le diff retire
      `outline-violet-500` des fichiers qui l'emploient désormais.
- [ ] Les tests des composants touchés passent.

## Ce que ça ne fait pas

Ne change pas la section `@theme` d'`index.css`.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Une utilité Tailwind v4 mal déclarée ne casse pas le build mais n'applique
rien : le test de `PuceFiltre` vérifie la classe, la capture vérifie le rendu.