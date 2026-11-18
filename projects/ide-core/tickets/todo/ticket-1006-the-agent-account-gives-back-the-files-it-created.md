---
id: ticket-1006
title: "The agent account gives back the files it created at the end of its last call"
type: fix
status: todo
priority: high
agent: codeur
depends_on: []
preuve_reelle: true
---

## Signalement

- Suite du ticket-998 (ADR-087), constat H3 de l'audit du 17/11.

## Ce qu'il faut faire

Dans `services/providers/droits_worktree.py` et `droits_appel.py` :

- `poser_ecriture` ajoute, en plus de l'existant, une ACE héritable
  `*S-1-3-4:(OI)(CI)(RC)` (OWNER RIGHTS, lecture des droits seulement) et
  `<compte du backend>:(OI)(CI)F`. Le propriétaire d'un fichier créé par l'agent
  n'a alors plus `WRITE_DAC` ni `WRITE_OWNER` ; le backend garde la main.
- `retirer_ecriture` : après le `/remove:g` existant, **seulement à la fin du
  dernier appel sur la racine**, `icacls <racine> /setowner <backend> /T /C /L`
  puis `icacls <racine> /reset /T /C /L`, `.git` compris. Puis ré-appliquer le
  `/inheritance:d` + `RX` du `.git` que `/reset` aurait rétabli, **ou** exclure
  `.git` du `/reset` : choisir et le dire dans la docstring.
- Un code de sortie non nul (fichier à DACL protégée posée à la création, que
  le backend ne peut pas reprendre) lève `DroitsAgentRefuses` : le run passe en
  `blocked` (ADR-037). Pas de repli, pas de `/grant` forcé.
- Le lanceur `icacls` reste injectable : les tests passent un faux.

## Critères d'acceptation

- [ ] Avec un faux `Icacls`, `poser_ecriture` émet l'ACE OWNER RIGHTS `(RC)` et l'ACE du backend.
- [ ] `clore_appel` émet `/setowner` puis `/reset` une seule fois, au dernier appel d'une racine, pas aux appels intermédiaires.
- [ ] Un code non nul sur `/setowner` ou `/reset` lève `DroitsAgentRefuses`.
- [ ] Le `.git` du worktree est en lecture seule pour le compte après la remise à l'héritage.
- [ ] Sans `AGENT_USER`, rien n'est émis.

## Preuve réelle

À lancer sur le poste, sous `AGENT_USER` : faire créer à un appel un fichier,
puis lui faire poser une DACL protégée par `icacls /inheritance:r` — le constater
refusé (accès refusé, grâce à l'ACE OWNER RIGHTS). Créer ensuite un fichier avec
une DACL explicite via un script, finir l'appel : constater que le run est
`blocked` avec `DroitsAgentRefuses` nommé, et que `icacls <fichier>` d'un fichier
ordinaire montre le backend propriétaire et la DACL héritée. Mesurer la durée de
`clore_appel` sur un worktree avec un `node_modules` de ~8 000 fichiers (attendu :
quelques secondes) et la noter dans le ticket.

## Ce que ça ne fait pas

- Ne traite pas le profil (ticket-1008) ni la concurrence (ticket-1007).
- Ne ferme pas une DACL posée par l'agent à la création même du fichier : elle se
  constate à la fin de l'appel et bloque le run, elle ne s'empêche pas.
