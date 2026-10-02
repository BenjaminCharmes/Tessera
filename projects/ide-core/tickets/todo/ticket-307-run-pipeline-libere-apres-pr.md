---
id: ticket-307
title: "run_pipeline libère le verrou après la PR et gère depends_on"
type: feat
status: todo
priority: high
agent: codeur
---

# ticket-307 — run_pipeline libère le verrou après la PR et gère depends_on

## Objectif

Brancher `livrer_phase_1` dans `run_pipeline` et confier la phase 2 à
`CIWatcher`. Le verrou de projet (ADR-038) se libère après `run_closed`
(ADR-041), dès la PR ouverte. Ajouter la lecture de `depends_on` dans
`run_queue` : un ticket qui déclare dépendre d'un autre attend son merge
avant de démarrer.

## Contexte

ADR-051. `run_pipeline` appelle aujourd'hui `self._livrer(resultat)` qui
bloque sur la CI. Après ticket-305 et ticket-306, il appelle `livrer_phase_1`
puis soumet la phase 2 à `CIWatcher`, sans attendre.

## Critères d'acceptation

- [ ] `run_pipeline` appelle `livrer_phase_1`, émet `LIVRAISON_DONE` avec le
      `pr_number`, confie la phase 2 à `CIWatcher` sans `await`
- [ ] `run_closed` est émis avant la fin de la phase 2
- [ ] `run_queue` lit `ticket.depends_on` ; si une dépendance est en `pr_open`
      (PR ouverte, merge en attente), le ticket suivant attend avant de démarrer
- [ ] Un test couvre le cas de base : pipeline approuvé → `livrer_phase_1` appelée
      → `CIWatcher.surveiller` appelé → `run_closed` émis
- [ ] Un test couvre `depends_on` : ticket B attend que A soit `done` avant de
      démarrer quand A a une PR ouverte
- [ ] Les tests existants de `run_pipeline` (arbre sale, non approuvé) passent

## Dépendances

ticket-305, ticket-306

## Périmètre

`backend/src/tessera/services/orchestrator.py`,
`backend/src/tessera/models/ticket.py` (champ `depends_on` si absent).
