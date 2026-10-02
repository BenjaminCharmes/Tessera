---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 1
id: ticket-286
pr_number: 183
priority: medium
status: done
title: A running run shows its ticket's title, in Supervision and in the run view
type: feat
---

# ticket-286 — Un run affiche le titre de son ticket

## Objectif

Qu'on sache de quoi parle un run sans ouvrir son ticket : la carte de la
Supervision et l'en-tête « Agents » affichent le titre du ticket à côté de
son numéro.

## Contexte

Retour d'usage du 2026-10-01 : la Supervision et la vue du run n'affichent
que `ticket-XXX`, parfois rien du tout.

- `RunActif` (`services/run_registry.py:34-95`) ne porte que `ticket_id`, et
  pas de titre. `run_executor` ne le remplit qu'à partir des événements
  (`run.ticket_id = event.ticket_id or run.ticket_id`,
  `services/run_executor.py:92`). Une file qui démarre, avant son premier
  événement de ticket, n'a donc aucun `ticket_id`.
- `SupervisionView/RunCard.tsx:94` affiche `run.ticket_id ?? "—"`.
  `AgentPanel/index.tsx:94-96` n'affiche `— {ticketId}` que si l'id est
  connu, et rien sinon.
- Le frontend ne peut pas retrouver le titre seul : la Supervision couvre tous
  les projets, et seuls les tickets du projet actif sont chargés.

## Solution proposée

- `RunActif` gagne un champ `ticket_titre`, sérialisé par `en_dict` et donc
  présent dans l'instantané de la WebSocket.
- Quand `ticket_id` change dans `run_executor`, le titre est lu depuis le
  ticket du projet. Une lecture qui échoue laisse le titre à `None` et
  n'interrompt pas le run.
- Une file connaît son premier ticket dès le lancement : `ticket_id` et
  `ticket_titre` sont remplis à la création du `RunActif`.
- `RunCard` affiche le titre sous le numéro, tronqué sur une ligne, avec le
  titre complet dans `title`. L'en-tête d'`AgentPanel` affiche
  `— ticket-XXX · Titre`, tronqué.

## Critères d'acceptation

- [ ] Un test backend vérifie que `en_dict()` contient `ticket_titre`
- [ ] Un test backend vérifie qu'après un événement portant un nouveau
      `ticket_id`, `ticket_titre` est le titre de ce ticket
- [ ] Un test backend vérifie qu'une file a `ticket_id` et `ticket_titre`
      renseignés avant tout événement
- [ ] Un test backend vérifie qu'un ticket illisible laisse `ticket_titre` à
      `None` sans lever d'exception
- [ ] Un test de `RunCard` vérifie l'affichage du titre et de son attribut
      `title`
- [ ] Un test d'`AgentPanel` vérifie que l'en-tête affiche le titre du ticket

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

La lecture du ticket se fait à chaque changement de `ticket_id` : une par
ticket, pas une par événement.