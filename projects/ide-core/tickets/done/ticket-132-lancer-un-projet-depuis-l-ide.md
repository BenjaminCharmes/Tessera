---
id: ticket-132
title: "Lancer un projet depuis l'IDE : back, front et base quand il en faut"
type: design
status: done
pr_number: 154
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-132 — Lancer un projet depuis l'IDE

## Objectif

Cadrer un bouton qui démarre un projet — backend, frontend, base de données —
à partir de ce que ses fichiers de contexte décrivent déjà.

## Contexte

Chaque `CLAUDE.md` de projet porte sa section de lancement : `ide-core` liste
`make dev`, `make dev-frontend`, `make tauri-dev`. L'information existe, elle
n'est jamais exécutée.

Mais un bouton qui lance des processus longs bute sur trois choses que le
produit a déjà tranchées dans l'autre sens :

- **ADR-027** — un hook refuse aux agents le git et le `gh` qui écrivent. Une
  commande de lancement n'est pas du git, mais la question « qu'a-t-on le
  droit de lancer » n'a jamais été posée pour autre chose ;
- **ADR-031** — un agent n'écrit que sous la racine de son projet, et le
  contrôle sur `Bash` « attrape une erreur, pas une évasion ». Un serveur
  lancé par un agent écrit des logs, des caches, parfois une base ;
- **ADR-038** — un verrou refuse deux runs sur un projet. Un serveur qui
  tourne n'est pas un run : faut-il un second verrou, ou le même ?

Et surtout : le pipeline est fait de processus **courts qui rendent la main**.
Un serveur ne rend jamais la main.

## Solution proposée

Le ticket est de type `design` : il produit une décision, pas du code.

Questions à trancher, dans l'ordre :

1. Qui lance — un agent avec `Bash`, ou le backend lui-même à partir d'une
   commande déclarée dans `agents.json` ? La seconde est plus sûre et moins
   souple ; la première est l'inverse.
2. Où vit le processus : enfant du backend, tué à l'arrêt, ou détaché ?
3. Comment on l'observe — le canal de ticket-128 transporte-t-il aussi la
   sortie d'un serveur, ou est-ce un autre flux ?
4. Comment on l'arrête, y compris après un redémarrage du backend qui a perdu
   la référence du processus.
5. Quel projet a le droit de se lancer : un champ de `agents.json`, sur le
   modèle d'ADR-029 — le défaut protège, l'autorisation se déclare.

## Critères d'acceptation

- [ ] Un ADR est rédigé, dans le budget du skill `write-adr`, et tranche les
      cinq questions ci-dessus
- [ ] L'ADR dit explicitement si un projet doit déclarer quoi que ce soit dans
      `agents.json` pour être lançable, et quel est le défaut
- [ ] L'ADR dit ce qui se passe quand le backend s'arrête alors qu'un projet
      tourne
- [ ] Un ou plusieurs tickets d'implémentation sont créés à partir de l'ADR
- [ ] Aucune ligne de code de lancement n'est écrite dans ce ticket

## Dépendances

Aucune, mais la question 3 se tranche mieux après ticket-128.

## Estimation

1 jour.

## Risques

C'est le ticket qui ouvre le plus de surface : un processus lancé par l'IDE
survit à l'IDE, écoute un port, et peut écrire n'importe où. Le décider
d'abord, l'écrire ensuite.
