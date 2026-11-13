---
agent: codeur
created: 2026-11-13
depends_on: []
estimated_days: 0.5
id: ticket-962
pr_number: null
priority: medium
status: todo
title: "Each documentation role reads the documentation as it is when it is called"
type: fix
---

# ticket-962 — Chaque rôle de documentation lit la documentation telle qu'elle est à son appel

## Objectif

Que doc-fonctionnelle ne propose plus d'éditions sur un texte que
doc-technique vient de remplacer dans le même lot.

## Contexte

Relecture des lots de documentation du 11 au 13/11 : RepoHealth 018, 020,
025, 050 et 054 ont fini en « texte introuvable » côté doc-fonctionnelle sur
`docs/guide-utilisateur.md`, après que doc-technique avait déjà écrit dans ce
fichier dans le même lot.

Dans `services/documentation/documentation.py`, `contenu_doc` et `brief`
sont calculés **une fois**, avant la boucle `for role in self._roles`
(lignes 191-192). doc-technique passe en premier et écrit sur le disque ;
doc-fonctionnelle reçoit ensuite le contenu d'**avant** ces écritures. Son
tour de correction (ticket-395) part de `user`, le même brief périmé, et
retombe sur le même texte absent.

## Solution proposée

1. Dans la boucle des rôles, recalculer `contenu_doc` et le brief depuis le
   disque juste avant l'appel de chaque rôle.
2. Le tour de correction part du brief de ce rôle, recalculé lui aussi
   depuis le disque.
3. `reduits` (fichiers tronqués, ticket-954) reste celui du premier calcul :
   ce qu'on journalise est le budget du lot, pas celui de chaque rôle.
4. Après chaque `appliquer_editions` réussi, journaliser
   `editions_appliquees` (rôle, fichiers modifiés) : aujourd'hui seul le
   second refus laisse une trace.

## Critères d'acceptation

- [ ] Un test avec deux providers simulés : doc-technique remplace un
      paragraphe de `docs/guide-utilisateur.md` ; le prompt reçu par
      doc-fonctionnelle contient le nouveau paragraphe et plus l'ancien ;
      une édition de doc-fonctionnelle qui vise le nouveau paragraphe
      s'applique.
- [ ] Un test : quand la première édition de doc-fonctionnelle est refusée,
      le prompt de son tour de correction contient le contenu du disque au
      moment de ce tour (le paragraphe écrit par doc-technique).
- [ ] Un test : `editions_appliquees` est journalisé avec le rôle et les
      fichiers modifiés après une édition acceptée.
- [ ] Les tests existants de `services/documentation` passent sans
      changement de leurs attentes.

## Ce que ça ne fait pas

- Ne change pas l'ordre des rôles ni les règles de contrôle (ADR-057).
- Ne traite pas les extraits de preuve joints sans espace (RepoHealth 045) :
  un seul cas, à voir s'il revient.
