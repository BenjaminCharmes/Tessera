---
agent: codeur
created: 2026-10-23
depends_on:
- ticket-544
estimated_days: 1.5
id: ticket-546
plan: true
pr_number: 625
priority: high
status: done
title: git_workspace.py is split into a package, one module per concern
type: refactor
---

# ticket-546 — Découper `git_workspace.py`

## Objectif
Que `services/git_workspace.py` (2 294 lignes, une classe d'environ 80
méthodes) devienne un paquet dont chaque module tient un sujet, sans changer
le comportement ni les imports existants.

## Contexte
Le fichier a reçu 46 commits depuis septembre et mélange six sujets :
- utilitaires de module (slug, lockfiles, unions de texte et de JSON, chemins
  d'artefacts) ;
- base et branche (`create_branch`, `initialiser_base_ref`,
  `sync_base_depuis_distant`, `restaurer_ticket_depuis_base`…) ;
- inspection (`diff_depuis_base`, `current_diff`, `dirty_files`, `is_clean`,
  SHA, ancêtres) ;
- commits (`commit_all`, `commit_bookkeeping`, staging sélectif des tickets) ;
- rebase et conflits (`rejouer_sur`, `_rebaser`, résolutions d'artefacts, de
  journal, de Prisma, renumérotation des migrations) ;
- identité du dépôt (`_is_own_repository`, `_toplevel`, worktree déclaré).

18 modules importent depuis `tessera.services.git_workspace`.

## Solution proposée
`services/git_workspace/` devient un paquet. `__init__.py` réexporte tout ce
qui est importé aujourd'hui (`GitWorkspaceService`, les exceptions, les
fonctions utilisées ailleurs), pour que les 18 importeurs ne changent pas.
`GitWorkspaceService` reste une façade qui délègue à des classes ou mixins
par sujet. Le tour de plan choisit entre mixins et composition, et dit
comment les tests qui patchent des méthodes privées continuent de fonctionner.

## Critères d'acceptation
- [ ] `backend/src/tessera/services/git_workspace.py` n'existe plus ; `backend/src/tessera/services/git_workspace/` existe avec un `__init__.py`
- [ ] Aucun module du paquet ne dépasse 400 lignes
- [ ] Le diff ne modifie aucun fichier hors de `backend/src/tessera/services/git_workspace/`, de `backend/tests/` et du test du ticket-544
- [ ] La table `PLAFONDS` de `backend/tests/test_longueur_des_fichiers.py` ne contient plus `git_workspace.py`, et liste les modules du paquet qui dépassent 300 lignes
- [ ] Le testeur passe la suite complète : aucun test existant n'est supprimé (un test déplacé garde son nom)

## Risques
Les tests qui `monkeypatch` des méthodes privées par leur chemin de module
cassent au déplacement : le plan les recense avant de couper.

## Ce que ça ne fait pas
- Ne change aucun comportement, aucun nom public, aucun message de log.