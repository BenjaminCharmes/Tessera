---
id: ticket-1039
title: "Démineur runs in a worktree, under the agent account"
type: chore
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
preuve_reelle: true
created: 2026-11-23
---

# ticket-1039 — Démineur tourne dans un worktree, sous le compte agent

## Objectif

Étendre le compte agent à un deuxième projet, Démineur, pour vérifier que ce
qui a été prouvé sur Serpent (ADR-083 à ADR-091) ne tenait pas à Serpent seul.

## Contexte

Seul Serpent déclare `worktree.compte_agent` dans son `agents.json`. Démineur
est le candidat le moins risqué : même chaîne que Serpent (Vite 7, Vitest 3,
la même `test_command` npm), aucun secret, aucune base, aucun service en
ligne, `autonomy: merge` avec `merge_without_ci`.

Relevé le 23/11 dans `projects/demineur`, trois écarts avec Serpent :

1. `agents.json` n'a pas de bloc `worktree` : les runs travaillent dans le
   checkout, sous le compte de l'utilisateur.
2. `memory/documentation.json` est exclu par `.git/info/exclude` (Serpent le
   versionne). Dans un worktree tiré de `origin/main`, le marqueur serait
   absent à chaque run : `mettre_a_jour` le réinitialiserait avec tous les
   tickets terminés et ne documenterait jamais rien.
3. Le checkout porte une modification non commitée de `memory/pipeline-log.md`
   sur `main`.

Un projet à worktree ne trouve un ticket que s'il est sur `origin/main`
(`refus_avant_ouverture`, `controle_base.py`).

## Ce ticket se fait à la main

`agents.json` et `.git/` se refusent en écriture à tout agent (ADR-067,
ADR-027) : lancé dans le pipeline, ce ticket tournerait trois tours sur un diff
vide. La session ide-core le réalise, par une PR dans le dépôt de Démineur, et
seulement après le contrôle de l'Orchestrateur.

## Solution proposée

Dans le dépôt de Démineur, sur une branche, PR vers `main` :

1. Commiter l'état de `memory/pipeline-log.md` laissé dans le checkout.
2. Retirer `memory/documentation.json` de `.git/info/exclude` et versionner le
   marqueur tel qu'il est sur disque.
3. Ajouter à `agents.json` le bloc de Serpent, sans autre changement :
   `"worktree": {"populate": [], "setup": "npm ci", "setup_timeout_s": 600, "compte_agent": true}`.
4. Aligner `artifacts` sur ce que le dépôt fait déjà (tickets et mémoire y
   sont versionnés) : `tracked`.

Aucun changement dans le code de Tessera, aucun rechargement du backend :
`agents.json` est relu à chaque run.

## Critères d'acceptation

- [ ] `projects/demineur/agents.json` porte un bloc `worktree` avec
      `compte_agent: true` et `setup: "npm ci"`.
- [ ] `memory/documentation.json` est versionné sur `main` de Démineur.
- [ ] `git status` du checkout de Démineur est propre sur `main` après le merge.

## Preuve réelle

Avant : `.\scripts\tessera.ps1 agent doctor` sans point rouge.

Puis un ticket Démineur minuscule (un test ou un libellé), poussé sur
`origin/main`, lancé seul par le pipeline. À constater sur la machine :

- le run crée `C:\ProgramData\Tessera\worktrees\demineur\<ticket>` et n'écrit
  rien dans le checkout `projects/demineur` ;
- pendant l'appel du codeur, un `claude.exe` appartient à `tessera-agent`
  (`Get-CimInstance Win32_Process` avec `GetOwner`) ;
- `npm ci` puis la `test_command` passent sous ce compte (ligne du testeur
  dans `memory/pipeline-log.md` du worktree) ;
- le run finit `APPROVED`, sa PR se merge seule, le worktree est supprimé ;
- après le run : aucun processus de `tessera-agent`, aucune tâche planifiée à
  son nom, `C:\ProgramData\Tessera\profil-agent` ne garde que le cache npm ;
- la passe de documentation lit un marqueur existant (pas de réinitialisation
  dans le journal) ;
- aucun run Serpent ne tourne en même temps (un worktree à la fois sous le
  compte, ADR-087) : le vérifier avant de lancer.

Si un point échoue : retirer `compte_agent` par une PR, Démineur revient à son
fonctionnement d'aujourd'hui, et le défaut devient un ticket ide-core.

## Ce que ça ne fait pas

- N'étend pas le compte agent aux autres projets : chacun aura sa preuve.
- Ne déclare pas `pipeline.controle_visuel` sur Démineur.
- Ne change ni le modèle des rôles ni l'autonomie du projet.

## Dépendances

Aucune dans le code. Contrôle de l'Orchestrateur avant tout lancement.

## Estimation

Une demi-journée, preuve comprise.

## Risques

- Les appels sous le compte agent se font un worktree à la fois : un run
  Démineur et un run Serpent ne peuvent plus se chevaucher.
- Chaque appel paie l'ouverture et la clôture du compte : un run Démineur sera
  plus lent qu'aujourd'hui.
- Démineur sert à mesurer l'orchestration (`memory/mesures.md`) : ses durées
  d'avant et d'après ce ticket ne se comparent plus directement.
