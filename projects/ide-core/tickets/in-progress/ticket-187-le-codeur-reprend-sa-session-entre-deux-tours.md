---
id: ticket-187
title: "Le codeur reprend sa session entre deux tours de revue"
type: feat
status: in-progress
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-26
---

# ticket-187 — Le codeur reprend sa session entre deux tours de revue

## Objectif

Qu'un codeur renvoyé par le reviewer reparte de ce qu'il sait déjà, au lieu
de redécouvrir le dépôt depuis une session vide.

## Contexte

Chaque appel d'agent est un `query()` neuf dans
`services/providers/agent_sdk.py`. Au tour 2, le codeur reçoit le contexte
projet, le ticket et le retour du reviewer — mais ni sa session, ni son
propre diff. Il relit donc le dépôt : sur les runs mesurés en base, un appel
codeur relit en moyenne 227 k tokens depuis le cache (jusqu'à 742 k), pour
9,6 k tokens produits, et dure 160 s. Sur un run type, 73 lectures et 13
`Glob` précèdent 10 éditions. Sur tous les runs, `CLAUDE.md` a été relu 34
fois, `package.json` 33 fois.

Le SDK installé (0.2.152) sait reprendre une conversation :
`ClaudeAgentOptions.resume` prend un identifiant de session, et
`ResultMessage.session_id` le rend à la fin d'un appel. Rien dans le code ne
s'en sert.

## Solution proposée

- `ProviderResult` gagne un champ `session_id: str | None`. Le provider SDK
  le remplit depuis le `ResultMessage` ; les autres providers le laissent à
  `None`.
- `LLMProvider.complete` et `.stream` acceptent un argument keyword-only
  `session: str | None = None`. Le provider SDK le passe dans `resume` ;
  `AnthropicApiProvider` l'ignore.
- `AgentRunner.run` transmet `session` et rend `session_id` dans
  `AgentResult`.
- Dans `pipeline_stages.py`, l'état du run garde la session du codeur du tour
  précédent. Au tour N > 1, le codeur est appelé avec cette session, et son
  prompt utilisateur ne contient **que** le retour du reviewer et la
  consigne de corriger : le contexte projet, le ticket et le system prompt
  sont déjà dans la conversation reprise.
- La session ne survit pas au run : un autre ticket, une autre branche,
  repart à vide. Le reviewer, lui, garde une session neuve à chaque tour —
  un regard frais est ce qu'on lui demande.
- Si la reprise échoue (session introuvable, SDK qui lève), on retombe sur
  l'appel complet d'aujourd'hui, et un log `session_resume_failed` le dit.

## Critères d'acceptation

- [ ] `ProviderResult.session_id` est renseigné par `ClaudeAgentSDKProvider`
      et vaut `None` pour `AnthropicApiProvider` — un test par provider
- [ ] Un test de `pipeline_stages` vérifie qu'au tour 2 le provider est
      appelé avec `session` égal au `session_id` rendu au tour 1
- [ ] Un test vérifie que le prompt utilisateur du tour 2 ne contient pas le
      corps du ticket ni la section « Décisions récentes »
- [ ] Un test vérifie qu'un nouveau run part avec `session=None`
- [ ] Un test vérifie le repli sur appel complet quand `resume` lève
- [ ] Les doubles de provider des tests existants acceptent l'argument
      `session` sans casser (`uv run pytest` vert)
- [ ] `uv run mypy src/` passe

## Ce que ça ne fait pas

Le contexte du tour 1 n'est pas réduit : c'est le ticket-190. La session
n'est pas partagée entre tickets d'une même file, ni persistée en base.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Le SDK stocke les sessions sur disque sous le profil utilisateur et les
retrouve par `cwd` : si le `cwd` diffère entre les deux tours, la reprise
échoue — d'où le repli. Une session reprise conserve aussi les lectures
d'outils, donc le contexte du tour 2 est plus long que celui d'un appel
neuf : c'est le prix d'une redécouverte évitée, à mesurer sur `cache_read`.
