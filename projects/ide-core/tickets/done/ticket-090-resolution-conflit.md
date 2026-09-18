---
id: ticket-090
title: "Tenter la résolution d'un conflit, et la faire relire"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-089]
estimated_days: 2
created: 2026-09-18
---

# ticket-090 — Les conflits

## Pourquoi

ticket-083 détectait les conflits, les nommait, annulait proprement. Honnête,
mais ça s'arrêtait là : sur un projet censé aller jusqu'au merge, un conflit
rendait la main pour un travail de cinq minutes.

Le tenter vaut la peine. Le **merger**, non.

## Critères d'acceptation

- [x] Un agent `resolveur-conflit` réécrit les fichiers, avec leur contenu
      marqué déjà dans le prompt — un tour d'outil de moins, une occasion de
      moins de se tromper de fichier
- [x] L'arbre est vérifié **après** : marqueur restant, fichier manquant,
      résolveur qui lève → tout est annulé
- [x] L'arbre ne reste **jamais** à mi-rebase, quel que soit le chemin
- [x] Une résolution qui aboutit ouvre sa PR et **s'arrête là**, même sur un
      projet en `autonomy: merge`
- [x] Le prompt interdit toute commande git : le rebase est en cours et
      l'agent n'en voit qu'une partie
- [x] Le prompt interdit toute amélioration au passage — la modification sera
      relue *comme une résolution de conflit*
- [x] Sans résolveur branché, le comportement d'ADR-030 est inchangé
- [x] ADR-033 écrite

## Ce que ça ne fait pas

Rien ne garantit que la résolution soit **bonne**. C'est précisément pourquoi
elle ne se merge jamais seule : une CI verte dit que le code passe, pas qu'on
a gardé la bonne intention. L'agent doit dire en trois lignes ce qu'il a gardé,
écarté, et ce dont il n'est pas sûr — c'est ce texte qu'on relit.
