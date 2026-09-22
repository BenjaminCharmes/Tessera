---
id: ticket-119
title: "Figer la politique du run et refuser les chemins qui la portent"
type: fix
status: in-progress
pr_number: null
priority: critical
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-22
---

# ticket-119 — Figer la politique du run et refuser les chemins qui la portent

## Objectif

Qu'un agent ne puisse pas, depuis l'intérieur d'un run, changer les règles qui
bornent ce run — ni en éditant `agents.json`, ni en déposant un hook git, ni en
contournant le garde git par une tournure triviale.

## Contexte

- `perimetre.py` accepte toute écriture sous la racine du projet. `agents.json`
  y est. `lire_niveau` (autonomy) et `racine_autorisee` (git_root) le relisent
  **après** le passage du codeur : un ticket peut passer un projet en
  `merge` + `ancestor` dans le même run (ADR-029, ADR-031 vidés en pratique).
- `project/.git/hooks/pre-commit` et `.git/config` sont sous la racine.
  `commit_all` lance `git commit` dans le process de l'orchestrateur : un hook
  déposé par l'agent s'exécute avec l'identité de l'utilisateur (ADR-027
  contourné sans une seule commande git dans `Bash`).
- `git_guard.commande_git_interdite` laisse passer `ls\ngit push`,
  `env git push`, `sh -c 'git push'`, `git -c alias.p=push p`,
  `/usr/bin/git push`, `git.exe push`, `gh pr merge`. Vérifié en exécution.
- `.claude/settings*.json` sous le projet peut déclarer des hooks que le CLI
  exécute au run suivant (`setting_sources=["project"]`). `.github/workflows/`
  est ce qui rend la CI « verte » en mode `merge`.

## Solution proposée

1. **Snapshot de politique.** Une dataclass `PolitiqueRun` (autonomy,
   git_root, artifacts, test_command) lue **une fois** au début du run par
   l'orchestrateur et passée à `LivraisonService`, `GitWorkspaceService`,
   `TestRunnerService` et au hook de périmètre. Plus aucune relecture
   d'`agents.json` après le premier appel d'agent.
2. **Chemins refusés sous la racine.** Dans `hook_refus_hors_perimetre` :
   `agents.json`, tout segment `.git`, `.claude/settings*.json`,
   `.github/workflows/**`. Message distinct de celui du hors-périmètre.
3. **Hooks git neutralisés côté orchestrateur.** `GitWorkspaceService._run`
   passe `-c core.hooksPath=<dossier vide>` sur les commandes qui écrivent.
4. **Garde git durci.** Tokenizer : `\n` et `\r` comme séparateurs, chaîne
   d'exécution (`sh`, `bash`, `env`, `command`, `exec`, `eval`, `xargs`,
   `time`, `nohup`, `timeout`, `sudo`) transparente, premier jeton comparé
   insensible à la casse et après suppression d'un chemin et de `.exe`,
   `-c alias.*` refusé, `gh` (pr, api, repo) refusé. Les huit formes citées
   dans le contexte passent en test.
5. **ADR-027 amendé** (skill `write-adr`) : dire ce que le garde garantit
   vraiment, comme ADR-031 le fait, et référencer les chemins refusés.

Hors périmètre : sandboxing du process agent, vérification de l'intégrité de
la CI distante.

## Critères d'acceptation

- [x] Un test montre qu'`Edit agents.json` → `{"autonomy": "merge"}` pendant le
      run n'affecte pas le niveau vu par `LivraisonService`
- [x] Le hook refuse `Write` sur `agents.json`, `.git/hooks/pre-commit`,
      `.git/config`, `.claude/settings.local.json`,
      `.github/workflows/ci.yml` — un test par chemin
- [x] Un test montre qu'un `pre-commit` déposé dans `.git/hooks` n'est pas
      exécuté par `commit_all`
- [x] `commande_git_interdite` renvoie `True` pour les huit formes du contexte
      et `False` pour `git status`, `git log`, `git diff`, `echo git push`
- [x] ADR-027 amendé dans `memory/decisions.md`, budget respecté
      (`test_consignes_coherentes.py` vert)
- [x] `uv run pytest -q` et `uv run mypy src/` verts

## Ce que ça ne fait pas

- **Pas de sandbox.** Le garde git et le hook de périmètre lisent ce que
  l'agent tape ; ils attrapent une erreur et les tournures triviales, pas une
  évasion. `python -c "subprocess.run(['git','push'])"` passe, un script
  écrit dans le projet puis lancé passe, `sudo -u root git push` passe (le
  jeton `root` n'est pas lu comme une option). ADR-031 le disait déjà pour
  les écritures ; ADR-027 le dit maintenant pour git.
- **La lecture GitHub tombe avec l'écriture.** `gh pr view` est refusé comme
  `gh pr merge` : distinguer les deux sous-commande par sous-commande
  multiplierait les formes à connaître, et lire GitHub n'est pas ce qui
  manque à un agent.
- **Les hooks ne sont neutralisés que côté orchestrateur.** Un `pre-commit`
  arrivé dans `.git/hooks` par un autre chemin que `Write`/`Edit`/`Bash`
  simple ne tournera pas depuis `GitWorkspaceService`, mais il reste dans le
  clone de l'utilisateur, qui l'exécutera à son prochain commit manuel. Il
  n'est ni détecté ni supprimé.
- **`.git/config` n'est pas relu.** `core.hooksPath` y est neutralisé par
  `-c`, mais d'autres clefs exécutables (`core.fsmonitor`, `diff.external`,
  `core.sshCommand`) ne le sont pas : c'est le refus d'écriture sur `.git/`
  qui les couvre, avec les limites du point précédent.
- **La politique figée ne vaut que dans un run.** Le chat, les endpoints de
  PR et de synchronisation lisent toujours `agents.json` au moment d'agir :
  ce sont des gestes de l'utilisateur, pas d'un agent, et la valeur courante
  du fichier est celle qu'il attend.
- **L'intégrité de la CI distante n'est pas vérifiée.** Un workflow modifié
  par un run précédent et déjà mergé rend la CI « verte » pour les suivants.
  Hors périmètre, comme annoncé.

## Dépendances
Aucune.

## Estimation
2 jours.

## Risques
Un faux refus sur un chemin légitime (un projet dont un dossier s'appelle
`.github/workflows` par usage réel) : le message doit dire pourquoi.
