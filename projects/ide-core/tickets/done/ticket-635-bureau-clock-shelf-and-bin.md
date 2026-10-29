---
agent: codeur
created: 2026-10-28
depends_on:
- ticket-631
estimated_days: 1
id: ticket-635
pr_number: null
priority: low
status: done
title: The Bureau rooms gain a wall clock, a wall shelf, a framed picture, and a bin
  that fills with refused rounds
type: feat
---

# ticket-635 — Une horloge, une étagère et une corbeille

## Objectif
Varier le mobilier des pièces, et que deux des trois objets disent un fait.

## Contexte
Idée de Benjamin du 28/10. ADR-058 : un objet se dessine toujours s'il est du
mobilier sans voyant ; tout ce qui bouge ou change dit un fait que le store ou
l'API fournit. Le ticket-631 donne un composant de mur partagé aux salles du haut
et aux pièces.

Les refus du reviewer se lisent déjà : `verdictDuReviewer` (`components/FilDuRun/verdict`)
sur l'`agent_done` du reviewer, comme dans `lib/bureau/copie.ts`.

## Solution proposée
- **Horloge murale** (pièces et salles du haut) : ses aiguilles donnent l'heure de
  l'horloge unique de la vue (`maintenant`), comme le ciel des fenêtres.
- **Étagère murale** (pièces) : une petite plante et deux livres. Mobilier fixe,
  sans état.
- **Cadre** (pièces et salles du haut) : un tableau accroché au mur, dont l'image
  varie d'une pièce à l'autre, tirée du nom du projet comme sa tenue. Mobilier
  fixe, sans état.
- **Corbeille** (pièces), au sol près d'un poste : une boule de papier froissé par
  `agent_done` du reviewer rendant `CHANGES_REQUESTED` sur le ticket en cours
  (`etat.ticketEvents`), trois au plus dessinées. Vide au ticket suivant.
- Les nouveaux sprites vivent sous `design/bureau/`, leurs tons sont des jetons
  `--sprite-*` du `@theme`.

## Critères d'acceptation
- [ ] Un test vérifie que l'horloge place ses aiguilles selon `maintenant` : 3 h et 9 h donnent des aiguilles différentes
- [ ] Un test vérifie que la corbeille dessine une boule par refus du reviewer sur le ticket en cours, trois au plus, et aucune sans refus
- [ ] Un test vérifie que la corbeille se vide quand `ticketEvents` change de ticket
- [ ] Un test vérifie que deux projets différents ont des cadres différents, et qu'un projet garde le même d'un rendu à l'autre
- [ ] Les nouveaux sprites n'utilisent que des jetons `--sprite-*` (ADR-058)

## Ce que ça ne fait pas
- Ne compte pas les refus du validateur : la copie rendue (ticket-599) les montre déjà.