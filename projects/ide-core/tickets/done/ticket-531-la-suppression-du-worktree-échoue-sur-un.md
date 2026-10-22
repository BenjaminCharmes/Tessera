---
agent: codeur
created: '2026-10-22'
depends_on: []
id: ticket-531
priority: medium
status: done
title: La suppression du worktree échoue sur un chemin de plus de 260 caractères dans
  node_modules, et le run livré finit interrupted
type: fix
---

## Signalement

- Projet source : kadoomi
- Nature : bug
- Reçu le : 2026-10-22

## Description

Run d6737be6 (kadoomi, ticket-090), 22/10 08:41:41 UTC. La livraison a abouti (rebase, PR #115 ouverte, pushed_sha 564fd10), puis un error WinError 3 « chemin introuvable » sur ~/.tessera/worktrees/kadoomi/ticket-090/node_modules/.pnpm/@typescript-eslint+eslint-p_<hash>/node_modules/@typescript-eslint/eslint-plugin/dist/rules/prefer-optional-chain-utils/PreferOptionalChainOptions.d.ts (plus de 260 caractères). Le run_closed passe en final_status interrupted, approved false, rounds 0, alors que le ticket est done et sa PR ouverte. Le worktree reste en place (git worktree list le montre). Piste : supprimer avec le préfixe \? (chemins longs) ou par git worktree remove --force, et ne pas faire échouer le run sur un nettoyage postérieur à la livraison.

## Contexte

Événements error et run_closed du run d6737be6405343ddab570fe12f316b6f. pnpm crée des chemins profonds : tout projet pnpm en worktree le rencontrera. Contournement : aucun, worktree laissé en place.

## Cause (triage ide-core, 22/10)

Deux défauts dans `services/run_dans_worktree.py` et
`services/run_worktree_populate.py` :
1. `retirer_les_liens` parcourt tout le worktree (`os.scandir`, `os.lstat`,
   `is_dir`) avec des chemins ordinaires : sous Windows, un chemin de plus de
   260 caractères lève `OSError` (WinError 3). `core.longpaths` ne couvre que
   git, pas Python.
2. `retirer_en_fin_de_run` ne rattrape que `TravailNonSauve` et
   `LienPersistant`, après avoir déjà posé `_worktree_retire = True` : toute
   autre erreur (`OSError`, `GitWorkspaceError`) remonte, le résultat livré est
   perdu et le run finit `interrupted` ; le repli `retirer_apres_echec` est
   sauté.

## Solution proposée

- Une fonction `chemin_etendu(p: Path) -> str` dans
  `services/run_worktree_populate.py` : sous Windows, le chemin absolu préfixé
  de `\\?\` ; ailleurs, `str(p)` inchangé. `retirer_les_liens` l'utilise pour
  tout appel au système de fichiers.
- `retirer_en_fin_de_run` rattrape aussi `OSError` et `GitWorkspaceError` :
  le résultat du run est rendu inchangé (livré reste livré), un avertissement
  `run_worktree_non_supprime` est journalisé avec le dossier, et le worktree
  reste pour la reprise au démarrage (ticket-520).

## Constat du 22/10 (nettoyage à la main)

Même `git -c core.longpaths=true worktree remove` sur ce worktree a échoué
(« Directory not empty ») : git n'arrive pas à vider `node_modules/.pnpm`.
Seul `rmdir /s /q "\?\<chemin>"` l'a supprimé. Les jonctions de pnpm y
pointent toutes à l'intérieur du worktree.

## Critères d'acceptation

- [ ] `chemin_etendu` existe dans `services/run_worktree_populate.py` ; un test vérifie, en simulant la plateforme, qu'il préfixe `\\?\` sous Windows et rend le chemin inchangé ailleurs
- [ ] `retirer_les_liens` passe par `chemin_etendu` pour lister, inspecter et retirer les entrées
- [ ] Un test vérifie, avec des doubles, qu'une `OSError` levée pendant la suppression laisse `retirer_en_fin_de_run` rendre le résultat du run inchangé (même `final_status`, même `arret`)
- [ ] Le même test, ou un autre, vérifie le même comportement pour une `GitWorkspaceError` levée par `git worktree remove`
- [ ] Quand `git worktree remove` échoue sur un worktree propre et sans lien vers l'extérieur, `supprimer` termine la suppression du dossier par un chemin étendu (`chemin_etendu`), puis `git worktree prune` ; un test le vérifie avec des doubles
- [ ] Dans ces deux cas, un avertissement `run_worktree_non_supprime` est journalisé avec la racine du worktree

## Ce que ça ne fait pas

- N'ajoute pas `--force` à `git worktree remove` : un worktree sale reste
  protégé (règle « worktree non commité »).