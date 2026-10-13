---
agent: codeur
created: 2026-10-13
depends_on: []
estimated_days: 0.5
id: ticket-414
pr_number: 403
priority: high
status: done
title: Agents working on a hosted project no longer inherit Tessera's own CLAUDE.md
  rules
type: fix
---

# ticket-414 — Les agents d'un projet n'héritent plus du CLAUDE.md de Tessera

## Objectif

Qu'un agent travaillant sur un projet rangé sous `projects/` ne lise que les
consignes de ce projet, pas celles de Tessera.

## Contexte

Le 2026-10-13, l'audit sécurité a bloqué le ticket-005 de `curio` (HIGH) :
« le code ajoute des appels API sans gérer l'authentification Bearer requise
par la politique de sécurité du projet (STATIC_TOKEN) ». `STATIC_TOKEN` est
l'authentification de l'API **de Tessera**, décrite dans le `CLAUDE.md`
racine du dépôt Tessera ; Curio n'a pas d'authentification (son ADR-004).
Même blocage le 2026-10-05 sur `homelab-monitor`.

Cause : `services/providers/agent_sdk.py` construit `ClaudeAgentOptions`
avec `cwd` = dossier du projet et `setting_sources=["project"]`. Claude
Code remonte alors l'arborescence et charge chaque `CLAUDE.md` ancêtre :
`tessera/CLAUDE.md` (et ses `@`-imports : `projects/ide-core/CLAUDE.md`,
`contraintes.md`) entre dans le contexte de **tous** les projets hébergés.
Contournement posé sur curio : une phrase dans son `CLAUDE.md`.

Le CLI embarqué (SDK 0.2.159) connaît le réglage `claudeMdExcludes` (liste
de chemins ou motifs de `CLAUDE.md` à ignorer), qui se passe par le
paramètre `settings` de `ClaudeAgentOptions`.

## Solution proposée

- Dans `agent_sdk.py`, quand `cwd` est un dossier situé **sous** la racine
  du dépôt Tessera (`_REPO_ROOT`) mais n'est pas un projet `git_root:
  ancestor` (ide-core, qui a besoin de ces consignes) : passer
  `settings` avec `claudeMdExcludes` listant le `CLAUDE.md` et le
  `CLAUDE.local.md` de chaque dossier ancêtre du projet jusqu'à
  `_REPO_ROOT` inclus.
- Isoler ce calcul dans une fonction pure testable
  (`claude_md_ancetres_a_exclure(cwd, racine, ancestor: bool) -> list[str]`).
- Vérifier sur un vrai appel (manuellement, consigné dans la PR) qu'un agent
  lancé sur un projet hébergé ne voit plus `STATIC_TOKEN` dans son contexte.

## Critères d'acceptation

- [ ] Un test vérifie que, pour un projet `racine/projects/p`, la fonction
      renvoie `racine/CLAUDE.md`, `racine/CLAUDE.local.md`,
      `racine/projects/CLAUDE.md` et `racine/projects/CLAUDE.local.md`, mais
      pas `racine/projects/p/CLAUDE.md`
- [ ] Un test vérifie qu'elle renvoie une liste vide pour un projet
      `git_root: ancestor`
- [ ] Un test vérifie qu'elle renvoie une liste vide pour un dossier hors de
      la racine
- [ ] Un test vérifie que les options construites par `agent_sdk.py` pour un
      projet hébergé portent `claudeMdExcludes` dans `settings`, et n'en
      portent pas pour ide-core

## Dépendances

Aucune.

## Risques

- Les chemins Windows : comparer des chemins résolus, et passer à
  `claudeMdExcludes` des chemins absolus avec `/`.
- Après merge et redémarrage, retirer la phrase de contournement du
  `CLAUDE.md` de curio (geste manuel).