---
id: ticket-283
title: "The way back to the running run is always offered, and the pipeline log follows the selected run"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-01
---

# ticket-283 — On retrouve toujours le run, et le log suit celui qu'on regarde

## Objectif

Que « Revenir au run en cours » soit proposé dès que le run n'est pas au
centre, et que le Pipeline log montre le run sélectionné dans la Supervision.

## Contexte

Retour d'usage du 2026-10-01 :

- `runCache` vaut `runEnCours && !runAuPremierPlan` (`hooks/useCockpit.ts:270`).
  `onToggleKanban` remet `runAuPremierPlan` à faux ; `onOpen` (ouvrir un
  fichier, `:356-359`) et `onShowDiff` (`:290-295`) non. Depuis un fichier ou
  un diff, le centre n'affiche plus le run mais le bouton reste caché.
- Sélectionner un run dans la Supervision (`useSupervision.selectionner`) ne
  touche pas au projet actif ; `BottomPanel` reçoit `cockpit.events`, ceux du
  run du projet actif (`useRunActif.ts:36-43`). On lit les agents d'un run et
  le log d'un autre.
- Dans une file, `queue_progress` remet l'état à `INITIAL` sans garder
  `events` (`streamState.ts:416-427`) : chaque ticket efface le log du
  précédent.
- Sur la carte d'un ticket en cours, le rond bleu est le bouton « Lancer le
  pipeline » désactivé (`Sidebar/TicketCard.tsx:242-258`), avec son `title`
  et son effet au survol : il a l'air cliquable et ne fait rien.

## Solution proposée

- `runCache` se calcule depuis la vue du centre (`vueDuCentre`) : vrai dès que
  le run est en cours et que le centre affiche autre chose.
- Le Pipeline log affiche les événements du run sélectionné dans la
  Supervision quand il y en a un, ceux du projet actif sinon ; son en-tête
  nomme le projet du run affiché.
- `queue_progress` conserve les événements déjà reçus de la file.
- Sur un ticket en cours, le rond devient « Voir le run » : il amène le run de
  ce ticket au centre.

## Critères d'acceptation

- [ ] Un test de `useCockpit` vérifie qu'après ouverture d'un fichier pendant
      un run, « Revenir au run en cours » est proposé, et de même après
      ouverture d'un diff
- [ ] Un test vérifie que sélectionner dans la Supervision un run d'un autre
      projet fait afficher ses événements par le Pipeline log
- [ ] Un test de `streamState` vérifie qu'après `queue_progress`, les
      événements du ticket précédent sont toujours dans `events`
- [ ] Un test de `TicketCard` vérifie qu'un ticket en cours affiche un bouton
      titré « Voir le run », actif, qui appelle le gestionnaire d'ouverture du
      run

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Garder les événements d'une file entière fait grossir l'état : un éventuel
plafond sur `events` s'applique alors à toute la file.
