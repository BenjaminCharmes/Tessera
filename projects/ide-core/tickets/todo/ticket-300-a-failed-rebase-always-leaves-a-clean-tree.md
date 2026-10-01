---
id: ticket-300
title: "A delivery rebase that stops always gives the tree back, even with untracked files in the way"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
plan: true
created: 2026-10-01
---

# ticket-300 — Un rebase de livraison arrêté rend toujours l'arbre

## Objectif

Que l'arbre ne reste jamais à mi-rebase après une livraison, comme ADR-033
le promet.

## Contexte

Le 2026-10-01, la livraison du ticket-282 a buté sur un conflit
« modifié / supprimé » : `develop` avait modifié son fichier ticket dans
`todo/`, et la branche le déplaçait dans `done/`. Le `rebase --abort` de
`rejouer_sur` (`services/git_workspace.py:687` et `:707`) a alors échoué :

```
error: The following untracked working tree files would be overwritten by reset:
	projects/ide-core/tickets/done/ticket-282-agent-cards-share-one-header.md
fatal: could not move back to 7778a78
```

Pendant le rebase, le fichier `done/` n'était pas suivi, et quelque chose
l'avait écrit dans l'arbre. L'exception a remonté jusqu'à `Livraison.arret`,
sans PR, et l'arbre est resté à mi-rebase. Le ticket suivant de la file, le
283, a trouvé l'arbre sale. Il a été marqué `blocked`, et son fichier
déplacé dans `blocked/`, sans qu'aucun agent ait tourné.

## Solution proposée

- Le tour de plan établit d'abord qui écrit le fichier `done/` pendant le
  rebase : la mise à jour de statut du ticket, la documentation, ou le
  résolveur de conflit.
- `rejouer_sur` garantit l'annulation : si `rebase --abort` échoue sur des
  fichiers non suivis, ceux qui portent un nom d'artefact Tessera sont mis de
  côté et l'annulation est retentée. En dernier recours, l'arbre revient à la
  pointe d'origine de la branche, sans rien perdre de ce qui était commité.
- Un conflit qui ne porte que sur le fichier ticket du run se résout en
  faveur de la branche, dont le fichier fait foi pour son propre statut.

## Critères d'acceptation

- [ ] Un test sur un dépôt git temporaire reproduit le conflit
      « modifié sur la base / déplacé sur la branche » d'un fichier ticket, et
      vérifie que `rejouer_sur` aboutit, la version de la branche gardée
- [ ] Un test vérifie qu'un `rebase --abort` gêné par un fichier non suivi
      laisse quand même l'arbre propre, sur la branche d'origine
- [ ] Un test vérifie qu'après un échec de `rejouer_sur`, `.git/rebase-merge`
      n'existe pas
- [ ] Un test vérifie qu'un conflit sur un fichier de code, lui, est toujours
      annulé et remonté (ADR-033)

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Résoudre automatiquement un conflit sur le fichier ticket ne doit jamais
s'étendre à d'autres fichiers : ADR-033 réserve ces résolutions à un agent,
et toujours sous relecture.
