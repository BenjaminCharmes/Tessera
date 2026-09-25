---
id: ticket-152
title: "L'IDE ne peut pas se lancer lui-même, et doit le dire"
type: feat
status: done
pr_number: 172
priority: medium
agent: codeur
depends_on: ["ticket-151"]
estimated_days: 1
created: 2026-09-23
---

# ticket-152 — Le projet qui fait tourner l'IDE

## Objectif

Que le projet bootstrap cesse de proposer un bouton qui ne peut rien produire
d'utile, et dise ce qu'il est.

## Contexte

**Relevé en usage.** `ide-core` affiche « Lancer », et cliquer démarre un
**second** backend — qui meurt aussitôt, le port 8000 étant pris par celui qui
fait tourner l'IDE — et un **second** frontend sur un autre port.

Le cas où ce bouton servirait n'existe pas : il faut que l'IDE tourne pour
qu'on voie l'écran, donc `ide-core` est toujours déjà lancé quand le bouton
s'affiche. Il produit systématiquement un doublon inutile.

C'est le projet bootstrap d'ADR-001 qui se mord la queue : il construit
l'IDE, et l'IDE voudrait le lancer alors qu'il est en train de l'exécuter.

## Solution proposée

**Reconnaître le projet qui fait tourner l'IDE.** Le backend connaît sa propre
racine ; un projet dont la racine autorisée (ADR-028) est celle du dépôt de
Tessera est ce projet-là. La comparaison porte sur des chemins résolus, comme
pour le périmètre d'écriture.

Pour lui, le panneau remplace le bouton par ce qu'il est : « ce projet fait
tourner l'IDE que tu utilises », avec les adresses sur lesquelles il répond —
que le backend connaît, puisqu'il les sert.

## Ce qui est écarté, et pourquoi

**Afficher les logs de l'IDE lui-même.** Sa sortie ne passe pas par un tube
que le backend contrôle : elle va dans le terminal qui l'a lancé. La lire
demanderait de l'écrire dans un fichier, donc de changer la façon dont l'IDE
démarre — c'est un autre sujet, à ouvrir s'il se confirme.

**Arrêter l'IDE depuis l'IDE.** Techniquement faisable, mais un bouton qui
coupe la branche sur laquelle on est assis demande une confirmation, un état
« en cours d'extinction » et une page qui survit à son propre serveur. Le
rapport entre le coût et le service rendu ne le justifie pas : fermer le
terminal suffit.

## Critères d'acceptation

- [ ] Un test vérifie qu'un projet dont la racine est celle de Tessera est
      reconnu comme le projet qui fait tourner l'IDE
- [ ] Un test vérifie qu'un projet ordinaire ne l'est pas, y compris un
      projet déclarant `git_root: ancestor` dans un autre dépôt
- [ ] Un test vérifie qu'aucun bouton « Lancer » ne s'affiche pour ce projet
- [ ] Un test vérifie que le panneau dit ce qu'il est, et donne les adresses
- [ ] `uv run pytest`, `uv run mypy src/`, `npm run typecheck`,
      `npm run lint`, `npm run test` et `npm run build` passent

## Dépendances

ticket-151.

## Estimation

1 jour.

## Risques

La reconnaissance repose sur une comparaison de chemins : un projet importé
par lien symbolique vers le dépôt de Tessera serait reconnu à tort. Les deux
côtés doivent être résolus, comme le fait déjà `hors_perimetre`.
