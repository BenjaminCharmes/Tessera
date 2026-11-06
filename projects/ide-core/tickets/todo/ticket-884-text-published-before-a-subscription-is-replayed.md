---
id: ticket-884
title: "Text published before a subscription is replayed on the observation socket, and a test proves it"
type: test
status: todo
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-11-06
---

# ticket-884 — Text published before a subscription is replayed on the observation socket, and a test proves it

## Objectif

Prouver par des tests que le texte d'un agent publié avant l'abonnement d'un client lui est rejoué, dans l'ordre.

## Contexte

Trouvé par l'essai de seconde revue (ticket-846, `docs/essais/seconde-revue.md`) : le reviewer l'a relevé sur un commit classé sain, un humain l'a confirmé, et le défaut est toujours sur `develop` le 06/11. Entrée s10, ticket-185.

`backend/tests/test_journal_du_texte.py` ne teste que `JournalDuTexte` seul. Rien ne vérifie que `EventHub.publier` alimente `JOURNAL_DU_TEXTE`, ni que `backend/src/tessera/routers/observation.py` le relit à l'abonnement ; `test_un_abonne_recoit_les_tokens_de_son_run` (`backend/tests/test_canal_d_observation.py`) n'affirme que `pipeline_done`.

## Solution proposée

Deux tests. Si l'un échoue sur le code actuel, corriger le code dans ce ticket.

## Critères d'acceptation

- [ ] Un test de `backend/tests/test_canal_d_observation.py` publie deux `agent_token` d'un run, puis un client envoie `{"subscribe": run_id}` et reçoit les deux textes dans l'ordre de publication.
- [ ] Un test vérifie qu'`EventHub.publier` ajoute le texte à `JOURNAL_DU_TEXTE` même quand la file d'un abonné est pleine.

## Dépendances

Aucune.

## Estimation

Une demi-journée au plus.

## Ce que ça ne fait pas

Ne revoit pas le reste du ticket d'origine : seulement le défaut confirmé.
