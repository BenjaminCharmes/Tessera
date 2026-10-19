---
id: ticket-506
title: "The Resend verification step reports a verification already under way instead of offering to launch it again"
type: fix
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: []
estimated_days: 0.5
created: 2026-10-19
---

# ticket-506 — L'étape resend_verify dit qu'une vérification est en cours au lieu de proposer de la relancer

## Objectif
Qu'un dry-run de mise en ligne montre l'état réel de la vérification Resend
d'un domaine, pour que l'utilisateur sache s'il doit attendre ou agir.

## Contexte
Le 19/10, sur Devinoo, la vérification avait été lancée et le domaine était
`partially_verified` (MX et TXT d'envoi en propagation). Le dry-run affichait
pourtant « verification is to be launched » : `ResendVerifyStep.inspect`
(`backend/src/tessera/services/provisioning/resend_steps.py`) ne regarde que
`verified` et `dns_published`, jamais le statut du domaine. `apply`, lui,
passe déjà par `_from_status`.

## Solution proposée
Dans `inspect`, une fois les DNS publiés : un domaine au statut
`not_started` (ou sans statut) reste `TODO` « verification is to be
launched » ; tout autre statut passe par `_from_status`, comme `apply`
(`pending`, `partially_verified`, `temporary_failure` → `PENDING` ;
`failed` → `FAILED`). Aucun appel d'écriture à Resend dans `inspect`.

## Critères d'acceptation
- [ ] Dans `resend_steps.py`, `ResendVerifyStep.inspect` renvoie `PENDING` pour un domaine au statut `partially_verified` dont les DNS sont publiés, avec un détail qui contient `partially_verified`
- [ ] `inspect` renvoie `FAILED` pour un domaine au statut `failed`
- [ ] `inspect` renvoie toujours `TODO` « verification is to be launched » pour un domaine au statut `not_started`
- [ ] `inspect` n'appelle jamais `verify_domain` (un test le vérifie avec un faux client)
- [ ] Les trois cas sont couverts par des tests dans `backend/tests/test_provisioning_resend.py`

## Dépendances
Aucune.

## Estimation
Une demi-journée.

## Risques
Le statut lu par `find_domain` (liste) peut différer de celui de
`get_domain` : vérifier que la liste porte bien le statut, sinon relire le
domaine comme le fait déjà `_ask_dns`.
