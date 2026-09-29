---
id: ticket-244
title: "Le lot de documentation tient aussi le CLAUDE.md du projet, dans un budget"
type: feat
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-244 — Le lot de documentation tient aussi le CLAUDE.md du projet

## Objectif

Un projet qui déclare `pipeline.doc_claude_md: true` laisse `doc-technique`
corriger son `CLAUDE.md` dans le lot de documentation, par modifications
ciblées, sans que le fichier franchisse un budget de taille.

## Contexte

`doc-technique` et `doc-fonctionnelle` n'écrivent que `README.md` et `docs/`.
Le `CLAUDE.md` d'un projet se tient à la main : quand un ticket rend une de ses
phrases fausse (« le testeur ne peut pas être activé »), la consigne fausse
reste chargée dans chaque session jusqu'à ce que quelqu'un la relise.

L'inverse est aussi un risque : chaque ligne d'un CLAUDE.md concurrence les
autres pour l'attention du modèle. Un agent qui y ajoute à chaque lot produit
un fichier qu'on finit par ignorer.

## Solution proposée

- `AgentPipelineConfig.doc_claude_md`, faux par défaut.
- `appliquer_editions(…, claude_md=…)` : « CLAUDE.md » désigne celui **du
  projet**, jamais celui de la racine d'écriture (pour ide-core, ce serait
  celui de Tessera, que la règle 5 réserve à un ticket explicite).
- Budget : 6 000 caractères. Un fichier sous le budget peut grandir jusqu'à
  lui ; un fichier déjà au-delà ne peut que raccourcir. Au-delà, le lot est
  rejeté, comme toute édition refusée d'ADR-035.
- Seul `doc-technique` reçoit le fichier et peut l'éditer.
- ide-core le déclare.
- **Ce ticket modifie `projects/ide-core/agents.json`** (la déclaration) et le
  prompt `doc-technique.md`.

## Critères d'acceptation

- [ ] `test_documentation_claude_md.py` vérifie qu'une édition de `CLAUDE.md` écrit celui du projet et laisse celui de la racine intact
- [ ] `test_documentation_claude_md.py` vérifie que sans déclaration, une édition de `CLAUDE.md` est refusée et n'écrit rien
- [ ] `test_documentation_claude_md.py` vérifie qu'une édition qui franchit le budget est refusée
- [ ] `test_documentation_claude_md.py` vérifie qu'un fichier déjà au-delà du budget peut raccourcir mais pas grandir
- [ ] `test_documentation_claude_md.py` vérifie que seul `doc-technique` reçoit le contenu du `CLAUDE.md`

## Ce que ça ne fait pas

- Le `CLAUDE.md` de la racine du dépôt et celui de `~/.claude/` ne sont jamais
  touchés.
- L'écriture ne passe pas par les outils de l'agent : `doc-technique` rend du
  JSON, le service écrit. Le hook du ticket-240 n'est donc pas en jeu.
