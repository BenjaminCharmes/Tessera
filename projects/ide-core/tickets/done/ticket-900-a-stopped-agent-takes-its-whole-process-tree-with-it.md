---
agent: codeur
created: 2026-11-09
depends_on:
- ticket-894
estimated_days: 1
id: ticket-900
plan: true
pr_number: 1007
priority: high
status: done
title: A stopped agent takes its whole process tree with it
type: fix
---

# ticket-900 — Un agent arrêté emporte tout son arbre de processus

## Objectif

Quand Tessera arrête un appel d'agent, que ce soit pour silence, annulation,
exception ou fin normale, tous les processus que l'agent a lancés meurent avec
lui. Plus aucun orphelin ne doit verrouiller un worktree.

## Contexte

Le 2026-11-09, le codeur du run Kadoomi `eeac187c` (ticket-145) a lancé
`python3 -`, qui attendait sur stdin. Au bout de 1 200 s, `agent_sdk.py` a levé
`ProviderIndisponible("agent silencieux depuis 1200 s")` et fermé le
générateur du SDK. Le CLI est bien mort, mais ses enfants ont survécu :
`bash > bash > bash > python3`, plus un `conhost`. Ils tenaient encore
`~/.tessera/worktrees/kadoomi/ticket-145`. Le worktree ne se supprimait pas
(« Device or resource busy »), et toute relance du ticket échouait aussitôt.

Sous Windows, `taskkill /T` ne suit plus l'arbre une fois qu'un maillon a
disparu, ce qui est ici le cas du CLI. `services/noyau/groupe_de_processus.py`
sait déjà faire ce qu'il faut : un *job object* avec `KILL_ON_JOB_CLOSE`
(`creer_groupe`, `rattacher_au_groupe`, `fermer_le_groupe`). Il est utilisé
pour les services et les étapes de test, mais pas pour le CLI des agents.

Ce ticket dépend de 894, qui change la façon dont le CLI est lancé (sous le
compte de l'agent). Le rattachement doit valoir dans les deux cas.

## Solution proposée

- À chaque appel d'agent, créer un groupe (`creer_groupe`) et y rattacher le
  processus du CLI dès qu'il est lancé, avant sa première commande. Ses enfants
  y entrent alors d'eux-mêmes.
- Dans un `finally` autour de la boucle de `agent_sdk.py` (silence, exception,
  annulation, fin normale), fermer le groupe avec `fermer_le_groupe`.
- Le tour de plan dit comment obtenir le PID du CLI depuis le SDK (transport,
  ou lanceur de 894), et ce qui se passe sans groupe disponible (Unix) : le
  journaliser, ne pas bloquer.

## Critères d'acceptation

- [ ] Un test vérifie, avec des doubles de `creer_groupe`,
      `rattacher_au_groupe` et `fermer_le_groupe`, que l'appel d'agent
      rattache le PID du CLI au groupe et ferme le groupe quand le flux se
      termine normalement
- [ ] Un test vérifie, avec les mêmes doubles, que le groupe est fermé quand
      l'appel lève `ProviderIndisponible` pour silence
- [ ] Un test vérifie, avec les mêmes doubles, que le groupe est fermé quand
      l'appel est annulé (`asyncio.CancelledError`)
- [ ] Un test vérifie que, lorsque `creer_groupe` renvoie `None`, l'appel
      d'agent se déroule normalement et journalise l'absence de groupe

## Dépendances

ticket-894 (lanceur du CLI sous le compte de l'agent).

## Estimation

1 jour.

## Risques

- Un job object Windows n'admet un processus que si celui-ci n'est pas déjà
  dans un job incompatible. Le backend est lui-même dans un job (ticket-150) :
  le groupe doit être imbriqué, comme pour les étapes de test.
- Ce ticket ne règle pas le `python3 -` qui fige. Il garantit seulement que la
  coupure au bout de 1 200 s nettoie derrière elle.