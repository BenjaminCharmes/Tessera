---
id: ticket-708
title: "A multi-line proof excerpt matches the diff without its line markers"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-30
---

# ticket-708 — Un extrait de preuve sur plusieurs lignes se retrouve dans le diff, marqueurs de ligne retirés

## Objectif
Un extrait sur plusieurs lignes, recopié du code ajouté par le diff, doit
satisfaire la règle « preuve » de la documentation.

## Contexte
Sur Curio, 37 étapes de documentation sur 54 ont fini à « 0 fichier(s) », après
8 à 15 minutes chacune, tour de correction compris (`projects/curio/memory/pipeline-log.md`,
ticket-061 le 30/10 : l'extrait « export type QuizMode = | "marathon… » est refusé).
Sur ide-core, c'est 126 étapes sur 315.

`_texte_du_code` (`backend/src/tessera/services/documentation_preuve.py`) colle les
diffs bruts. Chaque ligne d'un diff commence par `+`, `-` ou une espace. `aplatir`
fusionne les espaces, mais garde ces marqueurs : un extrait de deux lignes
devient `export type QuizMode = | "marathon"` côté agent, et
`+export type QuizMode = + | "marathon"` côté diff. Il ne se retrouve donc
jamais. Un extrait d'une seule ligne passe, parce que la sous-chaîne commence
après le `+`.

## Solution proposée
Dans `_texte_du_code`, ajouter pour chaque diff le texte de ses lignes `+` et de
contexte, privées de leur premier caractère. Les en-têtes `+++`, `---` et `@@`
sont exclus. Les lignes `-` aussi : ce code n'est plus livré. Le diff brut reste
dans le texte, pour que les extraits d'une ligne qui passent aujourd'hui
continuent de passer.

## Critères d'acceptation
- [ ] `test_multi_line_excerpt_from_added_lines_is_accepted` (dans `backend/tests/test_documentation_preuve.py`) : un extrait de deux lignes recopié de lignes `+` d'un diff, sans les `+`, passe la règle « preuve »
- [ ] `test_excerpt_from_removed_lines_is_refused` : un extrait recopié de lignes `-`, sans les `-`, est refusé
- [ ] `test_single_line_excerpt_still_passes` : un extrait d'une ligne d'un diff passe, comme avant
- [ ] `test_diff_headers_are_not_proof` : un extrait égal à une ligne `+++ b/<chemin>` ou `@@ … @@` est refusé

## Ce que ça ne fait pas
- Ne touche pas la règle « jeton vérifiable » : ses refus sur Curio (« manche 1 / 3 ») viennent d'un texte que ni le code ni les tickets ne portent, et c'est voulu (ADR-057)
- Ne change pas le moment de la documentation (par run approuvé, ticket-198)
