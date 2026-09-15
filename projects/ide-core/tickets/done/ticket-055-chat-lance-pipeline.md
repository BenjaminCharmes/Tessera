---
id: ticket-055
title: "Lancer un pipeline depuis la conversation"
type: feat
status: done
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

- [x] L'agent peut suggérer un lancement ; il ne peut pas le déclencher
- [x] La suggestion apparaît comme une action explicite dans l'UI
- [x] Le résumé de conversation atteint le codeur, borné en taille
- [x] L'avancement du run est visible dans le fil de la conversation
- [x] Un second lancement concurrent sur le même projet est refusé, avec un
      message qui dit pourquoi
- [x] Aucun nouvel outil d'écriture n'est donné à l'agent du chat
- [x] `uv run pytest -q`, `uv run mypy src/`, `npx tsc --noEmit` verts

## Dépendances

`ticket-048`.

## Estimation

**2j**.

## Risques

- **Moyen** — le couplage chat ↔ pipeline touche deux flux WebSocket distincts.
  Mitigation : le chat s'abonne au flux existant de l'orchestrateur plutôt que
  d'en créer un second.

## Livré

| Couche | Contenu |
|---|---|
| `chat_suggestion.py` | Marqueur, résumé borné, verrou par projet |
| `chat_service.py` | Extrait la suggestion, retire le marqueur du texte affiché |
| `routers/chat.py` | `POST /projects/{id}/chat/run` |
| `agents/prompts/chat.md` | Le protocole de suggestion |
| Frontend | Bouton, suivi du run, résultat dans le fil |

### Le protocole

L'agent termine sa réponse par `SUGGESTION_PIPELINE: ticket-XXX`. C'est un
protocole entre l'agent et l'UI, retiré du texte affiché — l'utilisateur voit
un bouton. L'identifiant est **validé** contre `^ticket-[a-z0-9-]{1,40}$` : le
marqueur vient d'un agent et ne doit pas pouvoir injecter un chemin relatif.

### Défaut trouvé par les tests

Le verrou était pris **après** la construction de l'orchestrateur : un refus
coûtait le chargement complet du projet et des providers pour rien. Il est
désormais pris en premier.

### Le résumé tronque par le début

Les décisions qui comptent sont celles auxquelles la conversation a abouti, pas
celles par lesquelles elle a commencé.
