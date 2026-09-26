---
id: ticket-188
title: "Le provider et le modèle se déclarent par rôle, avec un repli"
type: feat
status: done
pr_number: 55
priority: high
agent: codeur
depends_on: []
estimated_days: 2
created: 2026-09-26
---

# ticket-188 — Le provider et le modèle se déclarent par rôle, avec un repli

## Objectif

Qu'un projet puisse dire, rôle par rôle, quel provider et quel modèle
servent un agent, et sur quoi retomber quand ce provider ne répond pas.

## Contexte

Le provider est choisi une fois pour tout le backend, par
`settings.llm_provider` (`config.py:21`) ; `agents.json` ne connaît que
`model`. Cinq services ont leur modèle **codé en dur** et ignorent
`agents.json` : sécurité et validateur (`sonnet-4-6`), documentation
(`haiku-4-5`), planificateur, analyseur de projet. Le chat ne lit même pas
`settings.llm_provider` (`routers/chat.py:98`).

La grille tarifaire (`cost_calculator.py`) sert aussi de liste blanche :
`set_agent_model` refuse tout modèle absent de `_PRICING`. Un modèle local
serait donc refusé par l'UI, ou facturé au tarif Sonnet.

Sans ce ticket, le provider Ollama (ticket-189) n'est branchable nulle part :
le seul interrupteur existant basculerait aussi le codeur.

## Solution proposée

- `AgentConfig` gagne `provider: str = "agent_sdk"` et
  `fallback: FallbackConfig | None = None`, où `FallbackConfig` porte
  `provider` et `model`. Valeur de `provider` inconnue : le chargement du
  projet échoue avec un message qui nomme le rôle, comme pour tout
  frontmatter invalide.
- Une fabrique `provider_pour_role(project_path, role, ...)` remplace les
  appels directs à `get_provider` dans `routers/orchestrator.py`,
  `routers/agents.py`, `routers/projects.py` et `routers/chat.py`. Elle lit
  `agents.json`, construit le provider déclaré, et l'enveloppe dans un
  `ProviderAvecRepli` quand un `fallback` est déclaré.
- `ProviderAvecRepli` appelle le provider principal ; sur une exception de
  disponibilité (connexion refusée, délai dépassé, modèle absent — une
  classe `ProviderIndisponible` levée par les providers), il appelle le
  repli avec le modèle du repli, et émet un événement `provider_fallback`
  sur le canal d'ADR-041 avec le rôle, le provider tenté et celui utilisé.
  Une erreur de contenu (JSON illisible) n'est **pas** un repli : ADR-039
  la traite déjà.
- Les services à modèle codé en dur lisent désormais leur entrée
  `agents.json` par rôle (`securite`, `validateur`, `doc-technique`,
  `doc-fonctionnelle`, `planificateur`, `project-analyzer`). Rôle absent du
  manifeste : les valeurs d'aujourd'hui restent le défaut, rien ne change
  pour les projets existants.
- `ProviderResult.provider_name` et le modèle réellement utilisé partent
  dans `agent_calls`, pour que la ventilation des coûts dise ce qui a
  tourné. `agent_calls` gagne une colonne `provider`.
- La liste blanche se découple de la grille : `modeles_connus()` reste la
  liste des modèles **Anthropic** ; `set_agent_model` accepte n'importe quel
  nom quand le provider du rôle n'est pas Anthropic. `GET known_models`
  rend la liste par provider.
- L'UI de réglage des agents affiche et modifie `provider`, `model` et le
  repli, dans le panneau existant qui change déjà le modèle.

## Critères d'acceptation

- [ ] `agents.json` de `projects/ide-core` et de `demineur` chargent sans
      changement, et `test_consignes_coherentes.py` passe
- [ ] Un test vérifie qu'un `provider` inconnu fait échouer le chargement en
      nommant le rôle
- [ ] Un test vérifie que `ProviderAvecRepli` appelle le repli sur
      `ProviderIndisponible` et émet `provider_fallback`
- [ ] Un test vérifie qu'une réponse illisible ne déclenche **pas** le repli
- [ ] Un test par service (sécurité, validateur, documentation,
      planificateur, analyseur) vérifie que le modèle vient d'`agents.json`
      quand le rôle y est déclaré, et garde le défaut sinon
- [ ] Un test vérifie que le chat respecte le provider déclaré pour `chat`
- [ ] `set_agent_model` accepte un nom hors grille pour un rôle dont le
      provider n'est pas Anthropic, et le refuse toujours pour `agent_sdk`
- [ ] La ligne `agent_calls` d'un appel porte le provider réellement utilisé
- [ ] Un test vérifie qu'aucun `get_provider(` du code applicatif ne reste
      hors de la fabrique par rôle
- [ ] Le panneau agents du frontend permet de changer provider, modèle et
      repli (`npm run test` vert)
- [ ] `uv run mypy src/` et `npm run build` passent
- [ ] Un ADR est écrit : « le provider se déclare par rôle, un repli est
      explicite, et un repli utilisé se voit »

## Ce que ça ne fait pas

Aucun provider nouveau : `agent_sdk` et `anthropic_api` seulement. Pas de
routage automatique selon la taille du ticket ou la charge : le choix est
déclaré, jamais deviné (même forme qu'ADR-042).

## Dépendances

Aucune. Le ticket-189 en dépend.

## Estimation

2 jours.

## Risques

Beaucoup de points d'appel à unifier : le risque est d'en oublier un, qui
resterait sur le provider global. Le test sur les `get_provider(` restants
borne ce risque.
