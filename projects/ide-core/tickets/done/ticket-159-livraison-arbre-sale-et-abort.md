---
id: ticket-159
title: "La livraison échoue sur un arbre que le pipeline vient lui-même de salir"
type: fix
status: done
pr_number: 3
priority: high
agent: codeur
depends_on: ["ticket-158"]
estimated_days: 1
created: 2026-09-23
---

# ticket-159 — La livraison échoue sur un arbre sali par le pipeline

## Objectif

Qu'un run approuvé sur un projet en `autonomy: pr` ouvre réellement sa PR.

## Contexte

Premier run **approuvé** du projet démineur : codeur, testeur au vert,
sécurité `PASS`, reviewer, validateur `APPROVED` en un seul tour. Le commit
porte le type du ticket, `feat:`. Puis :

```
livraison_echouee: git command failed (code 128):
  git … rebase --abort
  fatal: no rebase in progress
```

Aucune branche n'est poussée, aucune PR n'est ouverte. Le run garde son
résultat — ADR-030 tient, une livraison ratée ne fait pas échouer le run —
mais le travail reste sur la machine.

## Deux défauts enchaînés

### 1. L'arbre est sale quand la livraison commence

Sur la branche du run, juste après :

```
 D tickets/in-review/ticket-001-modele-de-grille.md
?? tickets/done/
```

Le pipeline déplace le fichier du ticket de `in-review/` vers `done/` **après**
son dernier commit. `git rebase` refuse alors de démarrer :
`cannot rebase: You have unstaged changes`.

C'est la prémisse d'ADR-018 prise à revers : le run s'achève en laissant
l'arbre sale, ce que cet ADR interdit précisément pour que le ticket suivant
puisse démarrer. Ici ce n'est pas le ticket suivant qui trinque, c'est la
livraison du ticket courant.

### 2. `rebase --abort` est appelé quand aucun rebase n'est en cours

`GitWorkspaceService` :

```python
try:
    await self._run("rebase", base)
except GitCommandError:
    pass
...
if resolveur is None or not conflits:
    await self._run("rebase", "--abort")
```

Un rebase qui échoue **sans conflit** n'a rien laissé en cours : l'annuler
lève à son tour, et c'est cette seconde erreur qui remonte. Le message final
parle donc de `--abort`, jamais de la vraie cause — un arbre sale.

Les deux se corrigent séparément. Le second seul ferait apparaître le vrai
message ; le premier seul suffirait ici, mais laisserait l'annulation
fragile au prochain rebase qui échoue pour une autre raison.

## Solution proposée

1. Committer le déplacement du ticket **avec** le commit de fin de run, ou
   avant la livraison — ADR-018 veut un arbre propre à la sortie, et il ne
   l'est pas.
2. N'annuler que s'il y a quelque chose à annuler (`.git/rebase-merge` ou
   `rebase-apply` présent), et remonter l'erreur d'origine sinon.

## Critères d'acceptation

- [ ] Un run approuvé laisse l'arbre propre, déplacement du ticket compris
- [ ] Un rebase qui échoue sans conflit remonte **son** erreur, pas celle de
      `--abort`
- [ ] Un test couvre le rebase refusé pour arbre sale
- [ ] Un run approuvé sur un projet en `autonomy: pr` pousse sa branche et
      ouvre sa PR

## Dépendances

ticket-158.

## Estimation

Moins d'une journée.

## Risques

Committer plus tôt le déplacement du ticket change ce que le reviewer voit
du diff. Il relit le diff git réel (ADR-018) : un fichier de ticket déplacé
y apparaîtrait. À vérifier qu'il ne le prend pas pour du code.
