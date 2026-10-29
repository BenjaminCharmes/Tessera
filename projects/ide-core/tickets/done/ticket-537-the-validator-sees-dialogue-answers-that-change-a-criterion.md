---
agent: codeur
created: '2026-10-22'
depends_on: []
id: ticket-537
priority: medium
status: done
title: Le validateur ignore une réponse du dialogue qui change le sens d un critère,
  et le run se bloque
type: feat
---

## Signalement

- Projet source : kadoomi
- Nature : idee
- Reçu le : 2026-10-22

## Description

Run d10b5e00 (kadoomi, ticket-088, 22/10). Au tour 1, le codeur pose une question (agent_question) : le critère 2 demande un 404, mais un 404 distinct ferait oracle et casserait le toast Annuler ; il propose A (404) ou B (état vide). La session du projet répond B. Le codeur implémente B ; reviewer APPROVED, audit PASS, tests verts. Mais le validateur ne voit que le texte du ticket et refuse le critère 2 trois tours de suite : run blocked, ticket fini à la main. Un interject demandant au codeur de reformuler le critère dans le fichier du ticket est arrivé trop tard. Gain attendu : un run qui suit une décision prise au dialogue ne se bloque pas sur un texte périmé.

## Contexte

Pistes : joindre au validateur les questions et réponses du dialogue du run ; ou laisser le codeur proposer un amendement de critère (visible dans le diff du ticket), à confirmer par l humain au dialogue.

## Solution retenue (triage ide-core, 22/10)

`DialogueChannel` (`services/dialogue.py`) ne garde aucune trace des échanges :
`ask` attend une réponse, puis l'oublie. Il garde désormais la liste des
questions posées et des réponses **humaines** reçues pendant le run (pas les
hypothèses énoncées après un délai dépassé, ADR-025). `ValidatorService`
(`services/validator.py`) reçoit cette liste et, si elle n'est pas vide,
l'ajoute à son message dans une section « Décisions prises au dialogue
pendant le run », après les critères. `agents/prompts/validateur.md` dit
qu'un critère dont une réponse humaine a changé le sens se juge contre cette
réponse, et qu'il faut citer la réponse dans le verdict du critère.

## Critères d'acceptation

- [ ] `DialogueChannel` garde chaque question suivie de sa réponse humaine, dans l'ordre, et les expose ; un test le vérifie
- [ ] Une question restée sans réponse (délai dépassé) n'entre pas dans cette liste ; un test le vérifie
- [ ] `_build_user_message` de `services/validator.py` ajoute la section « Décisions prises au dialogue pendant le run » quand la liste n'est pas vide, et ne l'ajoute pas sinon ; un test couvre les deux cas
- [ ] L'orchestrateur passe au validateur les échanges du canal de dialogue du run ; un test vérifie, avec des doubles, qu'une réponse reçue au tour 1 arrive dans le message du validateur
- [ ] `agents/prompts/validateur.md` contient la règle : un critère dont une réponse humaine du dialogue a changé le sens se juge contre cette réponse, citée dans le verdict

## Ce que ça ne fait pas

- Ne modifie pas le fichier du ticket : le critère d'origine reste tel quel,
  et la décision vit dans le journal du run.
- Ne donne pas les échanges au reviewer.