---
agent: codeur
created: 2026-10-22
depends_on: []
estimated_days: 0.5
id: ticket-534
pr_number: null
priority: high
status: done
title: A documentation role declared inactive is not called
type: fix
---

# ticket-534 — Un rôle de documentation inactif n'est pas appelé

## Objectif
Qu'un projet puisse couper la documentation par lot, rôle par rôle, depuis
`agents.json`.

## Contexte
Signalé par Kadoomi le 22/10 (run b00d8d8a, ticket-101). Kadoomi avait mis
`doc-technique` à `"active": false` (kadoomi#119) parce que la doc générée
inventait des détails ; le run suivant a quand même écrit la doc.
`services/documentation.py` boucle sur `_ROLES = ("doc-technique",
"doc-fonctionnelle")` sans lire le registre du projet : les deux rôles
tournent toujours, `doc-fonctionnelle` même quand le projet ne le déclare pas
(provider et modèle par défaut). Aucun réglage ne coupe la doc.

## Solution proposée
`DocumentationService.mettre_a_jour` n'appelle que les rôles de `_ROLES` que
le projet déclare **et** marque actifs dans `agents.json`. Aucun rôle actif :
aucun appel LLM, le marqueur `memory/documentation.json` n'avance pas, et le
résultat le dit (aucun fichier modifié). Le filtre se décide dans
`routers/orchestrator.py` (`_documenteur`), qui lit déjà la configuration du
projet sur son dossier réel.

## Critères d'acceptation
- [ ] Un test vérifie, avec un double de fournisseur LLM, qu'un rôle de documentation déclaré `"active": false` n'est pas appelé
- [ ] Un test vérifie qu'un rôle de documentation absent d'`agents.json` n'est pas appelé
- [ ] Un test vérifie que, sans aucun rôle de documentation actif, aucun fichier n'est écrit et `memory/documentation.json` n'est pas modifié
- [ ] Un test vérifie que deux rôles déclarés actifs sont appelés tous les deux, comme aujourd'hui

## Ce que ça ne fait pas
- Ne touche pas à la qualité de la doc produite (ticket-535).
- Ne change pas les `agents.json` des projets : un projet qui veut garder
  `doc-fonctionnelle` doit le déclarer.

## Risques
Les projets qui comptaient sur `doc-fonctionnelle` sans le déclarer perdent
le guide utilisateur. Vérifier avant le merge quels `agents.json` le
déclarent, et le dire dans la PR.