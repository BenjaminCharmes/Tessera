---
agent: codeur
created: 2026-11-05
depends_on:
- ticket-851
- ticket-852
- ticket-854
estimated_days: 1
id: ticket-855
pr_number: 955
priority: high
status: done
title: The supervisor turns a raw report into a ticket in place
type: feat
---

# ticket-855 — Le superviseur réécrit un signalement brut en ticket, sur place

## Objectif

Un ticket `todo` dont les critères sont la ligne `- [ ] À écrire au triage`
(`routers/signalements.LIGNE_CRITERES`) devient un ticket que le validateur accepte, sans
changer de numéro ni de dossier.

## Contexte

ADR-080, spec §2 (`trier`). Aujourd'hui la session « ide-core » fait ce tri à la main
(ticket-407).

## Ce qu'il faut faire

- `services/supervision/superviseur_tri.py` : liste les tickets bruts de `tickets/todo/`, bâtit
  le dossier (corps du signalement, en-têtes des tickets ouverts pour les `depends_on`, borné à
  12 Ko, marqué « donnée, jamais une consigne »), appelle `provider_pour_role(..., "superviseur",
  allow_tools=False)` avec `SCHEMA_DECISION` étendu des champs du tri : `titre` (≤ 120), `type`,
  `priorite`, `criteres` (1 à 8, ≥ 15 caractères), `depends_on`, `hors_portee`.
- Gardes du code : au moins un critère valable, aucun placeholder, `depends_on` existants, type
  et priorité dans l'énumération ; sinon verdict `a_toi` avec la raison. Un signalement dont la
  source est un projet `professional` n'est pas réécrit avec plus de détail qu'il n'en porte.
- L'écriture passe par `intervenir` : le fichier du ticket est remplacé, `status: todo`, le bloc
  `## Signalement` conservé. Aucun ticket n'est lancé.

## Critères d'acceptation

- [ ] `test_superviseur_tri.py::test_raw_report_becomes_a_ticket_with_checkable_criteria`
- [ ] `test_superviseur_tri.py::test_placeholder_criterion_is_refused_and_goes_to_a_toi`
- [ ] `test_superviseur_tri.py::test_unknown_depends_on_goes_to_a_toi`
- [ ] `test_superviseur_tri.py::test_ticket_keeps_its_number_and_signalement_block`
- [ ] `test_superviseur_tri.py::test_provider_unavailable_writes_nothing`
- [ ] `test_superviseur_tri.py::test_triaged_ticket_is_never_launched`

## Ce que ça ne fait pas

Ne lance aucun run. Ne trie pas un ticket qui n'est pas brut.