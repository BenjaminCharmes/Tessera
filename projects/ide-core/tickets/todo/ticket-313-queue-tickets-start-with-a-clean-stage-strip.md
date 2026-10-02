---
id: ticket-313
title: "In a queue, each ticket starts with a clean stage strip, and returning to a run does not repeat its text"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-02
---

# ticket-313 — Dans une file, chaque ticket repart d'une bande d'étapes vierge

## Objectif

Que la vue d'un run en file montre les étapes du ticket **en cours**, et que
revenir sur un run dans la Supervision n'en répète pas le texte.

## Contexte

Capture du 2026-10-02 : `carriere`, file 2/2, ticket-017. Le codeur en est à
son tour 1, mais la bande d'étapes affiche Sécurité, Revue, Validation, Docs
et Livraison cochées : ce sont celles du ticket-016. Et le bloc CODEUR répète
quatre fois le même paragraphe.

**Les étapes du ticket précédent.** Le ticket-283 a cessé de remettre
`events` à zéro sur `queue_progress` (`hooks/streamState.ts`, vers la
ligne 496), pour que le Pipeline log garde l'historique de toute la file. Or
`AgentPanel/StageStrip.tsx` déduit chaque pastille de `events.some(…)`
(lignes 57-110) : il voit donc les événements du ticket d'avant. C'est
exactement le piège que le ticket-180 avait refermé, et le 283 l'a rouvert.

**Le texte répété.** À chaque `subscribe`, `routers/observation.py` renvoie le
tampon de texte du run (`JOURNAL_DU_TEXTE.relire`, ticket-185). Mais le
frontend garde l'état accumulé de chaque run, même désabonné
(`useSupervision.etatDe`), et ajoute ce rejeu au texte qu'il a déjà. Chaque
aller-retour entre deux runs dans la Supervision duplique donc le texte.

## Solution proposée

- Séparer, dans `StreamState`, ce qui appartient au **run** de ce qui
  appartient au **ticket**. Le journal brut de toute la file reste pour le
  Pipeline log. Les événements du ticket en cours repartent de zéro à chaque
  `queue_progress`, et c'est sur eux que `StageStrip` et les autres
  dérivations travaillent.
- Un rejeu de texte après un `subscribe` **remplace** le texte de l'entrée en
  cours au lieu de s'y ajouter, ou les événements rejoués déjà reçus sont
  écartés.

## Critères d'acceptation

- [ ] Un test de `streamState` vérifie qu'après `security_audit_done` du
      ticket A, puis `queue_progress` et `agent_started` du ticket B, la
      pastille Sécurité n'est pas « done » pour B
- [ ] Un test de `streamState` vérifie que les événements du ticket A sont
      toujours dans le journal lu par le Pipeline log après `queue_progress`
- [ ] Un test vérifie qu'un même lot de `agent_token` reçu deux fois (rejeu
      après réabonnement) ne double pas le texte du bloc codeur
- [ ] Un test de `useSupervision` vérifie qu'un aller-retour entre deux runs
      laisse le texte de chacun inchangé
- [ ] Le test de `streamState` du ticket-180 (le bloc reviewer d'un ticket
      précédent ne s'affiche pas sous le suivant) passe toujours

## Dépendances

Aucune.

## Risques

`events` sert à plusieurs consommateurs (Pipeline log, bande d'étapes, carte
de résumé). Chacun doit lire la bonne portée : le tour de plan les recense
avant de couper.
