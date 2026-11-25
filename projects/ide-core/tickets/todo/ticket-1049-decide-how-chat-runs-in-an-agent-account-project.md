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

## Décision de l'utilisateur (25/11)

L'option retenue est la 2, dans sa forme « chat sans outils ». L'ADR
l'écrit et la justifie, sans rouvrir le choix :

- **Chat** : dans un projet où `projet_exige_le_compte` est vrai, le chat
  part sans outil ni skill ni `signaler`. ADR-093 le permet déjà (seul un
  appel sans outil se passe du compte) : il part donc sous le compte de
  l'utilisateur, sans dossier de travail où écrire. Il garde son contexte
  (CLAUDE.md du projet, tickets ouverts, contraintes) : il sert à discuter et à
  préparer un ticket, ne lit ni n'écrit de fichier, et ne fait donc aucun
  commit. L'interface le dit (par exemple « sans accès aux fichiers sur ce
  projet ») au lieu d'afficher une erreur de provider. Vérifier dans
  `providers/par_role.py` que le rôle `chat` d'un tel projet ne reçoit ni skill
  ni `signaler` par sa déclaration dans `agents.json`.
- **`POST /api/v1/agents/run` et `WS /api/v1/agents/stream`** : dans un tel
  projet, un 409 explicite pour tout rôle sauf `github-sync`, qui n'appelle
  aucun modèle (ADR-010). Même forme que `refuser_projet_a_worktree`
  (`routers/dependencies.py`), qui refuse déjà `/chat/run` dans tout projet à
  worktree. Aucun écran n'appelle aujourd'hui ces deux routes pour un autre
  rôle que `github-sync`.
- **Rejetée, l'option 1 (un worktree par conversation)** : création du
  worktree, droit posé puis repris à chaque appel (ADR-091), et une livraison à
  inventer pour la branche `chat-…`, dont l'écriture ne passe aujourd'hui ni
  par l'audit ni par la relecture. Plusieurs tickets pour un usage quasi nul :
  la base ne compte qu'un message de chat, le 15/09. Elle reste possible plus
  tard si le besoin vient.
- **Rejetée, le refus pur** : aussi simple, mais on perd la discussion.

Une seule fiche de réalisation suffit (chat, `agents/run`, `agents/stream`,
message de l'interface), type `fix`.

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
