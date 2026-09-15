---
id: ticket-064
title: "Suivi par ticket et agent de workflow GitHub — PR, CI, conflits, jamais le merge"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-061]
estimated_days: 4
created: 2026-09-15
---

# ticket-064 — Suivi par ticket et agent de workflow GitHub

## Objectif

Voir dans l'IDE ce qui a été fait pour chaque ticket, et confier à un agent la
mécanique GitHub — ouvrir la PR, surveiller la CI, résoudre les conflits.
**Le merge reste manuel.**

## Contexte

### Le suivi manque

`PipelineResult` porte `branch` et `commit_sha`, l'historique des runs est en
base, mais rien ne rassemble en un endroit : ce ticket a produit telle branche,
tel diff, telle PR, la CI est dans tel état. Pour savoir ce qu'un ticket a
réellement changé, il faut sortir de l'IDE et lire `git log`.

### Le workflow GitHub est cassé de bout en bout

L'endpoint `create-pr` appelle l'API GitHub avec `head=<branche>` — mais
**rien, nulle part, ne pousse cette branche**. `git push` n'apparaît pas une
seule fois dans le code. GitHub refuse donc une `head` qu'il ne connaît pas :
la fonctionnalité n'a jamais pu aboutir.

## Solution proposée

### Suivi par ticket

Une vue par ticket rassemblant : branche, commits, diff, PR, état de la CI,
verdicts des agents du run. L'information existe déjà, éparpillée entre
`PipelineResult`, la base et GitHub — il s'agit de la réunir.

### Agent de workflow

Un agent dédié, déclenché explicitement, jamais en bout de pipeline :

1. **Pousser la branche** — le maillon manquant
2. **Ouvrir la PR** vers la base configurée, corps rédigé depuis le ticket et
   le diff réel
3. **Surveiller la CI** — remonter l'état dans l'IDE, sans interroger en boucle
4. **Traiter les conflits** — rebaser sur la base, et en cas de conflit :
   proposer une résolution, **ne jamais l'appliquer seul**
5. **Ne jamais merger**

### Pourquoi jamais le merge

Merger, c'est décider qu'un travail est bon. C'est le seul point du pipeline
où un humain tranche, et c'est ce qui rend acceptable tout le reste de
l'automatisation. Un agent qui mergerait rendrait la relecture facultative.

### Aucune trace d'IA

Le corps des PR et les messages de commit produits par cet agent suivent
[ticket-060](../done/ticket-060-aucune-trace-ia.md) : aucune mention d'outil.

## Critères d'acceptation

- [x] Une vue par ticket montre branche, commits, diff, PR et état de CI
- [x] L'agent pousse la branche avant d'ouvrir la PR
- [x] La PR cible la base configurée du projet
- [x] Son corps est rédigé depuis le ticket et le diff, **sans mention d'IA**
- [x] L'état de la CI remonte dans l'IDE sans interrogation en boucle
- [x] Un conflit produit une proposition de résolution, jamais appliquée seule
- [x] **Aucun chemin de code ne merge une PR**
- [x] L'agent ne se déclenche que sur action explicite
- [x] Un projet sans remote refuse l'action avec un message exploitable

## Dépendances

`ticket-061` — un projet sans remote n'a pas de PR à ouvrir.

## Estimation

**4j**.

## Risques

- **Élevé** — cet agent pousse sur le dépôt de l'utilisateur, potentiellement
  celui d'un client. Mitigations : déclenchement explicite uniquement, jamais
  de push forcé, jamais de merge, et toute résolution de conflit validée par
  l'utilisateur.

## Livré

| Couche | Contenu |
|---|---|
| `git_workspace.py` | `push_branch` — **le maillon manquant** |
| `github_workflow.py` | Pousse puis ouvre la PR, corps rédigé depuis le ticket |
| `routers/tickets.py` | `GET .../activity`, `POST .../open-pr` |
| Frontend | `TicketActivity` dans le panneau Agents |

### Le défaut de fond corrigé

`create-pr` demandait à GitHub une branche `head` que **rien n'avait jamais
poussée** — `git push` n'apparaissait pas une seule fois dans le code. GitHub
refuse une référence qu'il ne connaît pas : la fonctionnalité n'avait jamais pu
aboutir. L'ordre pousser-puis-créer est verrouillé par un test qui vérifie la
séquence d'appels.

### Ce qui est verrouillé par les tests

- **Aucun merge** : ni méthode publique, ni appel dans le module (ADR-022)
- **Aucun push forcé** : un test inspecte le source de `push_branch`
- **Aucune trace d'IA** dans le corps de PR (ticket-060)

## Non livré

La surveillance de CI et la résolution de conflits. Le suivi montre les runs,
la branche et la PR ; l'état de la CI passe encore par `get_pull_request_status`,
qui existe mais n'est pas branché sur cette vue. À reprendre si le besoin se
confirme à l'usage.
