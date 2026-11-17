---
id: ticket-1001
title: "Low findings of the 17/11 audit: declared env, relaunch arguments, setup script, hooks"
type: fix
status: todo
priority: medium
agent: codeur
depends_on: []
preuve_reelle: true
---

## Signalement

- Audit sans contexte du 17/11, constats LOW retenus (L1, L4, L6, L9, L10) et
  la réserve relevée sur le ticket-973.

## Ce qu'il faut faire

- **L1** `verification/lancement_compte.py`, `env_du_code_de_projet.py` : un
  `extra` (`worktree.env`) est réappliqué après le filtre des secrets. Le
  filtrer aussi (noms du coffre, `*_TOKEN`, `*_KEY`…) et refuser qu'il porte
  `PATH` (ADR-086).
- **L4** `verification/relance_instable.py`, `_commande` : passer les fichiers
  à relancer après `--`, et refuser un nom qui commence par `-`.
- **L6** `scripts/agent-setup-admin.ps1` : créer le fichier de remise du mot
  de passe avec son ACL finale (héritage coupé) avant d'y écrire, pas après.
- **L9** `scripts/hooks/pre-push` : lancer `coffre_cli` depuis la racine de
  Tessera (`cwd` fixé), jamais depuis le dépôt poussé.
- **L10** `worktrees/dossier_agent.py` et `Test-DossierWorktreesAgent` :
  refuser un dossier des worktrees qui porte un droit hérité pour le compte
  agent ou pour `Users`.
- **Réserve 973** `creation_projet/hook_pre_push.py`,
  `projets_avec_run_ouvert` : une base illisible rend « aucun run ouvert » ;
  la commande doit alors refuser (code 1) plutôt que poser les hooks partout.

## Critères d'acceptation

- [ ] Un test par point ci-dessus (les scripts PowerShell : test qui lit le
      script et vérifie l'ordre des opérations).

## Ce que ça ne fait pas

- L2 (ports de Tessera), L3 (filtres git au `status`), L5 (caractères de
  l'identifiant dans `secrets_diff`), L8 (motif d'arrêt perdu au
  réalignement), L11 (historique local détaché) : notés, non retenus ici.
