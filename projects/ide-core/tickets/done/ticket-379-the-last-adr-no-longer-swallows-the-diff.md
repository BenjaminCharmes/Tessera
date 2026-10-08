---
agent: codeur
created: 2026-10-07
depends_on: []
estimated_days: 0.5
id: ticket-379
pr_number: null
priority: critical
status: done
title: Filtering decisions by role no longer swallows the diff, the test results and
  the audit that follow them
type: fix
---

# ticket-379 — Le dernier ADR n'avale plus le diff, les tests et l'audit

## Objectif

Que le reviewer voie toujours le diff qu'il relit, quelle que soit la portée
du dernier ADR du projet.

## Contexte

`adr_pertinents` (`backend/src/tessera/services/adr.py`) prend **tout** ce qui
suit le titre `Décisions récentes` du contexte comme le fichier de décisions,
puis `adr_pour` le découpe avec `decouper`, qui fait courir le dernier ADR
jusqu'à la fin du texte. Les sections ajoutées au contexte après les
décisions — le diff à relire, les résultats du testeur, l'audit sécurité —
font donc partie du dernier ADR. Quand la portée de cet ADR (ligne
`**Portée** : …`) n'inclut pas le reviewer, elles sont retirées avec lui : le
reviewer relit sans voir aucun diff.

Signalé le 2026-10-07 par la session qui pilote affut. Projets exposés ce
jour-là : demineur, portfolio, carriere, freelance (leur dernier ADR a une
portée qui exclut le reviewer). Affut l'était jusqu'à son ADR-011, sans portée.

Le format `contraintes.md` (`contraintes_pour`) n'est pas concerné : ses blocs
s'arrêtent au titre de niveau 2 suivant.

## Solution proposée

Borner la section des décisions : elle s'arrête au premier titre de niveau 2
qui n'est pas un titre d'ADR (`## ADR-NNN`). Seule cette portion est filtrée
par rôle ; ce qui la suit est rendu intact, à sa place.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_adr_pertinents.py` construit un contexte avec une section `Décisions récentes` dont le dernier ADR a la portée `codeur`, suivie d'une section de diff, et vérifie que `adr_pertinents(contexte, "reviewer")` contient le diff
- [ ] Le même test vérifie que cet ADR de portée `codeur` est absent du résultat pour le reviewer et présent pour le codeur
- [ ] Un test de `backend/tests/test_adr_pertinents.py` vérifie que les résultats du testeur et l'audit placés après les décisions sont rendus intacts, dans le même ordre
- [ ] Un test de `backend/tests/test_adr_pertinents.py` vérifie qu'un contexte au format `contraintes.md` donne le même résultat qu'avant
- [ ] Les tests existants de `backend/tests/test_adr_pertinents.py` passent sans modification

## Dépendances

Aucune.

## Estimation

0,5 jour.

## Risques

Un ADR qui contiendrait lui-même un titre de niveau 2 non-ADR serait coupé à
ce titre : le format de `decisions.md` n'utilise que des titres `## ADR-NNN`
et des sous-titres de niveau 3.

## Ce que ça ne fait pas

- Ne change pas la règle de portée elle-même (un ADR sans portée va à tous).