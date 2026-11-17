---
agent: codeur
depends_on:
- ticket-895
id: ticket-994
preuve_reelle: true
priority: high
status: done
title: Protected files stay readable for the agent account
type: fix
---

## Contexte

Cinquième preuve réelle du 17/11 (Serpent ticket-009, run `ad42dba3`) :
181 tests sur 182 passent sous `tessera-agent` ; le dernier lit
`.github/workflows/ci.yml` et reçoit `EPERM`. Le `Read` du codeur sur ce
fichier échoue de même.

`droits_worktree.accorder_droits_agent` (ticket-895) pose sur chaque fichier
protégé (`agents.json`, `CLAUDE.md`, script de test, `.github/workflows/`…)
`icacls /deny <compte>:(W,D)`. Les droits simples `W` et `D` d'icacls
portent aussi `SYNCHRONIZE` : le refuser interdit d'ouvrir le fichier, même
en lecture. Or la règle ne refuse que l'écriture et la suppression ; lire
reste permis (ADR-031).

Mesuré sous le compte, sur quatre fichiers d'un même dossier où il a `M` :
témoin lu et écrit ; `(WD,AD)` et `(WD,AD,WEA,WA,DE)` lus, écriture refusée ;
`(W,D)` ni lu ni écrit.

## Ce qu'il faut faire

- Refuser les droits précis `(WD,AD,WEA,WA,DE)` : écrire, ajouter, attributs,
  attributs étendus, supprimer. La lecture reste.

## Critères d'acceptation

- [x] Test : chaque refus posé porte `WD`, `AD` et `DE`, et ni `W`, ni `D`,
      ni `F`, ni `M`.
- [x] Test existant : les trois fichiers protégés reçoivent le refus.

## Preuve réelle

Avant merge, sur le poste : l'essai des quatre fichiers ci-dessus sous
`tessera-agent`. Après merge et redémarrage : le test de Serpent qui lit
`ci.yml` passe sous le compte, et une écriture de l'agent sur ce fichier reste
refusée.

## Ce que ça ne fait pas

- Ne change pas la liste des fichiers protégés.
- Ne retouche pas les refus déjà posés dans un worktree existant : chaque run
  pose les siens à la création de son worktree.
