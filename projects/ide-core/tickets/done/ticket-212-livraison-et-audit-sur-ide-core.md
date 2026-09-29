---
id: ticket-212
title: "ide-core livre ses runs approuvés et passe l'audit sécurité sur Claude"
type: chore
status: done
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-28
---

# ticket-212 — Livraison et audit sécurité sur ide-core

## Objectif

Un run approuvé sur `ide-core` pousse sa branche et ouvre sa PR vers
`develop` tout seul, et le code de l'IDE passe par l'audit sécurité avant.

## Contexte

`ide-core` déclare `autonomy: merge`, mais pas de `github_remote`. Les runs
de ce matin ont donc fini sur « GitHub n'est pas configuré pour ce projet »,
avec le travail approuvé resté sur des branches locales. C'est le seul projet
lié à GitHub dans ce cas.

L'audit sécurité est désactivé, et son entrée pointe vers
`qwen3-coder:30b`. Rejoué trois fois sur un diff où Haiku avait trouvé une
traversée de chemin HIGH, qwen a rendu `PASS` à chaque fois.

## Solution proposée

- `agents.json` : `github_remote: BenjaminCharmes/Tessera` ; rôle `securite`
  sur `agent_sdk` / `claude-haiku-4-5`, sans repli ;
  `pipeline.securite_enabled: true`.
- Le validateur reste désactivé jusqu'au ticket-209 : dans son état actuel, il
  présume les critères qu'il ne juge pas. Le testeur reste désactivé, pour la
  raison que donne `projects/ide-core/CLAUDE.md`.
- **Ce ticket autorise la modification de `projects/ide-core/CLAUDE.md`**
  (règle 5), limitée au paragraphe « Ce qui tourne réellement sur ce
  projet », qui deviendrait faux.

Le merge automatique ne se déclenche pas tant que la CI ne peut pas tourner :
`merge` exige une CI verte, et `merge_without_ci` n'est pas déclaré. C'est
voulu.

## Critères d'acceptation

- [x] `GET /api/v1/projects` rend `github_remote` renseigné pour `ide-core`
- [x] Le rôle `securite` d'`ide-core` déclare `provider: agent_sdk` et
      `model: claude-haiku-4-5`
- [x] `pipeline.securite_enabled` vaut `true` ; `validateur_enabled` et
      `testeur_enabled` restent absents
- [x] `projects/ide-core/CLAUDE.md` dit que la sécurité est active, et que le
      validateur attend le ticket-209
- [x] `uv run pytest tests/test_consignes_coherentes.py` passe

## Dépendances

Aucune.
