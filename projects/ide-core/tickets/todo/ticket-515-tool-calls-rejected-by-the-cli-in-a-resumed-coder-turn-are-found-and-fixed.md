---
id: ticket-515
title: "Tool calls rejected by the CLI in a resumed coder turn are diagnosed, logged and no longer cost a round"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-19
---

# ticket-515 — Des appels d'outils refusés par le CLI dans un tour de codeur repris

## Objectif
Qu'un tour de codeur ne soit plus perdu parce que le CLI embarqué refuse ses
appels d'outils dans le projet, et qu'un tel refus soit visible dans le journal.

## Contexte
Le 19/10, Kadoomi ticket-034, run `93c6d590` : au tour 2 (reprise de la
session du codeur, ticket-187), un `Edit` sur `src/app/connexion/submit.ts`
(13:18:14 UTC) puis un `Grep` sous `src/` (13:18:15 UTC), tous deux **dans
le projet**, ont reçu du CLI : « The user doesn't want to take this action
right now. STOP what you are doing and wait for the user to tell you how to
proceed. » Le codeur s'est arrêté, et le tour a duré 11 s pour rien. Au tour 3,
qui reprenait la même session, les mêmes appels ont réussi. Le run s'est
bloqué après trois tours : un tour sur trois a été perdu.

Ce n'est pas le garde de Tessera : ses refus `PreToolUse` arrivent sous la
forme « PreToolUse:<outil> hook error: Écriture refusée… » (même transcription,
13:12:28). Tessera n'appelle jamais `interrupt()`, et aucun `stop` n'a été
demandé sur ce run. Le message est celui que le CLI rend quand une permission
est refusée sans callback : l'outil n'a pas été auto-approuvé
(`permission_mode="acceptEdits"`, `allowed_tools`, `cwd` dans
`backend/src/tessera/services/providers/agent_sdk.py`).

Preuve : la transcription du CLI
`~/.claude/projects/C--Users-Benjamin-CHARMES-Desktop-tessera-projects-kadoomi/531738e2-dfa5-46c4-9bd3-201dd0197564.jsonl`
(lignes 376 et 378).

## Solution proposée
1. Diagnostic (tour de plan) : comparer les `ClaudeAgentOptions` d'un tour
   initial et d'un tour repris (`cwd`, `allowed_tools`, `tools`,
   `permission_mode`, `resume`, `settings`). Chercher ce qui peut faire sortir
   un outil de l'auto-approbation dans une session reprise.
2. Corriger la cause, avec un test de non-régression sur les options d'un
   tour repris.
3. Quoi qu'il en soit : un refus de permission du CLI (ce texte exact dans un
   `tool_result` en erreur) écrit une ligne dans `memory/pipeline-log.md`,
   `[ticket-XXX] codeur: outil <nom> refusé par le CLI`, pour qu'il ne reste
   plus invisible.

## Critères d'acceptation
- [ ] Le plan nomme la cause trouvée, ou les hypothèses écartées avec leur preuve
- [ ] Un test vérifie que les options d'un tour repris gardent le même `cwd`, les mêmes `allowed_tools` et le même `permission_mode` que le tour initial
- [ ] Un test vérifie qu'un `tool_result` en erreur portant le message de refus du CLI produit la ligne `codeur: outil <nom> refusé par le CLI` dans le journal
- [ ] Les tests existants de `agent_sdk` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Un jour.

## Risques
Cause peut-être côté CLI embarqué (version du SDK) : dans ce cas, le
journal du critère 3 reste le livrable minimal, et la cause est documentée.
