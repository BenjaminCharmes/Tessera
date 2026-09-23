---
id: ticket-130
title: "Faire apparaître les sessions de chat dans la vue Supervision"
type: feat
status: in-review
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-129"]
estimated_days: 1
created: 2026-09-23
---

# ticket-130 — Faire apparaître les sessions de chat dans la Supervision

## Objectif

Montrer les sessions de chat en cours à côté des runs de pipeline, pour que la
vue Supervision dise vraiment tout ce que l'IDE est en train d'écrire.

## Contexte

ADR-019 fait du chat un producteur de travail de première classe : il écrit
sur une branche `chat-<horodatage>` et commite, exactement comme un run. Mais
il garde sa propre socket `/chat/{project_id}` et a été laissé **hors du
périmètre** de ticket-129 pour ne pas doubler la surface de ce chantier.

Conséquence assumée en attendant : un chat qui écrit dans un dépôt n'apparaît
nulle part dans la supervision.

## Solution proposée

Faire publier le chat sur l'`EventHub` de ticket-127, et le représenter dans
le registre comme un run d'un mode supplémentaire (`chat`). La vue le distingue
des runs de pipeline — il n'a ni ticket, ni étapes, ni verdict.

À décider au moment de l'implémentation : le chat conserve-t-il sa socket
propre pour le dialogue, ou passe-t-il lui aussi par le canal d'observation ?
Les deux se défendent ; ticket-128 aura montré ce que coûte la seconde option.

## Critères d'acceptation

- [ ] Un chat en cours apparaît dans l'instantané du registre
- [ ] Un test vérifie que la vue Supervision distingue visuellement une
      session de chat d'un run de pipeline
- [ ] Un test vérifie que le badge compte les chats actifs
- [ ] `RunLock` continue de refuser un pipeline sur un projet où un chat écrit
- [ ] `uv run pytest`, `npm run test` et `npx tsc --noEmit` passent

## Dépendances

ticket-129.

## Estimation

1 jour.

## Risques

Le chat et le pipeline partagent le verrou projet (ADR-038) mais pas le cycle
de vie : un chat n'a pas de fin naturelle. Le registre doit savoir fermer une
entrée que personne ne clôt explicitement.
