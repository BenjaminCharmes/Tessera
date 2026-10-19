---
agent: codeur
created: 2026-10-19
depends_on: []
estimated_days: 0.5
id: ticket-526
pr_number: 576
priority: medium
status: done
title: A run whose diff leaves two ticket files with the same id is sent back to its
  producer before review
type: fix
---

# ticket-526 — Un run qui laisse deux fiches au même identifiant repart au producteur avant la revue

## Objectif
Qu'aucun run ne livre un ticket dont l'identifiant est déjà pris, quel que
soit l'agent qui l'a écrit.

## Contexte
Le 19/10, le ticket-494 (type `design`, rôle `architect`) a créé ses tickets de
suite avec `Write`. Il a d'abord pris les numéros 515 à 518, déjà utilisés
(515 et 516 `done`, 517 et 518 `todo`, en file), puis il a écrit des copies
numérotées de 521 à 524, en laissant les premières en `todo` avec le titre
« Superseded by… ». La PR #567 a été approuvée et mergée avec deux fiches
`ticket-517` et deux `ticket-518` en `todo`. Elles ont été retirées à la main
(PR #568) avant que la file n'atteigne le 517.

`backend/src/tessera/services/ticket_check.py` sait déjà détecter les doublons
(`_duplicate_problems`, `verifier_tickets`), mais il n'est appelé que par la
route `routers/tickets.py`, jamais par le pipeline.

## Solution proposée
- Après chaque tour de production (codeur ou architecte), et avant les tests,
  le pipeline appelle `verifier_tickets` sur le projet. Un problème
  (identifiant en double, valeur de frontmatter invalide, dossier ≠ statut)
  renvoie le tour au producteur, avec la liste des problèmes dans son
  contexte, comme des tests rouges. Le tour suivant corrige.
- Une ligne de journal `[ticket-XXX] tickets: <n> problème(s) — <détail court>`.
- `agents/prompts/architect.md` : prendre le numéro suivant le plus grand
  existant, tous dossiers confondus, juste avant d'écrire chaque fiche, et ne
  jamais laisser une fiche « remplacée » : la supprimer.

## Critères d'acceptation
- [ ] Un test vérifie qu'un tour de production qui laisse deux fiches au même `id` est renvoyé au producteur avec un message qui nomme l'identifiant et les deux chemins
- [ ] Un test vérifie qu'un tour sans problème de tickets n'est pas affecté
- [ ] La ligne de journal `tickets: … problème(s)` est écrite quand un problème est trouvé (un test le vérifie)
- [ ] `agents/prompts/architect.md` demande de prendre le numéro suivant le plus grand, tous dossiers confondus, et de supprimer une fiche remplacée
- [ ] Les tests existants de `ticket_check` passent sans modification de leurs assertions

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Ne vérifier que les tickets du projet du run : un doublon ancien, hors du
diff, ne doit pas bloquer un run qui n'y touche pas. Comparer avec l'état
avant le tour.