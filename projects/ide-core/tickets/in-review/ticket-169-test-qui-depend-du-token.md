---
id: ticket-169
title: "Un test passe en CI et échoue chez qui a configuré un token"
type: fix
status: in-review
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-25
---

# ticket-169 — Un test qui dépend de l'environnement

## Objectif

Que la suite rende le même verdict quelle que soit la configuration de la
machine qui la lance.

## Contexte

`test_lier_un_remote_apres_init` a commencé à échouer sans qu'une ligne de code
ait bougé. Cause : un `GITHUB_TOKEN` venait d'être renseigné dans `.env`.

`link_git_remote` n'interroge le dépôt distant **que si un token le permet** —
c'est délibéré, et le commentaire du routeur le dit. Le test lie
`https://github.com/moi/repo.git`, qui n'existe pas : sans token il passe,
avec token l'API répond « introuvable » et l'endpoint rend 422.

Le défaut n'est donc pas dans le produit, il est dans le test. Et il est du
genre le plus désagréable : la CI n'a pas de token, donc **elle reste verte**,
pendant que la suite échoue chez celui qui a configuré le sien. Un test qui
dépend de l'environnement ne dit plus rien de ce qu'il teste.

Trois autres tests du même fichier épinglent pourtant `github_token`
explicitement, et simulent `get_repository_info`. Le réflexe existait ; celui-ci
l'a oublié.

## Solution proposée

La fixture `workspace`, déjà chargée d'isoler le workspace, la base et le
fournisseur LLM, épingle aussi `github_token` à vide. Les tests qui veulent un
token le posent après — ils le font déjà.

Corriger le seul test fautif aurait laissé le prochain tomber dans le même
trou.

## Critères d'acceptation

- [ ] La fixture `workspace` neutralise `github_token`
- [ ] `test_lier_un_remote_apres_init` passe avec **et** sans token dans
      l'environnement
- [ ] Les tests qui simulent un token continuent de passer
- [ ] `uv run pytest` passe

## Dépendances

Aucune.

## Estimation

Moins d'une journée.

## Risques

Un test qui aurait besoin du vrai token ne l'aurait plus. Aucun n'en a
besoin : ceux qui en veulent un le simulent, ce qui est la seule façon d'être
reproductible.
