---
id: ticket-079
title: "Ce que le dépôt livre ne se supprime pas, et se dit d'un seul mot"
type: fix
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-078]
estimated_days: 1
created: 2026-09-17
---

# ticket-079 — Agents livrés, et vocabulaire unique

## La distinction « built-in / custom » était fausse

Question posée à l'usage : « quelle est la différence, à part que je ne peux
supprimer que les custom ? » La réponse est qu'il n'y en avait pas d'autre — et
que le classement lui-même était faux.

`BUILTIN_ROLES` était une liste écrite à la main, restée à **six** rôles alors
que le dépôt en livre **treize**. Sept agents du produit passaient donc pour des
créations de l'utilisateur, et se supprimaient d'un clic :

`agent-creator`, `chat`, `doc-updater`, `planificateur`, `securite`, `testeur`,
`validateur`

Ce n'est pas théorique : `agent-creator` a été supprimé par erreur le
2026-09-17, et n'a été récupérable que parce qu'il est versionné.

La liste couvre désormais tout ce que le dépôt livre, et **un test refuse tout
prompt livré qui n'y figurerait pas** : ajouter un agent au dépôt sans le
déclarer fait échouer la suite. Une liste écrite à la main sans rien pour la
vérifier dérive — c'est ce qui vient de se passer.

## Conséquence sur la création automatique

Un rôle natif n'est jamais fabriqué à la volée, même si son prompt n'est pas
encore sur le disque : il est livré avec le dépôt, et en générer un l'écraserait
par un texte inventé. `planificateur` rejoint donc les rôles qui ne se
bootstrappent pas.

## Un mot par chose

Le badge existait en deux exemplaires : `built-in` / `custom`, en anglais et
colorés dans la liste ; `natif` / `personnalisé`, en français et sans couleur
dans l'en-tête. Le même fait, dit de deux façons, à deux endroits visibles en
même temps.

Un composant unique, en français, coloré, avec une infobulle qui dit ce que la
distinction **change** : un natif s'ajuste mais ne se supprime pas ; un agent
perso fait les deux.

## Vérifié

918 tests backend, mypy sur 65 fichiers, 369 tests frontend, 5 flows E2E,
`npm run build`.
