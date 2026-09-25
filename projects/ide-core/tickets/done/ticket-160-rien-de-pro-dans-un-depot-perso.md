---
id: ticket-160
title: "Rien de professionnel n'entre dans un dépôt personnel"
type: docs
status: done
pr_number: 2
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-23
---

# ticket-160 — Rien de professionnel n'entre dans un dépôt personnel

## Objectif

Qu'aucun agent, et aucune session, n'écrive de donnée professionnelle dans un
dépôt personnel — ni dans le contenu des fichiers, ni dans les métadonnées git.

## Contexte

Le 2026-09-23, le service cybersécurité d'un client a signalé le dépôt
`Tessera`, alors public. Cause : le `.gitconfig` global portait l'adresse
e-mail professionnelle, qui s'est retrouvée auteur et committer de 162 commits,
plus 91 trailers `Co-authored-by` produits par les squash-merges GitHub.

Le **contenu** était propre : ticket-103 avait déjà remplacé les noms de
clients et le hostname d'infrastructure interne par des valeurs neutres. Le
défaut était ailleurs, et c'est ce qui le rend intéressant : ticket-103 a
vérifié ce qu'on lit dans les fichiers, personne n'a vérifié ce que git écrit
tout seul à côté. Un `user.email` global s'applique à tous les dépôts d'une
machine sans jamais se rappeler à l'attention.

La réparation a coûté la réécriture complète de l'histoire des trois dépôts
touchés, leur suppression et leur recréation sur GitHub — donc la perte des PR
et de leurs discussions. Rien de tout cela n'aurait été nécessaire si la règle
avait existé.

Aucune règle du dépôt ne couvrait le cas. `CLAUDE.md` interdit de laisser une
trace d'écriture par IA (règle 8) ; rien n'interdit de laisser une trace
d'employeur.

## Solution proposée

1. Écrire l'ADR-043 dans `projects/ide-core/memory/decisions.md` : interdiction
   portant sur le contenu **et** les métadonnées git, et l'identité git déclarée
   par dossier plutôt que globalement. Sans `**Portée**` — c'est une contrainte
   de comportement, elle doit partir à tous les agents (ADR-032).
2. L'inscrire dans `_CONTRAINTES` de `backend/tests/test_adr_pertinents.py`,
   pour qu'une portée posée dessus par mégarde fasse échouer les tests.
3. Ne **pas** dupliquer la règle dans `CLAUDE.md` : ADR-034 veut une règle
   décrite à un seul endroit, et `decisions.md` est `@`-importé par le
   `CLAUDE.md` racine comme injecté dans chaque appel d'agent. Ce ticket
   n'autorise donc aucune modification de `CLAUDE.md` (règle 5).

## Critères d'acceptation

- [ ] `memory/decisions.md` contient un `## ADR-043 —` portant ses lignes
      `**Date**` et `**Décision**`
- [ ] ADR-043 ne porte pas de ligne `**Portée**`
- [ ] ADR-043 nomme explicitement les métadonnées git (auteur, committer,
      trailers) et pas seulement le contenu des fichiers
- [ ] `"ADR-043"` figure dans `_CONTRAINTES` de `test_adr_pertinents.py`
- [ ] `uv run pytest backend/tests/test_adr_pertinents.py
      backend/tests/test_consignes_coherentes.py` passe — ce dernier vérifie
      le budget de 160 mots
- [ ] `CLAUDE.md` est inchangé

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Un ADR de plus sans portée part dans les 18 appels d'agent d'un ticket. C'est
le prix d'une contrainte : un agent qui ne l'a pas lue ne la respecte pas
(ADR-032). Le budget de 160 mots borne la dépense.
