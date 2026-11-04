---
id: ticket-783
title: "Design a measured trial of a second review by a different model"
type: design
status: todo
pr_number: null
priority: low
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-04
---

# ticket-783 — Concevoir l'essai mesuré d'une seconde revue par un autre modèle

## Objectif

Savoir, chiffres à l'appui, si une seconde revue par un modèle différent attrape des défauts
que la revue actuelle laisse passer, et à quel coût.

## Contexte

Idée relevée le 04/11 dans une revue d'outils externes (un outil de la même famille fait relire
le code par un second modèle). Tessera peut l'essayer sans dépendance : chaque rôle déclare son
`provider` et son `model` dans `agents.json`, et tout appel passe par `LLMProvider`
(ADR-017, ADR-046). Aujourd'hui, le reviewer d'ide-core tourne sur `claude-opus-5-5`.

Des cas récents donnent la mesure de ce qu'on cherche : le 03/11, des relecteurs et le
validateur ont approuvé du code qui a dû être corrigé à la main (733 : la résolution de conflit
effaçait une fonctionnalité ; 750 : un faux positif de l'audit sécurité). L'audit du 30/10 a
trouvé quatre contournements de sécurité de gravité haute dans du code déjà approuvé.

## Ce que la conception doit fixer

- Le protocole : rejouer la revue d'un échantillon de runs passés (diffs approuvés puis
  corrigés, et diffs sains) avec un second modèle, sans toucher aux runs en cours.
- Les critères : défauts réels attrapés en plus, faux positifs, coût et durée par revue.
- Le modèle candidat (un autre fournisseur, ou un modèle local via Ollama) et ce qui
  déciderait de l'adopter, de le réserver aux diffs sensibles (gardes de sécurité), ou de
  l'abandonner.
- Où vivent les résultats (un rapport sous `docs/`), et ce qui reste hors du produit tant que
  l'essai n'a pas conclu.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `projects/ide-core/memory/decisions.md` décrit le
      protocole, les critères et la règle de décision
- [ ] Les tickets d'implémentation de l'essai sont créés dans `projects/ide-core/tickets/todo/`,
      chacun tient en moins d'une journée et nomme ses tests
- [ ] Aucun code n'est écrit par ce ticket
