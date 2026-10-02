---
agent: codeur
created: 2026-10-01
depends_on: []
estimated_days: 1
id: ticket-293
pr_number: 192
priority: medium
status: done
title: Tessera ships its own skills to every project's agents
type: feat
---

# ticket-293 — Tessera livre ses propres skills aux agents de tous les projets

## Objectif

Un rôle de n'importe quel projet peut déclarer dans `agents.json` un skill
**livré par Tessera** (`"skills": ["tessera:<nom>"]`), sans que ce skill soit
copié dans le dépôt du projet.

## Contexte

Depuis le ticket-242, un rôle déclare les skills qu'il voit. Mais le CLI ne
les cherche que dans le `.claude/skills/` du projet. Un skill utile à tous les
projets devrait donc être recopié dans chacun, ce qui pose trois problèmes :

- on écrit dans des dépôts tiers, alors qu'ADR-021 et ADR-023 tiennent les
  artefacts de Tessera hors de ces dépôts ;
- les copies divergent (ADR-034) ;
- un agent ne peut pas écrire `.claude/skills/` (ticket-240) : chaque copie se
  fait à la main.

Le SDK installé (0.2.152) accepte `plugins=[{"type": "local", "path": …}]`.
Ça a été vérifié en réel le 2026-10-01 : un plugin nommé `tessera` qui porte
`skills/sonde/SKILL.md` expose le skill `tessera:sonde`. Avec
`skills=["tessera:sonde"]` et `tools=["Skill"]`, l'agent le charge et en
applique le contenu.

## Solution proposée

- Créer un plugin local versionné dans le dépôt de Tessera,
  `agents/plugin/` :
  - `.claude-plugin/plugin.json` avec `{"name": "tessera", "version": "0.1.0"}` ;
  - `skills/<nom>/SKILL.md` pour chaque skill. Ce ticket n'en livre aucun de
    réel ; le premier arrive avec le ticket-294.
- Localiser le dossier comme les prompts du produit (voir `prompt_loader.py`
  et `IDE_PROMPTS_DIR`), en chemin absolu résolu. Ne jamais le résoudre depuis
  le `cwd` du projet.
- Dans `_build_options` (`services/providers/agent_sdk.py`), passer le plugin
  **uniquement** si au moins un skill déclaré commence par `tessera:`. Sinon
  `plugins` reste vide et rien ne change.
- Le nom complet, préfixe compris, part tel quel dans `skills=[…]` : c'est la
  forme que liste le CLI.

## Critères d'acceptation

- [ ] `agents/plugin/.claude-plugin/plugin.json` existe et déclare `"name": "tessera"`
- [ ] `test_skills_par_role.py` vérifie que `_build_options(skills=["tessera:x"])` passe un seul plugin `{"type": "local", "path": …}` dont le chemin est absolu et désigne `agents/plugin/`
- [ ] `test_skills_par_role.py` vérifie que `_build_options(skills=["verifier-mon-travail"])` et `_build_options(skills=None)` ne passent aucun plugin
- [ ] Un test vérifie que chaque dossier de `agents/plugin/skills/` contient un `SKILL.md` dont le frontmatter porte un `name` égal au nom du dossier et une `description` non vide
- [ ] `test_skills_par_role.py` vérifie que chaque skill `tessera:<nom>` déclaré dans `projects/ide-core/agents.json` existe sous `agents/plugin/skills/<nom>/SKILL.md`. Le contrôle existant sur les skills du projet reste en place pour les noms sans préfixe.

## Ce que ça ne fait pas

- Ça ne s'applique qu'au provider Agent SDK. Un rôle sur Ollama ou sur la
  Messages API ignore ses skills, comme avant.
- `agents/plugin/` n'est pas protégé en écriture, pas plus que
  `agents/prompts/` : c'est du code du produit, modifié par ticket et relu
  comme le reste. Un agent qui écrit là change les consignes des runs
  suivants, exactement comme quand il modifie un prompt.
- Pas de réglage dans l'UI.

## Risques

- La forme du plugin (`plugin.json`, préfixe `tessera:`) dépend du CLI. Si une
  mise à jour du SDK la change, le skill disparaît sans erreur : l'agent ne le
  voit plus. Le test de la forme d'options ne l'attrape pas ; seul un run réel
  le montre.