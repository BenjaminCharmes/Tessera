---
agent: codeur
created: 2026-11-12
depends_on: []
estimated_days: 0.5
id: ticket-957
pr_number: null
priority: medium
status: todo
title: "A hung Bash call is cut soon after the CLI's own limit, not after twenty minutes"
type: fix
---

# ticket-957 — Un appel Bash figé est coupé peu après la limite du CLI, pas après vingt minutes

## Objectif

Qu'un appel d'outil `Bash` qui ne rend jamais la main coûte une dizaine de
minutes au run, pas vingt.

## Contexte

Le 12/11 (homelab-monitor, ticket-028, 16:39 → 16:59 UTC), le codeur a lancé
`timeout 110 npx --prefix …/frontend tsc -b …`. Plus aucun message n'est venu
du CLI pendant 20 minutes, jusqu'à la garde de silence
(`agent_silence_max_s = 1200`, `services/providers/agent_sdk.py`), qui a coupé
le run en `ProviderIndisponible`. Hypothèse de la session HomeLab : sous Git
Bash, `timeout` tue le lanceur `npx` mais pas le `node` enfant, qui garde le
tuyau ouvert. Aucun processus orphelin ne restait après la coupure.

La garde vaut pour tout silence : une suite de tests lancée par l'agent peut
durer plusieurs minutes sans message. Mais l'outil `Bash` du CLI a sa propre
limite (10 minutes au plus par appel). Un appel `Bash` encore ouvert au-delà
de cette limite est figé, pas lent.

## Solution proposée

1. Pendant qu'un `tool_use` de l'outil `Bash` attend son `tool_result`, la
   borne de silence est `bash_silence_max_s` (nouveau réglage de
   `config.py`, 660 s par défaut : la limite du CLI plus une minute), si elle
   est plus courte que `agent_silence_max_s`.
2. Le reste du temps, la borne reste `agent_silence_max_s`.
3. Le message de `ProviderIndisponible` dit « appel Bash sans réponse depuis
   N s » dans le premier cas, pour que le journal distingue les deux.

## Critères d'acceptation

- [ ] Un test avec un flux simulé : après un `tool_use` `Bash` sans
      `tool_result`, le silence est coupé à `bash_silence_max_s`, avec le
      message « appel Bash ».
- [ ] Un test : après le `tool_result` de cet appel, la borne redevient
      `agent_silence_max_s`.
- [ ] Un test : un `tool_use` d'un autre outil (`Read`) garde
      `agent_silence_max_s`.
- [ ] Un test : `bash_silence_max_s` à 0 désactive la borne propre à Bash.

## Ce que ça ne fait pas

- Ne tue pas l'arbre de processus de l'appel figé : la coupure du CLI le
  fait déjà, et le ticket-943 traite les processus du compte agent.
- Ne change pas `agent_silence_max_s`.
