---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 1
id: ticket-439
pr_number: null
priority: high
status: done
title: 'Shared UI components from the charter: status pill, button variants, view
  switcher, empty/loading/error states'
type: feat
---

# ticket-439 — Les composants communs de la charte

## Objectif

Que chaque écran de Tessera tire ses pastilles, boutons, sélecteurs de vue
et états d'un seul endroit, comme le fixe la charte.

## Contexte

Charte validée le 2026-10-14 : `projects/ide-core/memory/design.md` et
`projects/ide-core/design/maquette/Charte.dc.html`. L'audit des neuf
onglets a relevé des pastilles d'état de formes différentes selon l'écran,
plusieurs styles de boutons, et trois copies du sélecteur de vue (onglets
Historique, Fichiers, Agents — tickets 427 à 429).

## Solution proposée

Dans `frontend/src/design/ui/` :
- `StatusPill.tsx` : `etat` parmi `en-cours | reussi | attention | echec |
  neutre`, et un libellé obligatoire ; couleurs d'ADR-026, fond à 12 %,
  rayon 4 px.
- `Button.tsx` : `variante` parmi `plein | borde | discret | arret`, taille
  `normal` (30 px) ou `compact` (26 px) ; `plein` en violet.
- `ViewSwitcher.tsx` : options `{ valeur, libelle }[]`, valeur courante,
  `onChange` ; `aria-pressed` sur chaque option.
- `ViewState.tsx` : `Vide` (titre, phrase, action facultative),
  `Chargement` (lignes squelettes), `Erreur` (message, bouton
  « Réessayer »).
- Les trois sélecteurs de vue existants (Historique, Fichiers, Agents)
  utilisent `ViewSwitcher`.

## Critères d'acceptation

- [ ] Un test vérifie que `StatusPill` rend son libellé et une classe de la
      famille de couleur de chaque état (blue, green, amber, red, zinc)
- [ ] Un test vérifie que `Button` en variante `plein` porte une classe violet
      et que `arret` ne porte pas de fond rouge plein
- [ ] Un test vérifie que `ViewSwitcher` marque l'option courante
      `aria-pressed="true"` et appelle `onChange` au clic
- [ ] Un test vérifie que `Erreur` affiche « Réessayer » et appelle son action
- [ ] `HistoriqueView`, `FichiersView` et `AgentDetail` importent
      `ViewSwitcher` (plus de copie locale du sélecteur)

## Dépendances

Aucune. Le ticket-442 en dépend.