---
id: ticket-1013
title: "A refused closure of an agent call is never swallowed"
type: fix
status: todo
pr_number: null
priority: high
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-11-19
---

## Signalement

- Audit sans contexte du 19/11, constat H2, vérifié par lecture.

## Contexte

Une clôture d'appel qui échoue lève `DroitsAgentRefuses` : processus du
compte encore vivant, profil non nettoyé, droit non retiré. Le run doit alors
finir `blocked` (ADR-037). Deux endroits rattrapent `Exception` et continuent :

- `services/pipeline/etape_de_capture.py`, `_arreter` : l'arrêt de l'app du
  contrôle visuel devient un simple avertissement, et le run continue vers la
  livraison.
- `services/providers/agent_sdk.py`, `_run_ou_reprendre` : un échec de la
  reprise de session relance un appel neuf, même quand l'échec est un refus
  de clôture.

## Ce qu'il faut faire

- Dans les deux fonctions, `DroitsAgentRefuses` remonte telle quelle. Les
  autres exceptions gardent leur traitement actuel.
- Ne rien changer d'autre à l'étape de capture ni au repli de reprise.

## Critères d'acceptation

- [ ] Test : `_arreter` de `etape_de_capture.py`, avec une app dont
  `arreter()` lève `DroitsAgentRefuses`, laisse remonter l'exception.
- [ ] Test : `_arreter`, avec une app dont `arreter()` lève `RuntimeError`,
  journalise et ne lève rien, comme aujourd'hui.
- [ ] Test : `_run_ou_reprendre` de `agent_sdk.py`, quand la reprise lève
  `DroitsAgentRefuses`, la laisse remonter sans lancer d'appel neuf.
- [ ] Test : `_run_ou_reprendre`, quand la reprise lève une autre exception,
  lance toujours l'appel neuf.

## Ce que ça ne fait pas

- Ne cherche pas d'autres `except Exception` dans le dépôt : seuls ces deux
  chemins portent une clôture d'appel.
