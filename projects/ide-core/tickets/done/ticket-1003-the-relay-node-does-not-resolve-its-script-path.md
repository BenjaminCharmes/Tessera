---
agent: codeur
depends_on:
- ticket-992
id: ticket-1003
preuve_reelle: true
priority: high
status: done
title: The relay node does not resolve its script path under the agent account
type: fix
---

## Contexte

Preuve réelle du 18/11 (Serpent ticket-009, run `ba1cf4e5`, après le
redémarrage qui active 994, 995 et 996) : préparation sous `tessera-agent`
(995 prouvé : `node_modules` appartient au compte), 20 tests verts sous le
compte (994 prouvé), puis `securite: BLOCK — Audit sécurité indisponible :
Command failed with exit code 1`. Le run finit `blocked` avec son commit,
comme il le doit (ADR-039).

Le stderr de l'appel n'est pas journalisé. Rejoué à la main sous le compte,
avec le lanceur du backend et `avec_stderr=True`, le relais du ticket-992
rend :

```
Error: EPERM: operation not permitted, lstat 'C:\Users\<profil>\AppData'
    at Object.realpathSync (node:fs)
    at resolveMainPath (node:internal/modules/run_main)
```

Le dossier d'appel (`tempfile.mkdtemp`) vit dans le TEMP de l'utilisateur.
Le compte de l'agent n'a aucun droit sur ce profil (ticket-994), mais ouvre un
fichier par son chemin complet. node, lui, résout le chemin réel de son script
principal en examinant chaque dossier parent. Le CLI lancé directement
(`--version`, sans relais) rend 0 sous le compte : seul le relais échoue.

## Ce qui change

`relayer_si_trop_long` lance `node --preserve-symlinks-main relais.js
relais.json` : node ne résout plus le chemin du script, il l'ouvre. Rejoué sous
le compte, la même commande rend 0.

## Critères d'acceptation

- [x] La commande relayée porte `--preserve-symlinks-main` avant le script
  (`test_long_command_is_relayed_through_files`).
- [x] Sous `tessera-agent`, le relais d'une commande de plus de 1 024
  caractères rend le code du CLI, et non une erreur EPERM de node (rejoué à la main le 18/11).

## Preuve réelle

Après redémarrage : relancer Serpent ticket-009 sous le compte agent. L'audit
sécurité doit rendre un verdict, et pas « indisponible ».

## Ce que ça ne fait pas

- Ne journalise pas le stderr d'un appel d'agent qui échoue : c'est ce qui a
  masqué la cause (« Check stderr output for details »). Relevé pour l'audit
  sans contexte.
- Ne déplace pas le dossier d'appel hors du profil de l'utilisateur.
