---
name: code-review
description: Use when reviewing a diff, a branch or a pull request in this repository, or when receiving review feedback and deciding what to do with it.
---

# Relire du code

## L'ordre compte

1. **Correction** — ça fait ce que le ticket demande, et ça ne casse rien
2. **Invariants** — aucune garantie existante n'est rompue
3. **Réutilisation** — ça n'existait pas déjà ailleurs
4. **Simplification** — ça peut être plus simple à comportement égal
5. **Style** — en dernier, et seulement si une convention écrite le dit

Ne jamais remonter un point de style avant d'avoir statué sur la correction.

## Ce qui se relit, ici

**Le diff, pas la prose.** L'agent qui décrit son travail décrit une intention.
Relire `git diff`, pas le résumé.

```bash
git diff develop...HEAD          # tout l'apport de la branche
git diff                         # le travail non commité
```

## Les invariants de ce dépôt

Les violations les plus coûteuses portent sur des garanties déjà posées :

| Invariant | Où il est écrit | Ce qui le casse |
|---|---|---|
| L'arbre est propre au démarrage d'un run | ADR-018 | Écrire sans committer |
| Le commit est conditionné à la branche créée | ADR-018 | Committer quand `branch is None` |
| `memory/decisions.md` part dans chaque appel d'agent, filtré par portée | `routers/orchestrator.py`, `routers/agents.py`, `routers/chat.py` → `services/adr.py` | Un ADR de 500 mots ; une portée sur une contrainte |
| `tools` **et** `allowed_tools` toujours explicites | ADR-017 | Ne fixer que `allowed_tools` |
| Les prompts du produit ne sont pas de la config Claude Code | ticket-047 | Déplacer `agents/prompts/` |

## Points de vigilance récurrents

- **`git add -A`** — balaie les projets importés dans `projects/`
- **Fichiers sans `encoding="utf-8"`** — casse sur Windows, silencieusement
- **Texte d'agent interpolé dans un sujet de commit** — un retour ligne coupe
  le message
- **Coercition d'enum au parsing** — une valeur hors liste fait tomber le
  chargement du projet entier, pas seulement le fichier fautif
- **Un `type: ignore` ajouté** — presque toujours le symptôme d'un type à
  corriger en amont

## Formuler une remarque

Dire **ce qui casse**, pas ce qui déplaît. Une remarque utile contient un
scénario d'échec concret.

| ❌ | ✅ |
|---|---|
| Ce nom n'est pas terrible | `_single_line` est appelé après la troncature : un résumé de 200 caractères garde son retour ligne à la position 40 |
| Il faudrait des tests | Aucun test ne couvre le cas où `create_branch` échoue — c'est le chemin qui committait sur `main` avant `beaa28a` |

## Recevoir une revue

Vérifier avant d'appliquer. Une remarque de revue peut être fausse.

1. Reproduire le problème décrit. S'il ne se reproduit pas, le dire, avec la
   commande et sa sortie.
2. S'il se reproduit, écrire d'abord le test qui échoue (→
   `test-driven-development`).
3. Ne pas appliquer une suggestion qu'on ne comprend pas : demander le scénario
   d'échec.

Être d'accord par politesse produit du mauvais code plus vite.

## Avant de valider

- [ ] Relu le diff réel, pas un résumé
- [ ] Aucun invariant du tableau ci-dessus n'est rompu
- [ ] Chaque remarque porte un scénario d'échec concret
- [ ] Les remarques sont ordonnées : correction d'abord, style en dernier
