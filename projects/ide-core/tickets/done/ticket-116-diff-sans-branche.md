---
id: ticket-116
title: "Relire le diff d'un ticket dont la branche a été supprimée"
type: fix
status: done
pr_number: 133
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-21
---

# ticket-116 — Relire le diff d'un ticket dont la branche a été supprimée

## Objectif

Que le diff d'un ticket reste consultable après le nettoyage de sa branche.

## Contexte

`diff_du_ticket` retrouve le travail par sa branche :

```
git branch --list "{ticket_id}-*"
```

Une branche **locale**. Or la supprimer après le merge est la pratique
normale : c'est ce que fait `gh pr merge --delete-branch`, que le skill
`ticket-workflow` prescrit.

Conséquence : le diff est perdu pour **tout ticket proprement terminé**.
L'écran affiche « ce ticket n'a jamais été lancé — aucune branche ne lui
correspond », ce qui est faux et trompeur : le ticket a bien été lancé, c'est
sa branche qui n'existe plus. Le travail, lui, est toujours dans l'historique.

Le défaut est structurel, pas accidentel : il apparaît au premier nettoyage de
branches, et le ticket-069 qui a créé cet écran voulait précisément permettre
de « juger un run sans ouvrir VSCode ».

## Solution proposée

Quand aucune branche ne correspond, chercher le **commit** : les messages
portent tous l'identifiant du ticket (`feat: ticket-116 — …`), y compris après
un squash.

Plusieurs commits peuvent le mentionner — celui du travail, puis celui de
clôture. Le second ne touche que `tickets/`, que `_ARTEFACTS` exclut déjà :
son diff est donc **vide** après exclusion. Il suffit de parcourir les commits
du plus récent au plus ancien et de rendre le premier dont le diff n'est pas
vide.

`TicketDiff` gagne un champ `commit`. L'écran ne dit « jamais lancé » que
lorsque ni branche ni commit n'existe.

## Critères d'acceptation

- [ ] Un ticket dont la branche a été supprimée mais dont le commit existe
      rend son diff, et le champ `commit` est renseigné
- [ ] La branche reste prioritaire quand elle existe : un run en cours se
      relit sur sa branche, pas sur un commit passé
- [ ] Un commit de clôture, qui ne touche que des artefacts, n'est pas rendu
      comme s'il était le travail
- [ ] Un ticket réellement jamais lancé rend toujours `branch` et `commit` nuls
- [ ] L'écran ne dit « jamais lancé » que dans ce dernier cas
- [ ] `.\scripts\tessera.ps1 verify` est vert de bout en bout

## Ce que ça ne fait pas

Ne va pas chercher le diff sur GitHub. La suite de tests doit tourner hors
ligne, et l'historique local suffit — il contient le commit dès que la branche
a été mergée puis récupérée.

Ne reconstitue pas l'historique d'un ticket réécrit : si le message de commit
ne porte pas l'identifiant, rien ne le relie au ticket.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Chercher par message de commit repose sur une convention — le type et
l'identifiant en tête — que `CLAUDE.md` impose et que le pipeline applique.
Un commit écrit à la main sans cet identifiant restera introuvable ; c'est le
prix d'une recherche qui n'exige aucune donnée supplémentaire dans le ticket.
