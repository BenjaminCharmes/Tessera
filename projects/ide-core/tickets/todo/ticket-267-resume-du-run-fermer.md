---
id: ticket-267
title: "Run summary: working Close in Supervision, ticket id shown, not 'finished' before delivery"
type: fix
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-30
---

# ticket-267 — Le résumé du run : Fermer marche, le ticket s'affiche, « terminé » attend la livraison

## Objectif

Que le bloc de fin de run dans la Supervision dise vrai et que son bouton serve.

## Contexte

Constaté le 2026-09-30 sur le run du ticket-265, dans la Supervision :

1. **« Fermer » ne fait rien.** `SupervisionView/index.tsx` passe à
   `AgentPanel` un `clear` qui vaut `rien` (fonction vide).
2. **La croix et « Fermer » ne sont pas sur la même ligne** : dans
   `AgentPanel/index.tsx`, le bouton contient `<IconCross /> Fermer` sans
   `inline-flex`.
3. **« Ticket : » est vide** dans `PipelineSummary` : le résultat prend
   `ev.data["ticket_id"]`, puis `s.ticketId`, que l'état de la Supervision ne
   renseigne pas. L'événement porte pourtant `ticket_id` à son premier niveau
   (`OrchestratorEvent.ticket_id`).
4. **« Pipeline terminé » s'affiche pendant que la carte dit « en cours »** :
   `pipeline_done` part après la validation ; documentation et livraison
   tournent encore jusqu'à `run_closed` (ADR-041).

## Solution proposée

- `clear` dans la Supervision retire le run terminé de la liste (ou masque son
  détail) ; un run encore en cours ne se ferme pas — le bouton n'apparaît
  qu'après `run_closed`.
- Bouton en `inline-flex items-center gap-1`.
- Le résultat prend `ev.ticket_id` quand `ev.data["ticket_id"]` est absent.
- Entre `pipeline_done` et `run_closed`, le titre du bloc devient « Revue
  terminée — livraison en cours » ; « Pipeline terminé » n'apparaît qu'après
  `run_closed`.

## Critères d'acceptation

- [ ] Un test de la Supervision montre qu'un clic sur « Fermer » d'un run clos
      le retire de la liste des cartes.
- [ ] Un test montre que « Fermer » n'est pas rendu tant que `run_closed` n'est
      pas reçu.
- [ ] Un test montre que `PipelineSummary` affiche l'identifiant du ticket
      quand seul `ev.ticket_id` le porte.
- [ ] Un test montre qu'après `pipeline_done` et avant `run_closed`, le bloc
      affiche « livraison en cours » et pas « Pipeline terminé ».
- [ ] Le bouton « Fermer » porte la classe `inline-flex`.

## Dépendances

Aucune.

## Estimation

Une demi-journée. Frontend uniquement.

## Risques

Les tickets 256, 257 et 266 touchent aussi `AgentPanel` et la Supervision : si
l'un est mergé avant, repartir de `develop` à jour.
