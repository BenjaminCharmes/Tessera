---
agent: codeur
created: 2026-11-25
depends_on: []
estimated_days: 1
id: ticket-1051
pr_number: 1268
priority: medium
status: done
title: The chat talks without tools and agents/run refuses in an agent-account project
type: fix
---

# ticket-1051 — Chat sans outils et `agents/run` fermé dans un projet à compte agent

## Objectif

Réaliser l'ADR-094 : dans un projet où `projet_exige_le_compte` est vrai, le
chat ne lève plus `ProviderIndisponible` mais répond sans outils, et
`agents/run` / `agents/stream` refusent explicitement.

## Contexte

`routers/chat.py` construit le provider avec `tools=_CHAT_TOOLS` et
`routers/agents.py::_make_runner` sans `compte_agent` : ADR-093 les refuse.
Le chat lit `skills` dans `agents.json` (`par_role.py`, `config.skills`) : un
rôle `chat` déclaré avec skills, ou `"web": true` hors `allow_tools=False`,
serait encore refusé. Aucun rôle `chat` n'est déclaré dans ide-core aujourd'hui.

## Ce qu'il faut faire

1. **Chat** (`routers/chat.py`) : si `projet_exige_le_compte(project_path)`,
   construire le provider avec `allow_tools=False`, sans skill ni `signaler`
   (skills du rôle ignorés dans ce cas), sans `compte_agent`. Le contexte
   (CLAUDE.md, tickets ouverts, contraintes) reste fourni. Aucune écriture,
   donc aucun commit `chat-…` pour ce projet.
2. **`agents/run` et `agents/stream`** (`routers/agents.py`) : dans un tel
   projet, refus pour tout rôle sauf `github-sync`, avant la construction du
   runner. `POST /agents/run` répond 409 avec un `detail` en français, sur le
   modèle de `refuser_projet_a_worktree` (`routers/dependencies.py`).
   `WS /agents/stream` accepte la connexion avant de lire la requête et ne
   peut donc pas répondre par un code HTTP : il envoie `{"error": …}` en
   français, puis ferme avec le code 1008, comme le chat.
3. **Interface** : le chat d'un tel projet affiche un bandeau « sans accès aux
   fichiers sur ce projet » à la place d'une erreur de provider. L'état se lit
   d'un champ de l'API du chat (ex. `sans_outils: bool` dans `ChatHistory`),
   non d'un message d'erreur.

## Critères d'acceptation

- [ ] Un test backend, avec `AGENT_USER` posé et un manifeste
      `worktree.compte_agent: true`, montre que le provider du chat est
      construit sans outil, sans skill et sans `signaler`, et qu'un message
      de chat reçoit une réponse au lieu de `ProviderIndisponible`.
- [ ] Un test montre qu'un rôle `chat` déclaré avec `skills` ou `"web": true`
      dans `agents.json` part quand même sans outil ni skill dans ce projet.
- [ ] Un test montre que, dans un projet sans `compte_agent`, le chat garde
      `_CHAT_TOOLS` et son comportement actuel.
- [ ] Des tests montrent, pour `codeur` et `reviewer` dans un tel projet,
      que `POST /api/v1/agents/run` répond 409 et que
      `WS /api/v1/agents/stream` envoie une erreur en français puis ferme
      avec le code 1008, sans construire de runner ; et que `github-sync`
      passe encore.
- [ ] Un test montre que le chat d'un tel projet ne crée ni branche
      `chat-…` ni commit.
- [ ] Un test frontend (Vitest) montre le bandeau « sans accès aux fichiers
      sur ce projet » quand l'API signale `sans_outils`, et son absence sinon.
- [ ] Le diff ne touche ni `compte_exige.py` ni la règle d'ADR-093 : un appel
      outillé sans compte reste refusé.

## Ce que ça ne fait pas

- Ne donne au chat ni worktree ni droit sous le compte agent (option rejetée
  par l'ADR-094).
- Ne change pas `refuser_projet_a_worktree`, ni le chat des projets sans
  `compte_agent`.

## Dépendances

Aucune. ADR-094.