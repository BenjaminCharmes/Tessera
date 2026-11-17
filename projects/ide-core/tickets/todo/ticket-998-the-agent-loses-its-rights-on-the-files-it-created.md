---
id: ticket-998
title: "Design: the agent account loses its rights on the files it created at the end of a call"
type: design
status: todo
priority: high
agent: architect
depends_on: []
---

## Signalement

- Audit sans contexte du 17/11, constat H3 (HIGH), plus M3.

## Contexte

`droits_worktree.retirer_ecriture` ne fait que `/remove:g` sur la racine et
sur `.git`. Les fichiers et dossiers créés par l'agent lui appartiennent : il
garde le droit implicite de réécrire leur DACL, et peut leur poser une DACL
protégée qui ne dépend plus de l'héritage. Avec le contournement du contrôle
de traversée et des chemins prévisibles, un agent d'un autre projet (même
compte) peut modifier ces fichiers entre la revue et le commit, ou pendant
qu'un appel d'un autre projet tourne.

M3 : le profil du compte est commun à tous les appels et projets et n'est
jamais remis à zéro : `HKCU\…\Command Processor\AutoRun`, `~/.bashrc`,
`~/.npmrc`, `%APPDATA%\uv\uv.toml`, `.pth` du site-packages utilisateur sont
autant de points de persistance d'un appel à l'autre.

## Ce qu'il faut décider

- En fin d'appel : reprendre la propriété des fichiers créés par l'agent
  (`icacls /setowner` vers le compte du backend, puis `/reset`), ou une ACE
  `OWNER RIGHTS` qui retire au propriétaire ses droits implicites ; coût sur
  un `node_modules` de 8 000 fichiers (mesuré : grant + remove ≈ 2,5 s).
- Un compte agent par projet, ou un verrou qui interdit deux appels sous le
  compte en même temps.
- Profil de l'agent : remise à zéro des points de persistance avant chaque
  appel, ou profil jetable.
- Écrire les tickets de réalisation.

## Ce que ça ne fait pas

- Ne traite pas le bureau partagé : c'est le ticket-944.
