---
id: ticket-084
title: "Refermer la boucle : de l'issue au merge"
type: feat
status: done
pr_number: null
priority: high
agent: codeur
depends_on: [ticket-083]
estimated_days: 1
created: 2026-09-18
---

# ticket-084 — De l'issue au merge

## Pourquoi

Ticket-083 a branché la livraison sur **un seul** endroit : le run unique.
C'est le mode où l'utilisateur est déjà devant son écran — donc celui où
l'absence de clic compte le moins. Une file de dix tickets n'en livrait aucun.

Et la boucle ne se refermait pas : la PR partait, elle était mergée, l'issue
d'origine restait ouverte.

## Objectif

Rendre la chaîne complète : une issue écrite sur GitHub devient un ticket,
le ticket devient une PR, la PR referme l'issue.

## Critères d'acceptation

- [x] La livraison est appelée depuis `run_pipeline` : elle vaut donc pour les
      trois modes — unique, file, autonome
- [x] L'orchestrateur ne sait pas ce qu'est une livraison : il appelle un
      rappel que le routeur fabrique, et reste ignorant de GitHub
- [x] Le corps de la PR porte `Closes #N` quand le ticket vient d'une issue
- [x] Le titre et le corps de la PR viennent du ticket, plus de son seul
      identifiant
- [x] Un run autonome peut tirer les issues `agent-ready` avant de démarrer
- [x] Il ne le fait **pas** sans qu'on le demande : un appel réseau vers le
      dépôt d'un client ne part pas de lui-même

## Ce que ça ne fait pas

Le mode autonome n'a pas de surface dans l'UI — c'est la file de tickets qui y
tient ce rôle, et elle livre désormais. `depuis_github` n'est donc accessible
que par l'API.
