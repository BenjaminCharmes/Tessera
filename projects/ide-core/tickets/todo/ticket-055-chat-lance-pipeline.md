---
id: ticket-055
title: "Lancer un pipeline depuis la conversation"
type: feat
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: [ticket-048]
estimated_days: 2
created: 2026-09-15
---

# ticket-055 — Chat v2 : lancer un pipeline depuis la conversation

## Objectif

Passer de la discussion à l'exécution sans quitter le chat, en transmettant au
pipeline ce qui a été décidé dans la conversation.

## Contexte

[ticket-048](../done/ticket-048-chat-agent-ide.md) a livré le chat en
restreignant volontairement ses outils : lire, écrire, chercher. Le lancement
de pipeline a été reporté en v2, pour livrer d'abord la cohabitation git
(ADR-019) sans y ajouter le risque d'un déclenchement automatique.

Le manque se ressent : on discute d'un besoin, on aboutit à un ticket, puis il
faut changer d'onglet, retrouver le ticket, cliquer — et surtout **tout le
raisonnement de la conversation est perdu**. Le codeur reçoit le ticket nu.

## Solution proposée

1. **Le chat propose, l'utilisateur dispose.** L'agent n'a pas d'outil qui
   lance un pipeline : il émet une *suggestion* que l'UI rend sous forme de
   bouton. Un agent conversationnel qui déclenche seul l'écriture de plusieurs
   fichiers sur un dépôt est exactement ce que ticket-048 a refusé.
2. **Transmettre le contexte de la discussion** au pipeline, en plus du ticket :
   un résumé de la conversation, borné en taille, injecté dans le contexte
   projet du codeur.
3. **Suivre le run dans le fil** — l'onglet Chat affiche l'avancement plutôt que
   de forcer un aller-retour vers l'Agent Stream.
4. **Un seul run à la fois par projet**, et refus explicite si un run est déjà
   en cours : deux pipelines concurrents sur le même dépôt violeraient
   l'isolation par branche d'ADR-018.

## Critères d'acceptation

- [ ] L'agent peut suggérer un lancement ; il ne peut pas le déclencher
- [ ] La suggestion apparaît comme une action explicite dans l'UI
- [ ] Le résumé de conversation atteint le codeur, borné en taille
- [ ] L'avancement du run est visible dans le fil de la conversation
- [ ] Un second lancement concurrent sur le même projet est refusé, avec un
      message qui dit pourquoi
- [ ] Aucun nouvel outil d'écriture n'est donné à l'agent du chat
- [ ] `uv run pytest -q`, `uv run mypy src/`, `npx tsc --noEmit` verts

## Dépendances

`ticket-048`.

## Estimation

**2j**.

## Risques

- **Moyen** — le couplage chat ↔ pipeline touche deux flux WebSocket distincts.
  Mitigation : le chat s'abonne au flux existant de l'orchestrateur plutôt que
  d'en créer un second.
