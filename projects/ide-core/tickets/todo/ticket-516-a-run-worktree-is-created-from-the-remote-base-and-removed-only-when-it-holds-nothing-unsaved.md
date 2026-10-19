---
id: ticket-516
title: "A run worktree is created from the remote base and removed only when it holds nothing unsaved"
type: feat
status: todo
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-10-19
pr_number: null
---

# ticket-516 — Créer, reprendre et supprimer le worktree d'un run

## Objectif
Un service qui donne à un run son dossier de travail, sans toucher le checkout,
et qui ne détruit jamais du travail non sauvé.

## Contexte
ADR-056, spec § 1. `services/temporary_worktree.py` (ticket-479) fournit
`run_git` et un worktree **détaché et jetable**. Celui-ci est nommé, extrait sur
la branche du ticket, et survit à la requête. Réutiliser `run_git`, ne pas le
recopier.

## Ce qu'il faut faire
Nouveau module `backend/src/tessera/services/run_worktree.py` :

```python
@dataclass(frozen=True)
class RunWorktree:
    racine: Path          # <IDE_WORKTREES_DIR>/<project_id>/<ticket_id>
    projet: Path          # le dossier du projet dans le worktree
    branche: str

async def creer(depot: Path, project_path: Path, project_id: str,
                ticket_id: str, branche: str, base: str) -> RunWorktree: ...
async def supprimer(wt: RunWorktree, depot: Path) -> None: ...
```

- `creer` : `fetch` de `origin/<base>`, puis `git worktree add -b <branche>
  <racine> origin/<base>` — sans `-b` si la branche existe (reprise). Un dossier
  déjà là, propre et sur la bonne branche, est repris ; sinon `WorktreeOccupe`.
  Git refuse la branche déjà extraite ailleurs : l'erreur se remonte nommée
  (`BrancheDejaExtraite`), sans `--force`.
- `projet` se déduit de `project_path` relativement à `git rev-parse
  --show-toplevel` (cas `git_root: ancestor` : sous-dossier du dépôt).
- `core.longpaths=true` sur **chaque** appel git : l'ajouter à `run_git`
  (`temporary_worktree.py`) et à `GitWorkspaceService._run`, hooks toujours
  désactivés.
- `supprimer` refuse (`TravailNonSauve`) si `git status --porcelain
  --untracked-files=normal` n'est pas vide : le dossier reste, la cause le
  nomme. Sinon `worktree remove`, puis `worktree prune`. Jamais `--force` sur un
  arbre sale. Le retrait des liens est le sujet du ticket-517 : ici, appeler un
  point d'extension `retirer_les_liens(racine)` vide.

## Tests
`backend/tests/test_run_worktree.py`, sur un dépôt temporaire avec un `origin`
local (dépôt nu) :
- [ ] `creer` crée le dossier attendu, sur la branche, au commit de `origin/<base>`
- [ ] un fichier écrit à la main dans le checkout n'existe pas dans le worktree
- [ ] `creer` deux fois sur la même branche : le second reprend un worktree propre
- [ ] branche déjà extraite dans le checkout → `BrancheDejaExtraite`, rien de forcé
- [ ] `supprimer` sur arbre propre retire le dossier et l'enregistrement git
- [ ] `supprimer` sur arbre sale lève `TravailNonSauve` et laisse le dossier
- [ ] un chemin de plus de 260 caractères se crée (Windows ; ignoré ailleurs)
- [ ] `projet` pointe le sous-dossier pour un projet `git_root: ancestor`
- [ ] le checkout de départ est resté sur sa branche, arbre inchangé

## Critères d'acceptation
- [ ] Les neuf tests ci-dessus existent et passent
- [ ] `run_git` n'est pas dupliqué ; les tests existants de `temporary_worktree` et `git_workspace` passent
- [ ] Aucun appel depuis le pipeline : le branchement est le ticket-518

## Dépendances
Aucune.

## Ce que ça ne fait pas
Ni peuplement, ni suppression des liens (517), ni branchement dans le run (518).
