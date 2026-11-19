---
agent: codeur
created: 2026-11-19
depends_on: []
estimated_days: 1
id: ticket-1015
pr_number: null
preuve_reelle: true
priority: high
status: blocked
title: The rights of a call are set on the run worktree, never on a folder found by
  walking up
type: fix
---

## Signalement

- Audit sans contexte du 19/11, constat C1.

## Contexte

`services/providers/droits_appel.py`, `racine_du_worktree` : la racine où le
droit du compte se pose est le premier dossier, en remontant depuis le
dossier de l'appel, qui contient un `.git`. Un agent peut créer un `.git`
dans un sous-dossier pendant un appel. Si l'appel suivant part de ce
sous-dossier (`pipeline.test_cwd`, `git_root: ancestor`), la racine devient
ce sous-dossier : le `/reset` de clôture (ticket-1006) y efface les refus
d'écriture des fichiers protégés, que `_REFUSES` ne repose que pour la vraie
racine.

Aujourd'hui aucun projet sous compte agent ne lance ses appels depuis un
sous-dossier : le défaut est latent.

Vérifié sur le poste le 19/11 : `icacls` sans `/L` sur une jonction modifie
la jonction, pas sa cible. La variante « jonction `.git` vers le profil de
l'utilisateur » de l'audit ne donne donc pas de droit sur la cible. Le `/L`
demandé ci-dessous reste une précaution.

## Ce qu'il faut faire

- La racine d'un appel est le dossier, en remontant, qui est un enfant
  direct de `<dossier des worktrees>/<projet>/` : le worktree du run. Plus
  aucune recherche de `.git`.
- Un `.git` de cette racine qui est un point de reparse (`lstat`, attribut
  `0x400`) lève `DroitsAgentRefuses`.
- Chaque appel `icacls` de `droits_worktree.py` porte `/L`.

## Critères d'acceptation

- [ ] Test : un dossier d'appel `<worktrees>/p/t/sous`, avec un `.git` créé
  dans `sous`, donne la racine `<worktrees>/p/t`.
- [ ] Test : un dossier d'appel hors du dossier des worktrees lève toujours
  `DroitsAgentRefuses` (ticket-999).
- [ ] Test (Windows, ignoré ailleurs) : un `.git` de la racine qui est une
  jonction lève `DroitsAgentRefuses`.
- [ ] Avec un faux `Icacls` : tous les appels émis par `poser_ecriture`,
  `retirer_ecriture` et `accorder_droits_agent` contiennent `/L`.

## Preuve réelle

Sous `AGENT_USER`, dans un worktree jetable de Serpent : créer `sous/.git`,
lancer un appel depuis `sous`, et constater que le droit est posé puis retiré
sur la racine du worktree, et qu'un fichier protégé de la racine garde son
refus d'écriture après la clôture.

## Ce que ça ne fait pas

- Ne change pas la règle du ticket-996 sur les liens dans l'arbre.