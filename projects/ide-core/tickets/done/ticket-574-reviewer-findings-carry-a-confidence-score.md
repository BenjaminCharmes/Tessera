---
agent: codeur
created: 2026-10-24
depends_on: []
estimated_days: 0.5
id: ticket-574
plan: true
pr_number: 699
priority: medium
status: done
title: Reviewer findings carry a confidence score and only confident ones block
type: feat
---

# ticket-574 — Un score de confiance sur chaque remarque du reviewer

## Objectif
Moins de tours `CHANGES_REQUESTED` déclenchés par des remarques incertaines,
sans laisser passer un vrai problème.

## Contexte
Veille du 24/10 : le plugin officiel `code-review` d'Anthropic note chaque
problème de 0 à 100 et écarte ceux sous un seuil (80 par défaut).
`agents/prompts/reviewer.md` n'a aucune notion de confiance, et
`_parse_reviewer_verdict` (`services/pipeline_text.py`) ne lit qu'un verdict
global. Le 24/10, l'audit de sécurité a aussi bloqué un ticket de Vigie sur
une affirmation fausse (« `IN ()` est une erreur SQL ») : une remarque
incertaine présentée comme sûre.

## Solution proposée
Le prompt du reviewer demande, pour chaque remarque bloquante, un score de
confiance de 0 à 100. Une remarque sous le seuil (réglable, 80 par défaut)
est listée pour information mais ne justifie pas `CHANGES_REQUESTED` à elle
seule. Le tour de plan dit comment le score se lit dans la réponse, sans
casser le parsing par mot-clé (ADR-009).

## Critères d'acceptation
- [ ] `agents/prompts/reviewer.md` demande un score de confiance de 0 à 100 pour chaque remarque bloquante et dit qu'une remarque sous le seuil ne bloque pas
- [ ] Un test montre qu'une réponse `CHANGES_REQUESTED` dont toutes les remarques sont sous le seuil est lue comme une approbation avec remarques
- [ ] Un test montre qu'une remarque au-dessus du seuil garde `CHANGES_REQUESTED`
- [ ] Un test montre qu'une réponse sans score garde le comportement actuel de `_parse_reviewer_verdict`
- [ ] Le seuil est un réglage avec 80 pour défaut, et un test le vérifie

## Ce que ça ne fait pas
- Ne touche pas à l'audit de sécurité : une faille `CRITICAL` ou `HIGH` bloque toujours (ADR-039).