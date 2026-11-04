---
agent: codeur
created: 2026-11-03
depends_on: []
estimated_days: 1
id: ticket-764
pr_number: null
priority: medium
status: done
title: The shared modal traps focus and gives it back when it closes
type: fix
---

# ticket-764 — La modale partagée retient le focus et le rend à la fermeture

## Objectif

Une modale ouverte garde le clavier, se ferme à Échap où que soit le focus, et rend le focus
à ce qui l'a ouverte.

## Contexte

Audit du 30/10 (relecture du 03/11), ticket-682. `frontend/src/design/ui/Modale.tsx` pose
`aria-modal="true"`, mais Tab sort vers la page derrière ; Échap n'est écouté que sur le
fond, donc plus rien ne ferme une fois le focus sorti ; le focus n'est pas rendu au bouton
d'ouverture. Les exemptions existantes (`RemoveProjectModal`, `Fenetre`) restent valables.

## Critères d'acceptation

- [ ] Un test vérifie que Tab depuis le dernier élément focalisable revient au premier, et
      Maj+Tab depuis le premier va au dernier
- [ ] Un test vérifie qu'après la fermeture le focus est sur le bouton qui a ouvert la modale
- [ ] Un test vérifie qu'Échap ferme la modale quand le focus est sur un champ de la modale
- [ ] Les tests existants des modales exemptées passent sans changement