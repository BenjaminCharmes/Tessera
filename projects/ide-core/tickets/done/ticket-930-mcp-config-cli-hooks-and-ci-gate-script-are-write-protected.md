---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-930
pr_number: null
priority: high
status: done
title: The project MCP config, CLI hook scripts and the CI forbidden-terms script
  are write-protected
type: fix
---

# ticket-930 — `.mcp.json`, `.claude/hooks/` et le script CI des termes interdits se refusent en écriture

## Objectif

Qu'un run ne puisse pas déposer du code que le CLI ou la CI exécutera plus
tard, en dehors de ce qu'il livre et que la revue lit.

## Contexte

Audit du 11/11, vérifié sur `origin/develop` dans
`backend/src/tessera/services/providers/chemins_proteges.py` :
`motif_de_protection` (l. 99-163) refuse `agents.json`, `.git/`,
`.claude/settings*.json`, `.claude/{skills,commands,agents}/`,
`.github/workflows/`, `CLAUDE.md`, le `.env` et `scripts/hooks/`. Il laisse
passer :

- **`.mcp.json`** — les serveurs MCP du projet. L'agent tourne avec
  `setting_sources=["project"]`
  (`backend/src/tessera/services/providers/agent_sdk.py`, l. 175) : le
  fichier est lu par le CLI des sessions suivantes, et par une session humaine
  ouverte dans le dossier.
- **`.claude/hooks/**`** — les scripts qu'un `settings.json` désigne : le
  `settings.json` est protégé, mais pas le script qu'il lance, qui
  s'exécuterait sous le compte du backend au run suivant.
- **`scripts/termes_interdits_ci.py`** — exécuté par la CI
  (`.github/workflows/ci.yml`, l. 58), c'est l'une des trois portes des termes
  interdits (ADR-050), au même titre que `scripts/hooks/` déjà protégé. Sa
  lecture depuis la base est corrigée à la main en parallèle ; ce ticket
  refuse en plus son écriture par un agent.

Classe de la faille : ce que le CLI charge ou exécute (`.claude/settings*`,
`skills`, `commands`, `agents` — déjà protégés ; `hooks`, `.mcp.json` —
ajoutés ici) et ce qui sert de porte en CI (`scripts/hooks/` déjà protégé,
`scripts/termes_interdits_ci.py` ajouté ici ; `scripts/verifier.py` l'est déjà
comme script de `test_command`). Les autres étapes de la CI exécutent le code
livré : c'est leur rôle, et ce code passe la revue.

ADR-031 : ce refus porte sur les outils d'écriture et les formes Bash
simples ; il attrape une erreur, pas une évasion.

## Solution proposée

- `motif_de_protection` refuse un dernier segment `.mcp.json` (normalisé
  comme les autres) et tout chemin sous `.claude/hooks/`.
- `_motif_du_depot` refuse `scripts/termes_interdits_ci.py` sous la racine
  d'écriture, à côté de `scripts/hooks/`.
- `_NOMS_PROTEGES_INLINE`
  (`backend/src/tessera/services/providers/redirections_bash.py`) gagne
  `.mcp.json` et `termes_interdits_ci.py`, pour le filet `python -c`.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_chemins_proteges.py` vérifie qu'un
      `Write` de `<projet>/.mcp.json` est refusé.
- [ ] Un test vérifie qu'un `Write` de `<projet>/.claude/hooks/x.py` est
      refusé.
- [ ] Un test vérifie qu'un `Write` de `scripts/termes_interdits_ci.py` sous
      une racine `git_root: ancestor` est refusé.
- [ ] Un test vérifie qu'un `Write` de `<projet>/.claude/notes.md` passe.
- [ ] `backend/src/tessera/services/providers/redirections_bash.py` cite
      `.mcp.json` dans `_NOMS_PROTEGES_INLINE`.

## Ce que ça ne fait pas

- Ne corrige pas la lecture de `termes_interdits_ci.py` depuis la base dans
  la CI : correctif manuel en cours, `.github/` n'est pas écrivable par un
  agent.
- Ne détecte pas une modification par `sed -i` ou `dd` : ticket-933.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un projet qui versionne un `.mcp.json` légitime ne pourra plus le faire
évoluer par un run : comme `agents.json`, c'est un changement à la main.