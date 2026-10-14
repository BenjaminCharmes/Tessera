---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-444
pr_number: 449
priority: medium
status: done
title: A queue's status tells the approved tickets from the ones that ended without
  approval
type: fix
---

# ticket-444 — Le statut d'une file distingue l'approuvé du bloqué

## Objectif

Qu'en lisant `GET /api/v1/runs/{run_id}`, on sache quels tickets de la file
ont réellement été approuvés et livrés, et lesquels se sont arrêtés.

## Contexte

Signalé par la session carrière le 2026-10-14 : sa file 068-077 a vu le
ticket-071 se bloquer (« testeur: délai dépassé deux fois », travail commité
en « unapproved work », sans PR) ; `GET /runs/{id}` (ticket-431,
`routers/runs.py`) l'a pourtant rangé dans `faits`, avec les tickets
approuvés. Lu par une session qui suit sa file, cela fait croire que 071 est
livré.

## Solution proposée

- La réponse sépare : `approuves` (fin approuvée), `arretes` (bloqué,
  non approuvé, interrompu — avec le motif court quand il est connu),
  `restants`, `ticket_courant`.
- `faits` reste présent, déprécié, égal à `approuves` + `arretes`, pour ne
  pas casser un appelant existant ; `docs/api.md` le dit.

## Critères d'acceptation

- [ ] Un test vérifie qu'une file où un ticket est approuvé et un autre
      bloqué renvoie le premier dans `approuves` et le second dans `arretes`
      avec son motif
- [ ] Un test vérifie qu'un ticket interrompu (redémarrage) est dans
      `arretes`
- [ ] Un test vérifie qu'un ticket coupé avant d'avoir produit un commit
      (limite de session, `session_limit` : resté `todo`, sans commit) est
      dans `restants`, ni dans `approuves` ni dans `arretes` — cas signalé
      par affût le 2026-10-14 sur le ticket-073
- [ ] Un test vérifie que `faits` vaut toujours l'union des deux listes
- [ ] `docs/api.md` décrit `approuves`, `arretes` et la dépréciation de `faits`

## Dépendances

Aucune.