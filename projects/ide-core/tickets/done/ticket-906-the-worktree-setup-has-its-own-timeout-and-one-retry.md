---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 1
id: ticket-906
plan: true
pr_number: 1012
priority: medium
status: done
title: The worktree setup has its own timeout, and one retry when it times out
type: feat
---

# ticket-906 — La préparation d'un worktree a son propre délai, et une relance

## Objectif

Une installation de dépendances lente ne doit plus bloquer un run parce
qu'elle emprunte le délai des tests et ne réessaie jamais.

## Contexte

`preparation_du_run` (`backend/src/tessera/services/pipeline/preparation_worktree.py`)
lance `worktree.setup` avec le délai du testeur, `pipeline.test_timeout_s`
(`assemblage_run.py`). Chez Kadoomi, ce délai vaut 420 s et le setup est
`corepack pnpm@10 install --frozen-lockfile`.

Durées relevées le 2026-11-10 : 174 s, 322 s, puis un arrêt à 420 s pendant
qu'un autre worktree lançait vitest. Le run s'est terminé `blocked`
(`worktree_setup_failed`) sans qu'aucun agent ait travaillé.

Deux choses ne vont pas. Le setup n'a aucune raison de partager le délai des
tests. Et un setup coupé par un délai réussit en général à la deuxième
tentative, alors qu'une vraie erreur, comme un lockfile désynchronisé, échoue
à chaque fois.

Hors périmètre : réutiliser les `node_modules` d'un autre worktree. Une
jonction de `node_modules` dans un worktree a déjà détruit l'arbre d'un
checkout, et pnpm partage déjà son store global.

## Solution proposée

- Une clé optionnelle `worktree.setup_timeout_s` (entier positif), lue dans
  `worktree_politique.py`, refusée si elle est mal typée, comme `setup`. Sans
  elle, le délai reste `pipeline.test_timeout_s`.
- `assemblage_run.py` passe ce délai à `preparation_du_run`.
- Dans `preparation_du_run`, quand le setup échoue **par délai dépassé**, une
  seule relance, journalisée. Un échec par code de sortie non nul ne se relance
  pas. Le tour de plan dit comment `TestRunnerService` distingue un délai d'un
  code de sortie.

## Critères d'acceptation

- [ ] `worktree_politique.py` lit `setup_timeout_s`, et un test vérifie qu'une
      valeur non entière ou négative est refusée
- [ ] Un test vérifie que `preparation_du_run` reçoit `setup_timeout_s`
      quand il est déclaré, et `test_timeout_s` sinon
- [ ] Un test vérifie, avec un double de `TestRunnerService`, qu'un setup
      arrêté par délai est relancé une fois, et que le run continue si la
      relance réussit
- [ ] Un test vérifie, avec le même double, qu'un setup qui sort avec un code
      non nul n'est pas relancé
- [ ] Un test vérifie que deux délais dépassés de suite terminent le run en
      `worktree_setup_failed`, comme aujourd'hui

## Dépendances

Aucune. La valeur de Kadoomi (`setup_timeout_s` dans son `agents.json`) se
déclare à la main après le merge : aucun agent n'écrit `agents.json`.

## Estimation

1 jour.

## Risques

Une relance double le temps perdu quand le délai est trop court par nature :
le délai reste à déclarer correctement, la relance couvre la charge passagère.