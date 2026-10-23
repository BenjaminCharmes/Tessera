---
id: ticket-547
title: "A push is refused when the added lines carry a recognisable secret"
type: feat
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-23
---

# ticket-547 — Contrôle déterministe des secrets avant le push

## Objectif
Qu'un jeton ou une clé reconnaissable dans le diff ajouté arrête le push,
sans dépendre d'un modèle.

## Contexte
Avant un push, `services/termes_interdits.py` (ADR-048) cherche des termes
listés dans `.env`, et l'audit de sécurité est un appel LLM qui peut se
tromper. Rien ne reconnaît la forme d'un secret. KrumIA (revue du 23/10)
contrôle le diff par expressions régulières : clés AWS, jetons GitHub et
GitLab, clés Anthropic, clés privées, identifiants dans une URL.

## Solution proposée
Un service `services/secrets_diff.py`, appelé au même endroit que
`TermesInterditsService` dans `GitHubWorkflowService.open_pull_request()`.
Motifs : `AKIA[0-9A-Z]{16}`, `gh[pousr]_[A-Za-z0-9]{36,}`, `github_pat_`,
`glpat-`, `sk-ant-[A-Za-z0-9_-]{20,}`, `sk_live_`, `-----BEGIN … PRIVATE
KEY-----`, `://user:password@`, et l'ajout d'un fichier `.env`, `*.pem` ou
`id_rsa`. Seules les lignes ajoutées comptent. Comme pour les termes
interdits, la sortie nomme le fichier et la ligne, jamais la valeur.
Le placeholder `sk-ant-...` (`doctor.py`) ne déclenche rien.

## Critères d'acceptation
- [ ] `backend/src/tessera/services/secrets_diff.py` expose une fonction qui prend un diff et rend la liste des violations (fichier, ligne, type de secret)
- [ ] Un test par motif listé ci-dessus montre une ligne ajoutée détectée, et la même ligne en suppression ignorée
- [ ] Un test montre que `sk-ant-...` et une chaîne `AKIA` trop courte ne sont pas détectés
- [ ] Un test montre que le message de violation ne contient pas la valeur du secret
- [ ] `open_pull_request()` refuse le push quand une violation existe, et un test le vérifie avec des doubles
- [ ] `PolitiqueRun.confidentialite == "professional"` ne court-circuite pas ce contrôle, et un test le vérifie

## Ce que ça ne fait pas
- Ne touche ni au hook `pre-push` ni à la CI (les deux autres portes de
  l'ADR-050) : à décider après usage.
