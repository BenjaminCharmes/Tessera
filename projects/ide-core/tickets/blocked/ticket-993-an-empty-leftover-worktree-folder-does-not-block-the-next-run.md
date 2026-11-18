---
agent: codeur
depends_on: []
id: ticket-993
priority: medium
status: blocked
title: An empty leftover worktree folder does not block the next run
type: fix
---

## Contexte

17/11, Serpent ticket-009 sous `tessera-agent` : le run `02d9b72d` finit
`blocked` à 09:14 UTC ; son worktree est supprimé, mais le dossier
`C:\ProgramData\Tessera\worktrees\serpent\ticket-009` reste, **vide**, et git
ne le connaît plus. Le run suivant (`cdde95f4`, 11:52 UTC) s'arrête en 43 ms :
`… ticket-009 existe mais n'est pas le worktree de « ticket-009-… »`
(`worktrees/run_worktree.py`, `_reprendre`). Il a fallu le retirer à la main.

La cause du dossier restant n'a pas pu être lue : le journal du backend est
réécrit à chaque démarrage. Hypothèse : `git worktree remove` vide le dossier
mais ne peut pas le supprimer (poignée encore ouverte par un processus du
compte agent au moment de la clôture), et `supprimer` n'y revient pas.

## Ce qu'il faut faire

- Dans `_reprendre` : un dossier existant qu'aucun worktree n'enregistre et
  qui est **vide** (aucune entrée) est supprimé (`rmdir`, jamais récursif),
  journalisé (`run_worktree_dossier_vide_retire`), et la création continue.
  Un dossier non vide reste un refus, comme aujourd'hui (ADR-037).
- Dans `supprimer` : après `git worktree remove` ou la suppression étendue,
  si le dossier existe encore et est vide, une seconde tentative de `rmdir`
  après une courte attente ; un échec se journalise
  (`run_worktree_dossier_restant`) sans lever.

## Critères d'acceptation

- [ ] Test sur dépôt réel : dossier vide non enregistré à la place du
      worktree — le run crée son worktree, le journal le dit.
- [ ] Test : dossier non vide non enregistré — refus inchangé, rien n'est
      supprimé.
- [ ] Test : `supprimer` qui laisse un dossier vide le retire au second essai.

## Ce que ça ne fait pas

- Ne supprime jamais un dossier qui contient quoi que ce soit, même un
  fichier ignoré par git.
- Ne cherche pas quel processus tenait le dossier.