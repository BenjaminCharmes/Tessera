---
id: ticket-057
title: "Les ADR doivent être chargés, pas espérés"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-047]
estimated_days: 1
created: 2026-09-15
---

# ticket-057 — Charger les ADR au lieu d'espérer qu'on les lise

## Objectif

Garantir que les contraintes d'architecture atteignent l'agent qui code, à
chaque session, sans dépendre de sa mémoire ni de son initiative.

## Contexte

Constat fait à l'usage : **rien ne garantit qu'un agent connaisse les ADR.**

| Fichier | Chargé automatiquement dans Claude Code ? |
|---|---|
| `CLAUDE.md` (racine) | ✅ Toujours |
| `projects/ide-core/CLAUDE.md` | ❌ Non — la ligne 14 demande de le lire |
| `memory/decisions.md` | ❌ **Non, et rien n'y renvoie** |

La règle 3 de `CLAUDE.md` dit d'**écrire** dans `decisions.md`. Aucune règle ne
dit de le **lire**. Une session neuve ignore donc qu'ADR-018 existe, et peut
casser la garantie d'arbre propre dont dépend tout l'enchaînement des tickets
sans même savoir qu'elle existe.

Côté produit le problème n'existe pas : `routers/orchestrator.py` et
`routers/agents.py` injectent `decisions.md` dans le contexte de chaque appel
d'agent. C'est **côté Claude Code** que le trou se trouve.

### L'erreur de raisonnement à corriger

Les `@`-imports ont été écartés en ticket-047 au motif qu'ils coûtent des
tokens à chaque session. C'était une confusion entre deux budgets :

- **Côté produit** — `decisions.md` part sur *chaque appel d'agent*, jusqu'à 18
  par ticket. Là, la longueur compte vraiment (d'où ADR-017/018 raccourcis).
- **Côté session Claude Code** — ~2000 tokens **une seule fois**. Négligeable
  au regard du coût d'une décision d'architecture violée par ignorance.

## Solution proposée

1. **`@`-imports dans `CLAUDE.md`** pour `projects/ide-core/CLAUDE.md` et
   `projects/ide-core/memory/decisions.md` : ce qui doit toujours tenir doit
   toujours être chargé.
2. **Une règle de lecture**, symétrique de la règle d'écriture : consulter les
   ADR avant toute décision d'architecture.
3. **Corriger la discipline `git add -A`** — le skill `ticket-workflow`
   l'interdit, mais la forme `git add -A -- <chemins>` a été utilisée à
   répétition. Le skill doit dire ce qu'il faut faire à la place, pas seulement
   ce qu'il faut éviter.

## Contrainte

Ce ticket **autorise la modification de `CLAUDE.md`** (règle 4), pour la
section des `@`-imports et la règle de lecture des ADR.

## Critères d'acceptation

- [x] `CLAUDE.md` importe `projects/ide-core/CLAUDE.md` et `decisions.md`
- [x] Une règle impose de consulter les ADR avant une décision d'architecture
- [x] Le skill `ticket-workflow` donne la commande de remplacement de
      `git add -A`, pas seulement l'interdiction
- [x] `CLAUDE.md` explique pourquoi l'import est justifié ici alors que les
      skills restent à la demande — sinon l'arbitrage sera rejoué
- [x] Le coût ajouté par session est mesuré et consigné

## Dépendances

`ticket-047` — c'est la décision de ce ticket qui est corrigée.

## Estimation

**1j**.

## Risques

- **Faible** — le seul coût est en tokens de session, mesuré et assumé.

## Coût mesuré

| Fichier importé | Mots |
|---|---|
| `projects/ide-core/CLAUDE.md` | 722 |
| `projects/ide-core/memory/decisions.md` | 1569 |
| **Total** | **2291** (~3100 tokens, une fois par session) |

À comparer au coût côté produit, qui reste la vraie contrainte de longueur des
ADR : `decisions.md` part sur chaque appel d'agent, jusqu'à 18 par ticket.
