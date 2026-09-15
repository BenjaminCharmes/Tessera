---
name: write-adr
description: Use when recording a non-trivial architecture decision in memory/decisions.md — enforces the house format and the length budget, because that file is injected whole into every agent call.
---

# Écrire un ADR

## Le coût caché — lire ceci en premier

`routers/orchestrator.py` et `routers/agents.py` injectent **l'intégralité** de
`memory/decisions.md` dans le contexte projet de **chaque** appel d'agent. Sur
un ticket qui va au bout, c'est jusqu'à 18 appels. Un ADR de 500 mots coûte
donc ~650 tokens × 18, à chaque ticket, pour toujours.

Un ADR long n'est pas un défaut de style. C'est une taxe permanente.

## Budget

| | Mots |
|---|---|
| ADR-001 à ADR-016 (référence) | 46 – 72 |
| Décision structurante, avec conséquence assumée | ≤ 160 |
| **Jamais** | > 200 |

Si tu dépasses, tu écris une spec, pas un ADR. La spec va dans le ticket.

## Format

```markdown
## ADR-0XX — Titre à l'impératif, pas de nom de ticket

**Date** : AAAA-MM-JJ
**Décision** : Ce qui est décidé. Au présent, à l'actif.
**Raison** : Pourquoi, en pointant la contrainte réelle qui force le choix.
**Alternative rejetée** : Ce qu'on n'a pas fait, et ce qui le disqualifie.
**Détail** : voir `tickets/.../ticket-XXX-....md`   ← si le sujet est vaste
```

Deux lignes optionnelles, seulement quand elles portent une information qu'on
regretterait de perdre :

- **Conséquence assumée** — un effet indésirable accepté en connaissance de
  cause (exemple : ADR-018 écrit du code bloqué par la sécurité dans
  l'historique git).

## Ce qui n'a rien à faire dans un ADR

| À écrire ailleurs | Où |
|---|---|
| Le détail d'implémentation | Le ticket |
| Les invariants à respecter dans le code | Un commentaire, à l'endroit où ils s'appliquent |
| La liste des fichiers touchés | Le message de commit |
| Le mode d'emploi | `docs/guide-utilisateur.md` |

## Numérotation

Prendre le numéro suivant le plus élevé du fichier. Les ADR ne sont pas
réordonnés ni renumérotés — ADR-011 apparaît après ADR-016 dans le fichier,
c'est l'ordre d'écriture, il n'a pas d'importance.

## Avant de valider

- [ ] Sous 160 mots
- [ ] La ligne « Alternative rejetée » dit pourquoi elle est rejetée, pas
      seulement laquelle
- [ ] Aucun détail d'implémentation qui vivrait mieux dans le ticket
- [ ] Le titre se comprend sans lire le corps
