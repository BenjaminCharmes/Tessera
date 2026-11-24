---
agent: codeur
depends_on: []
estimated_days: 1
id: ticket-1043
priority: medium
status: done
title: A tool-bearing call cannot skip the agent account
type: fix
---

# ticket-1043 — Un appel outillé ne peut pas contourner le compte agent

## Objectif

Rendre vérifiable l'exception d'ADR-093 : seul un appel sans aucun outil part
sous le compte de l'utilisateur dans un projet qui déclare
`worktree.compte_agent`. Aujourd'hui l'exception tient au seul fait que
`_sans_outils`, `documenteur_run.py` et `lecons_run.py` oublient
`compte_agent` ; rien ne l'impose à un futur rôle.

## Contexte

ADR-093 (ticket-1041). Dans `backend/src/tessera/services/providers/agent_sdk.py`,
`_build_options` reçoit `compte_agent`, `allowed_tools`, `skills`, `plugins` et
`signaler`. Le `serveur_tessera` n'expose `signaler` qu'aux rôles outillés
(`outille=allowed_tools != []`).

## Ce qu'il faut faire

- Quand le projet déclare `worktree.compte_agent` (et `AGENT_USER` est
  renseigné) et que l'appel n'a pas `compte_agent=True`, `_build_options`
  (ou `provider_pour_role`, à l'endroit où le projet est connu) lève
  `ProviderIndisponible` si `tools` n'est pas `[]`, ou si `skills`, un plugin
  ou `signaler` est présent.
- Sans `AGENT_USER`, ou sans `worktree.compte_agent` : aucun changement.
- Les quatre rôles sans outils (validateur, doc-technique, doc-fonctionnelle,
  leçons) continuent de passer.

## Critères d'acceptation

- [ ] Un appel outillé sans compte, dans un projet à `compte_agent`, lève
      `ProviderIndisponible` ; un test le montre pour `tools` non vide, pour
      un skill et pour `signaler`.
- [ ] Un appel `allow_tools=False` passe sans compte, avec `AGENT_USER`
      renseigné.
- [ ] Sans `AGENT_USER` ou sans `compte_agent` déclaré, les tests existants
      passent sans changement.

## Ce que ça ne fait pas

- Ne fait passer aucun rôle sans outils par le compte (ADR-093).
- Ne touche ni `agents.json` ni la configuration des tests.

## Risques

Un rôle outillé que le code appelle aujourd'hui sans `compte_agent` casserait :
c'est le but, mais le Codeur lance la suite entière pour le trouver.