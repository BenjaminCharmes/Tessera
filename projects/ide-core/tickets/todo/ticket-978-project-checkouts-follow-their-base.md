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

## Contexte

Depuis que les runs partent d'`origin/<base>` (ticket-923), le checkout d'un
projet n'avance que dans un cas : après un merge par `CIWatcher`, pour un
projet **sans** worktree (`realigner_base`, ticket-422, appelé par
`CIWatcher._realigner_si_libre`). Deux trous restent, relus dans le code le
20/11 :

- `surveillance_run.py` ne donne aucun `Realignement` à `CIWatcher` quand le
  run a un worktree (`realignement = None if wt is not None`). Le checkout d'un
  projet à worktree ne suit donc jamais sa base : le 16/11,
  `projects/kadoomi/package.json` portait next 16.3.8 alors qu'`origin/develop`
  était en 16.4.6, et le radar de Vigie en a tiré une fausse version installée ;
  le 20/11, le checkout de Serpent avait sept commits de retard.
- `lancer_les_services` (`routers/services.py`) lit `agents.json` dans le
  checkout sans l'avancer. Affût et Vigie ont dû faire un `merge --ff-only` à
  la main pour que leur correctif de port soit lu.

## Ce qu'il faut faire

Réutiliser `realigner_base` (`services/livraison/realignement_base.py`), qui
refuse déjà tout arbre qui n'est pas sur la base ou qui porte une modification
hors du journal, ne lève jamais et journalise `realignement_ignore` avec sa
raison. Ne pas écrire un second service.

- `surveillance_run.py` : un run à worktree donne lui aussi un `Realignement`
  sur le checkout du projet (`project_path`), pas sur le worktree.
- `CIWatcher._realigner_si_libre` : le refus « un run occupe le projet » ne
  vaut que pour un projet sans worktree ; le checkout d'un projet à worktree
  n'est pas l'arbre de travail des runs.
- `lancer_les_services` : avant `load_services_config`, appeler
  `realigner_base` sur la racine du projet et sa branche de base, sauf si un
  run occupe un projet sans worktree. Un refus ne bloque rien : les services
  démarrent sur l'arbre tel quel.

## Critères d'acceptation

- [ ] Test : `surveillance_run` passe à `CIWatcher` un `Realignement` dont la
      racine est le checkout du projet quand le run a un worktree.
- [ ] Test : après un merge, `_realigner_si_libre` appelle `realigner_base`
      pour un projet à worktree même si un run l'occupe, et ne l'appelle pas
      pour un projet sans worktree occupé.
- [ ] Test : `lancer_les_services` lit l'`agents.json` du commit avancé (dépôt
      de test en retard d'un commit sur `origin/<base>`, arbre propre).
- [ ] Test : `lancer_les_services` démarre les services quand `realigner_base`
      refuse (arbre sur une autre branche).
- [ ] Aucun nouveau module qui lance `git merge` ou `git pull` : le diff
      n'ajoute aucun appel à ces commandes hors de `realignement_base.py`.

## Ce que ça ne fait pas

- Ne fait jamais de merge non fast-forward, de rebase, de reset ni de checkout
  de branche.
- Ne réaligne pas un checkout resté sur une autre branche que la base, ni un
  arbre modifié.
- N'ajoute aucune tâche périodique : le checkout n'avance qu'après un merge et
  au lancement des services.
