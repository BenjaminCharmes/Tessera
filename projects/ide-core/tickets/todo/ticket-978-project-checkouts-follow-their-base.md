---
agent: codeur
created: '2026-11-16'
depends_on: []
id: ticket-978
priority: medium
status: todo
title: Les checkouts de projet suivent leur base
type: feat
---

## Signalement

- Projets sources : vigie (signalement API du 16/11) et affut (idée du même
  jour, même cause)
- Nature : idée
- **À lancer après la clôture de la stabilisation** (aucune fonctionnalité
  nouvelle d'ici là)

## Contexte

Depuis que les runs partent d'`origin/<base>` (ticket-923), rien n'avance le
checkout d'un projet sans worktree, et les sessions ont pour consigne de ne
pas y lancer git. Tout ce qui lit le checkout voit des fichiers périmés :

- Le 16/11, `projects/kadoomi/package.json` porte next 16.3.8 alors
  qu'`origin/develop` est en 16.4.6. Le radar de Vigie en a tiré une fausse
  version installée.
- `POST /services/start` lit `agents.json` dans le checkout. Affût et Vigie
  ont dû faire un `merge --ff-only` à la main, sur exception, pour que leur
  correctif de port soit lu.
- Le ticket-977 traite le cas du texte d'un ticket lu en retard ; celui-ci
  traite le reste du checkout.

## Ce qu'il faut faire

Un service avance le checkout d'un projet en `merge --ff-only` sur
`origin/<base>` quand **toutes** ces conditions tiennent : le projet ne
déclare pas `worktree` ; aucun run n'est ouvert sur lui (`RunLock`) ; la
branche courante est la base ; l'arbre est propre (`git status --porcelain`
vide). Sinon, il ne fait rien et journalise la raison.

Il est appelé à deux moments : après le merge d'une PR du projet par
`CIWatcher`, et au début de `lancer_les_services`, avant la lecture
d'`agents.json`.

## Critères d'acceptation

- [ ] Test : dépôt de test en retard d'un commit sur `origin/<base>`, arbre
      propre, sur la base, sans run : le checkout est avancé.
- [ ] Tests : run ouvert, arbre sale, branche autre que la base, projet à
      worktree → le checkout ne bouge pas, la raison est journalisée.
- [ ] Test : `lancer_les_services` lit l'`agents.json` du commit avancé.
- [ ] Test : un merge par `CIWatcher` déclenche l'avance.
- [ ] Une avance refusée par git (non fast-forward) ne lève pas : elle se
      journalise, et les services démarrent sur l'arbre tel quel.

## Ce que ça ne fait pas

- Ne fait jamais de merge, de rebase, de reset ni de checkout de branche.
- Ne touche pas aux projets à worktree, dont le checkout n'est pas l'arbre
  de travail des runs.
