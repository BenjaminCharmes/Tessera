---
id: ticket-587
title: "Steps that work silently are no longer reported as a frozen agent"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-26
---

# ticket-587 — Les étapes silencieuses ne passent plus pour un agent figé

## Objectif
Que « un agent semble figé » redevienne une alerte qu'on lit : le 26/10,
Benjamin la recevait « très souvent », et elle était fausse à chaque fois.

## Contexte
La santé (`frontend/src/lib/santeAgent.ts`, ticket-549) passe à
`blocage_suspecte` après 3 min sans événement, et
`lib/notifications.ts` (`devientFige`) envoie alors la notification. Or
plusieurs étapes n'émettent rien pendant qu'elles travaillent. Silences
relevés le 26/10 sur la file ide-core (run `222833a0`) :

| Étape | Silence | Événements |
| --- | --- | --- |
| testeur | 9,4 min | `ticket_status_changed` → `test_result` |
| audit sécurité | 3,8 min | `security_audit_started` → `security_audit_done` |
| validateur (Ollama) | 5,7 et 6,0 min | `validation_started` → `validation_done` |
| documentation | 5,8 min | `documentation_started` → `doc_updated` |
| livraison (retest après rebase) | 8,3 min | `livraison_started` → `livraison_done` |

Soit trois à cinq fausses alertes par ticket. Seuls le codeur, l'architecte
et le reviewer émettent en continu pendant leur travail ; pour eux, 3 min de
silence reste un vrai signe. Les étapes silencieuses ont déjà leur propre
coupure côté backend (délai du testeur, `agent_silence_max_s`).

Le testeur n'a pas d'événement de départ (`postesDuRun.ts` le note) : on ne
sait pas, côté frontend, qu'il tourne.

## Solution proposée
- Backend : un événement `test_started` émis quand le testeur démarre, à côté
  de `test_result` (`backend/src/tessera/services/pipeline_stages.py`,
  `EventType` dans `pipeline_events.py`), ajouté aux types du frontend
  (`types/api.ts`) et à l'alignement des types (`backend/tests/test_event_types_alignment.py`).
- Frontend : `santeAgent` reçoit l'information « étape silencieuse en
  cours » (testeur démarré sans `test_result`, ou `etape` parmi `securite`,
  `validation`, `documentation`, `livraison`) et rend alors `attente`, jamais
  `blocage_suspecte`, quelle que soit la durée — comme `external_wait`
  aujourd'hui. Tous les appelants de `santeAgent` la passent.
- Le Bureau peut montrer le testeur occupé entre `test_started` et
  `test_result` (`postesDuRun.ts`) : la donnée existe enfin (ADR-058).

## Critères d'acceptation
- [ ] Le backend émet `test_started` avant de lancer les tests du testeur ; un test du pipeline le vérifie, et `test_event_types_alignment.py` reste vert
- [ ] Entre `test_started` et `test_result`, 10 min sans événement donnent `attente` et non `blocage_suspecte` ; un test de `santeAgent` le vérifie
- [ ] Avec `etape` à `validation`, `securite`, `documentation` ou `livraison`, 10 min sans événement donnent `attente` ; un test le vérifie pour chacune
- [ ] Après `agent_started` du codeur, 4 min sans événement donnent toujours `blocage_suspecte` ; un test le vérifie
- [ ] Aucune notification « un agent semble figé » n'est émise pendant une étape silencieuse ; un test de `notifications.ts` le vérifie
- [ ] Dans `postesDuRun.ts`, le poste du testeur est occupé entre `test_started` et `test_result` ; un test le vérifie
