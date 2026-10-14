---
agent: codeur
created: 2026-10-14
depends_on: []
estimated_days: 0.5
id: ticket-433
pr_number: null
priority: medium
status: done
title: One command checks every ticket file of a project the way the loader reads
  it, and names the file and field that fail
type: feat
---

# ticket-433 — Valider les tickets d'un projet avant de les committer

## Objectif

Savoir avant de committer des tickets écrits à la main que le projet se
chargera encore, et lequel corriger sinon.

## Contexte

Signalement de vigie, 2026-10-14 (récupéré, voir ticket-430) : pour poser
12 tickets (vigie 043-054), la session a écrit un script qui instancie
`tessera.models.ticket.Ticket` sur chaque fichier, en convertissant
`created` que YAML lit comme une date. Une valeur hors enum dans un
frontmatter fait échouer le chargement de tout le projet (skill
`new-ticket`).

## Solution proposée

- Une fonction `verifier_tickets(racine_projet) -> list[Probleme]` qui lit
  `tickets/**/ticket-*.md` exactement comme le chargeur (`TicketService`),
  et rend pour chaque fichier fautif : chemin, champ, valeur, message. Elle
  signale aussi un fichier rangé dans un dossier qui ne correspond pas à
  son `status`, et deux fichiers portant le même `id`.
- `GET /api/v1/projects/{id}/tickets/check` renvoie cette liste (vide si
  tout va bien).
- `make check-tickets PROJET=<id>` et
  `.\scripts\tessera.ps1 check-tickets <id>` l'appellent et sortent en
  erreur s'il y a un problème.

## Critères d'acceptation

- [ ] Un test vérifie qu'un `type` hors enum est signalé avec le chemin du
      fichier et le champ
- [ ] Un test vérifie qu'un `created` lu par YAML comme une date est accepté
- [ ] Un test vérifie qu'un fichier dans `todo/` avec `status: done` est
      signalé
- [ ] Un test vérifie que deux fichiers de même `id` sont signalés
- [ ] Un test vérifie que `GET …/tickets/check` renvoie une liste vide sur un
      projet sain

## Dépendances

Aucune.