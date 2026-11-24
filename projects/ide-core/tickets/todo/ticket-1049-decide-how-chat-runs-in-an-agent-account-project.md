---
id: ticket-1049
title: "Decide how the chat and agents/run work in a project that declares the agent account"
type: design
status: todo
pr_number: null
priority: medium
agent: architect
depends_on: []
estimated_days: 1
created: 2026-11-24
---

# ticket-1049 — Décider comment le chat et `agents/run` tournent dans un projet à compte agent

## Objectif

Trancher, par une ADR, ce que deviennent les deux appels outillés qui ne
passent pas par le compte agent dans un projet qui déclare
`worktree.compte_agent` : le chat du projet et `POST /api/v1/agents/run`.

## Contexte

Depuis le ticket-1043 (ADR-093), `refuser_appel_outille_sans_compte`
(`backend/src/tessera/services/providers/compte_exige.py`) lève
`ProviderIndisponible` pour tout appel outillé sans `compte_agent=True` dans un
tel projet. Deux appelants sont dans ce cas :

- `backend/src/tessera/routers/chat.py` : `provider_pour_role(project_path,
  "chat", tools=_CHAT_TOOLS, …)`, sans `compte_agent` ;
- `backend/src/tessera/routers/agents.py` : `_make_runner`, qui construit
  codeur et reviewer sans `compte_agent`.

Sur un projet à compte agent (Démineur aujourd'hui), le chat répond donc par
une erreur. Le faire partir sous le compte ne suffit pas : le chat travaille
dans le checkout du projet, sous le profil de l'utilisateur, où le compte agent
n'a aucun droit (ADR-083, ADR-086) ; un run, lui, travaille dans son worktree
sous `C:\ProgramData\Tessera`.

## Solution proposée

Une ADR qui choisit entre, au moins :

1. le chat d'un tel projet ouvre son propre worktree (comme un run, branche
   `chat-<horodatage>`, ADR-018 et ADR-056) et part sous le compte ;
2. le chat y est réduit à la lecture ou refusé, avec un message qui le dit
   dans l'interface au lieu d'une erreur de provider ;
3. une autre voie, si la lecture du code en montre une.

Pour chaque option : ce que le compte peut lire et écrire, ce que coûte un
appel (ADR-091), ce qui se passe pour `agents/run`, et ce que voit
l'utilisateur. L'ADR nomme les tickets de réalisation à écrire.

## Critères d'acceptation

- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` tranche le
      sort du chat et celui de `POST /api/v1/agents/run` dans un projet qui
      déclare `worktree.compte_agent`, et nomme l'alternative rejetée.
- [ ] L'ADR dit, pour l'option retenue, sous quel compte part l'appel et dans
      quel dossier il travaille.
- [ ] Une règle correspondante est écrite sous `## Proposées` de
      `memory/contraintes.md`, ou l'ADR dit pourquoi aucune règle n'est
      nécessaire.
- [ ] Les fiches de réalisation sont écrites dans `tickets/todo/`, chacune
      avec des critères jugeables sur un diff.
- [ ] Le diff ne modifie aucun fichier sous `backend/` ni `frontend/`.

## Ce que ça ne fait pas

- N'écrit aucun code : la réalisation vient par les fiches que ce ticket crée.
- Ne revient pas sur ADR-093 : un appel outillé sans compte reste refusé.

## Dépendances

Aucune.

## Estimation

Une journée.

## Risques

`contraintes.md` est au plafond de 12 000 caractères : une règle acceptée
devra en fusionner ou en resserrer une autre.
