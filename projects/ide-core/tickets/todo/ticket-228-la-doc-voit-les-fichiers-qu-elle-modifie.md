---
id: ticket-228
title: "Les agents de documentation reçoivent les fichiers qu'ils modifient"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-09-29
---

# ticket-228 — La doc voit les fichiers qu'elle modifie

## Objectif

Les éditions proposées par `doc-technique` et `doc-fonctionnelle` portent sur du texte qui existe vraiment dans `README.md` et `docs/`.

## Contexte

`DocumentationService` n'envoie aux deux agents que les tickets livrés (`_brief`). Les agents n'ont pas d'outils, et ne voient donc jamais la doc qu'ils doivent modifier. Ils inventent alors l'ancien texte ou la section visée. Les trois derniers lots ont tous été rejetés, sur qwen puis sur Haiku : « texte introuvable — ## Pipeline », « section ## Lancer un ticket introuvable », « section ## Configuration introuvable ». `appliquer_editions` fait son travail en refusant ces éditions, mais du coup la doc n'avance jamais.

## Solution proposée

Le message utilisateur contient, après les tickets, le contenu actuel des fichiers documentables (`README.md`, `docs/*.md`), chacun sous son chemin, dans une borne totale (par exemple 60 000 caractères). Au-delà de cette borne, on donne la liste des titres `#` de chaque fichier au lieu de son contenu. Les prompts des deux rôles disent que l'ancien texte doit être recopié mot pour mot depuis ce contenu.

## Critères d'acceptation

- [ ] Un test : le message envoyé au provider contient le texte d'une section de `README.md` du projet
- [ ] Un test : un fichier de `docs/` apparaît sous son chemin relatif
- [ ] Un test : au-delà de la borne, un fichier est remplacé par la liste de ses titres, et le message ne dépasse pas la borne
- [ ] `agents/prompts/doc-technique.md` et `doc-fonctionnelle.md` exigent un ancien texte recopié du contenu fourni

## Dépendances

Aucune.
