---
agent: codeur
created: 2026-11-02
depends_on:
- ticket-674
id: ticket-732
pr_number: 841
priority: low
status: done
title: A conflicting PR branch is merged with its base in a throwaway worktree
type: feat
---

# ticket-732 — Fusionner la base dans la branche d'une PR, hors de tout arbre de travail

## Contexte

ADR-069 (conception : ticket-674). Une PR `conflicting` s'arrête aujourd'hui sur
« à rebaser » (ticket-452). Ce ticket livre le **geste** : fusionner
`origin/<base>` dans la tête poussée et la pousser sans forcer. Le branchement
dans `CIWatcher` est le ticket-733 : ici, rien n'appelle encore ce module.

## Interface

Nouveau module `backend/src/tessera/services/mise_a_jour_branche.py`.

```python
@dataclass(frozen=True)
class MiseAJour:
    sha: str | None      # nouvelle tête poussée ; None si rien n'est parti
    arret: str | None    # cause du refus ; None quand sha est rempli
    etapes: tuple[str, ...] = ()

async def mettre_a_jour_branche(
    depot: Path, branche: str, base: str, tete_attendue: str,
    retest: RetestApresRebase | None = None,
) -> MiseAJour: ...
```

Déroulé, dans l'ordre :

1. `git fetch origin <base> <branche>` ; si `origin/<branche>` n'est pas
   `tete_attendue`, refus — aucun worktree n'est créé.
2. `detached_worktree(depot, tete_attendue)` (ticket-479) : le checkout du
   projet, son index et sa branche ne sont ni lus ni déplacés (ADR-056).
3. `git merge --no-edit origin/<base>` ; message de commit en anglais
   (`chore: merge <base> into <branche>`). Rien à fusionner : refus, la
   cause du conflit est ailleurs.
4. Conflits : tous dans `_JOURNAL_UNION_SUFFIXES` (`pipeline-log.md`,
   `documentation.json`) → union, en réutilisant `_union_lines` et
   `_union_json_lists`. **Dans un merge, l'étage 2 est la branche de la PR et
   l'étage 3 la base** — l'inverse du rebase : la base vient en premier dans
   l'union, comme au ticket-391. Un autre fichier en conflit, ou un JSON
   illisible : refus, rien n'est poussé.
5. Avec un `retest`, `juger()` avant le push ; un rouge refuse (ADR-039).
6. `git push origin HEAD:refs/heads/<branche>` — jamais `--force`, jamais
   `--force-with-lease` (ADR-022). Un push refusé est un refus, sans nouvelle
   tentative.
7. `sha` = `git rev-parse HEAD` du worktree, relu après le push.

Toute exception (git, worktree, réseau) devient un `MiseAJour` avec `arret` ;
le module ne lève jamais vers le watcher. Le worktree se supprime quoi qu'il
arrive.

## Critères d'acceptation

- [ ] Test sur un dépôt réel et un distant nu : une branche en retard sur la base, sans conflit, repart avec un commit de merge dont le premier parent est `tete_attendue` ; `sha` est la tête du distant
- [ ] Test : un conflit sur `documentation.json` seul se résout en union (entrées de la base et de la branche présentes, sans doublon) et le merge aboutit
- [ ] Test : un conflit sur un fichier de code refuse, `sha` est `None`, la tête du distant n'a pas bougé
- [ ] Test : une tête distante différente de `tete_attendue` refuse avant toute écriture
- [ ] Test : un push refusé (distant avancé entre-temps) refuse sans second push ; aucune commande git du module ne porte `--force`
- [ ] Test : `git status` et `HEAD` du checkout du projet sont identiques avant et après, succès comme refus
- [ ] Test : un `retest` rouge refuse sans push ; vert, la mise à jour part
- [ ] Le fichier reste sous 300 lignes ; `scripts/verifier.py` passe

## Ce que ça ne fait pas

- Ne branche rien dans `CIWatcher` ni dans `surveillance_pour` (ticket-733).
- N'écrit pas `pushed_sha` : c'est le watcher qui le note (ticket-733).
- N'appelle aucun agent : un conflit hors journaux se refuse, il ne se tente pas (ADR-033).