---
agent: codeur
created: 2026-09-30
depends_on:
- ticket-256
estimated_days: 1
id: ticket-257
pr_number: 155
priority: high
status: done
title: Supervision and the run view share one timeline, with security and validator
  verdicts in it
type: feat
---

# ticket-257 — Un seul fil du run, avec les verdicts sécurité et validateur

## Objectif

Que la Supervision et l'onglet du run racontent la même histoire d'un run, et
que cette histoire dise **pourquoi** un run repart pour un tour.

## Contexte

Constaté en réel le 2026-09-30 sur le ticket-253, trois tours :

- `RunView` (onglet du run) affiche le fil chronologique de tous les passages
  d'agents (ticket-222) : reviewer, codeur, reviewer, codeur, reviewer.
- `AgentPanel` (Supervision) n'affiche que deux blocs, codeur et reviewer, du
  tour en cours (`blocsDuPanneau.ts`). Les tours précédents disparaissent.
- **Aucune des deux ne montre le validateur.** Il a refusé aux tours 1 et 2
  alors que le reviewer approuvait : à l'écran, « reviewer APPROVED → le codeur
  repart » sans raison visible. La raison n'était lisible que dans
  `memory/pipeline-log.md`.

Le fil se construit dans `hooks/streamState.ts` : chaque `agent_started` ajoute
une `PassageAgent` à `entries`. L'audit et la validation n'attribuent aucun
agent à leurs événements, donc n'y entrent jamais. Leurs événements portent
pourtant tout ce qu'il faut :
- `security_audit_done` : `verdict`, `summary`, `issues_count`, `reason` ;
- `validation_done` : `verdict`, `feedback`, et `criteria` — une liste de
  `{criterion, passed, note}`.

## Solution proposée

- Dans `streamState.ts`, `security_audit_done` et `validation_done` ajoutent
  chacun une entrée au fil, avec le tour en cours, marquée terminée. Élargir le
  type d'entrée pour porter ces deux genres (le champ `agent` accepte
  `securite` et `validateur`, ou un champ `genre` distinct — au choix du codeur,
  sans `any`).
- Extraire le rendu du fil de `components/RunView/index.tsx` en un composant
  partagé (`FilDuRun`), utilisé par `RunView` **et** par `AgentPanel`, à la
  place des deux `AgentBlock` pilotés par `blocsDuPanneau`.
- Une entrée validateur affiche son verdict en en-tête replié et, dépliée, le
  `feedback` puis la liste des critères, chacun avec son état (réussi / échoué)
  et sa `note`. Une entrée sécurité affiche son verdict et son `summary`.
- Couleurs ADR-026 : `green` pour un verdict favorable, `red` pour un refus,
  jamais de violet en texte ; glyphes depuis `design/icons.tsx`.
- `AgentDialogue` (question d'un agent) et la frise d'étapes du ticket-256
  restent dans `AgentPanel`, au-dessus du fil.

## Critères d'acceptation

- [ ] Un test de `streamState` montre qu'un événement `validation_done` ajoute
      une entrée au fil, portant son verdict et ses critères.
- [ ] Un test de `streamState` montre qu'un événement `security_audit_done`
      ajoute une entrée au fil, portant son verdict.
- [ ] `FilDuRun` existe et est importé à la fois par `components/RunView/index.tsx`
      et par `components/AgentPanel/index.tsx`.
- [ ] Un test d'`AgentPanel` montre qu'après deux tours, le passage du codeur
      au tour 1 est toujours affiché.
- [ ] Un test montre qu'une entrée validateur `CHANGES_REQUESTED` dépliée
      affiche le texte de la `note` d'un critère échoué.

## Dépendances

ticket-256 — il ajoute la frise d'étapes dans `AgentPanel` ; ce ticket passe
après pour ne pas modifier le même fichier en parallèle.

## Estimation

1 jour. Frontend uniquement.

## Risques

- `blocsDuPanneau.ts` sert à un observateur arrivé en cours de run
  (ticket-182) : le fil est vide pour lui, puisque les événements passés ne lui
  parviennent pas. Garder ce repli — si `entries` est vide, afficher le bloc de
  l'agent courant comme aujourd'hui — plutôt que de le supprimer.
- `AgentPanel.test.tsx` et `RunView.test.tsx` cherchent les blocs actuels : les
  adapter sans perdre ce qu'ils vérifient.
- Hors périmètre : rejouer l'historique d'un run à la reconnexion.