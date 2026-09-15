---
id: ticket-050
title: "Deux pannes silencieuses : clef API parasite et prompts introuvables"
type: fix
status: done
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-15
---

# ticket-050 — Clef API parasite et chemin des prompts

## Objectif

Corriger deux défauts qui rendaient **toute action d'agent impossible** en
configuration par défaut, sans qu'aucun message ne désigne la cause.

## Contexte

Signalés à l'usage : « Planifier une évolution » tourne, s'arrête, et rien ne
se passe. Les logs révèlent deux causes indépendantes.

### 1. `ANTHROPIC_API_KEY` parasite le mode abonnement

```
ResultError: Claude Code returned an error result:
  Failed to authenticate. API Error: 401 API key is invalid.
⚠ claude.ai connectors are disabled because ANTHROPIC_API_KEY or another
  auth source is set and takes precedence over your claude.ai login
```

Le CLI Claude Code donne la **priorité** à `ANTHROPIC_API_KEY` sur la session
d'abonnement. En mode `agent_sdk` — le défaut — cette clef ne sert à rien, mais
si elle est présente le CLI tente de s'authentifier avec elle et échoue en 401.

Le piège : `.env.example` livre `ANTHROPIC_API_KEY=sk-ant-...`. Ce placeholder,
recopié tel quel dans `.env` comme la documentation le demande, suffit à casser
**tous** les appels agent. Le message d'erreur ne mentionne jamais `.env`.

Ce défaut a échappé aux tests parce qu'un appel de provider lancé à la main
n'hérite pas de `--env-file ../.env` : le provider fonctionne en isolation et
échoue sous le serveur.

### 2. `IDE_PROMPTS_DIR` ne résout jamais

`ide_prompts_dir` valait `Path("agents") / "prompts"`, **relatif au répertoire
de lancement**. Or `make dev` fait `cd backend && uv run uvicorn …`, et
`backend/agents/` n'existe pas.

Conséquence : aucun agent ne trouvait son system prompt, avec la méthode de
lancement documentée. Le code dégradait silencieusement sur un
`WARNING prompt_file_missing` — le registre d'agents, le planificateur,
l'auditeur sécurité, le validateur et le doc-updater tournaient donc tous sans
leurs instructions.

## Solution livrée

1. `_build_options` passe `env={"ANTHROPIC_API_KEY": ""}` au sous-process du
   SDK. La clef reste disponible pour `AnthropicApiProvider`, seul consommateur
   légitime.
2. `ide_prompts_dir` est ancré sur la racine du dépôt, déduite de
   l'emplacement du paquet, et non plus sur le cwd.

## Critères d'acceptation

- [x] Un appel agent réussit avec un `ANTHROPIC_API_KEY` invalide dans `.env`
      et `LLM_PROVIDER=agent_sdk`
- [x] Un test vérifie que `_build_options` neutralise la clef
- [x] `Settings().ide_prompts_dir` est absolu et contient `codeur.md`
- [x] Un test vérifie ce défaut
- [x] `POST /projects/{id}/plan` renvoie des drafts, vérifié en réel
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Dépendances

Aucune.

## Estimation

**1j**.

## Suite possible

Les deux pannes étaient **silencieuses**. Un ticket dédié pourrait faire
échouer bruyamment un prompt d'agent manquant plutôt que de le dégrader en
`WARNING` — un agent sans son system prompt produit du travail hors sujet, ce
qui coûte plus cher qu'un refus net.
