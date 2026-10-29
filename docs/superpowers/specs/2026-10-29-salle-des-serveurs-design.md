# La salle des serveurs — conception (ticket-626)

ADR : ADR-064. Complète ADR-058 (rien n'est décoratif) et ADR-039 (échec fermé).

## 1. Problème

Idée du 28/10 : la vue « En cours » devient une salle par app lancée, avec les
agents propres à chaque produit. Tessera connaît d'une app son processus, ses
ports, sa mémoire (`AppEnCours`, `backend/src/tessera/models/inventaire.py`) et
l'état de ses services (`ServiceActif`, `frontend/src/types/api.ts`). L'activité
des agents d'un produit vit dans ce produit : rien ne la remonte.

## 2. Ce que chaque projet fait tourner

Source des services : le champ `services` de chaque `agents.json`. « Lu » = le
fichier a été ouvert ; « listé » = son existence est vérifiée, son contenu non.

| Projet | Services déclarés | Agents IA | Ce qui existe déjà | Preuve |
|---|---|---|---|---|
| vigie | backend (8025), frontend, worker | Trois rôles d'appel : `triage`, `synthesis`, `tickets`, tous à un seul tour, sans outil, passant par `LLMClient.run` | Un battement du worker (table `worker_heartbeat`, `worker_status`) ; un module d'usage LLM | `backend/app/llm/client.py` (lu), `backend/app/services/worker_heartbeat.py` (lu), `services/llm_usage.py`, `routers/llm.py`, `services/digest_llm.py` (listés) |
| affut | backend (8024), frontend, veille (worker) | Quatre rôles : `research`, `extraction`, `cse`, `questions`, via `LLMClient.run` | Un module d'usage LLM et une route | `backend/app/llm/client.py` (lu), `llm/usage.py`, `routers/llm.py`, `services/llm_extraction.py` (listés) |
| carriere | backend (8010), frontend | Le simulateur d'entretien (modèle Opus) ; trois autres modules LLM dont le rôle n'est pas lu | Rien relevé sur l'activité | `backend/app/llm.py` (lu), `training_llm.py`, `story_llm.py`, `inbox_llm.py`, `self_review_llm.py` (listés) |
| freelance | backend (8020), frontend | L'agent de prospection : recherche web et lecture d'URL, jusqu'à 20 tours | Une tâche suivie par identifiant | `backend/app/agents/prospecting_agent.py` (lu) |
| kadoomi | web (3201) | Aucun relevé | — | `agents.json` (lu) |
| devinoo | web (3200) | Aucun relevé | — | `agents.json` (lu) |
| demineur, serpent | un service de dev | Aucun relevé | — | `agents.json` (lu) |
| curio | backend (8026), frontend | Non vérifié | — | `agents.json` (lu) ; sources non lues |
| habit-tracker, repo-health | backend, frontend | Non vérifié | — | `agents.json` (lu) ; sources non lues |
| homelab-monitor | api (8022), frontend | Aucun fichier d'agent ou de LLM dans `src/` | — | liste de `src/` (listé) |

Hors inventaire : ide-core (ses runs ont le Bureau) ; portfolio, cookie_clicker
et benjamincharmes, qui ne déclarent aucun service.

Deux faits décident de la suite :

- **Les agents d'un produit sont des appels, pas des résidents.** Vigie et Affût
  passent tous leurs appels par un seul `LLMClient.run` : un point d'émission
  par process suffit, pas un par rôle.
- **Un produit a plusieurs process.** Le worker de Vigie et celui d'Affût sont
  des services distincts du backend : une source unique par projet ne tient pas.

## 3. Les trois sources

| | Route de santé enrichie | Sortie du service | Fichier d'activité |
|---|---|---|---|
| Effort par produit | Une route et un contrat HTTP par produit ; le worker n'a pas de serveur | Un format de ligne à tenir, et le log y gagne du bruit | Une fonction d'écriture dans le point d'appel du LLM |
| Tokens | Nuls | Nuls | Nuls |
| App muette | Un service arrêté ne répond plus : on ne distingue pas « repos » de « mort » | Seules les apps lancées par Tessera ont une sortie, tampon borné | Un fichier périmé se reconnaît à sa date |
| App lancée à la main | Oui, si le port est connu | Non | Oui |
| Surface | Tessera appelle un port local de chaque produit | Aucune | Aucune : une lecture de fichier |
| Échec fermé | À écrire (délai, statut, corps) | À écrire (parser du texte) | Une validation de schéma |

**Recommandation : réduire, puis adopter le fichier.** La salle par app, avec
l'état seul, se livre sans dépendre d'aucun produit. Les agents s'y ajoutent
quand un produit déclare un fichier d'activité. Écarter l'idée ne se justifie
pas : le coût est faible et la vue dit ce que Benjamin demande, sans rien
inventer.

## 4. Contrat du fichier d'activité

Déclaration, dans `agents.json`, par service (un geste humain : les agents ne
modifient pas `agents.json`, ADR-027) :

```json
{ "nom": "worker", "commande": "…", "cwd": "backend",
  "activite": "backend/data/activite-worker.json" }
```

Le chemin est relatif à la racine du projet. Une fois résolu (liens compris), il
doit rester dans le dossier du projet (ADR-031). Le produit l'ignore dans son
propre `.gitignore` : le fichier change sans cesse.

Contenu, écrit par le produit, jamais par Tessera :

```json
{ "version": 1,
  "maj": "2026-10-29T10:12:03Z",
  "agents": [
    { "id": "triage", "nom": "Triage des signaux", "etat": "actif",
      "depuis": "2026-10-29T10:11:58Z", "libelle": "lot 3 sur 5" }
  ] }
```

| Champ | Règle |
|---|---|
| `version` | 1 ; toute autre valeur : fichier refusé |
| `maj` | ISO 8601 UTC ; périmé au-delà de 30 s, refusé s'il est à plus de 5 s dans le futur |
| `agents` | 12 au plus ; liste vide permise (arrêt propre) |
| `id` | `[a-z0-9-]`, 1 à 40 signes, unique dans le fichier |
| `nom` | 1 à 40 signes |
| `etat` | `actif` ou `repos` |
| `depuis`, `libelle` | facultatifs ; `libelle` 80 signes au plus, un nom d'étape, **jamais** un texte d'utilisateur (le cockpit Carrière manipule du contenu personnel) |

Le produit réécrit le fichier au moins toutes les 10 s tant qu'un agent est
`actif`, à chaque changement d'état, et en écriture atomique (fichier
temporaire, puis renommage). Le fichier fait 16 Ko au plus.

Règle de lecture, échec fermé : fichier absent, illisible, trop gros, hors
schéma, périmé, chemin hors du projet, ou service sans app vivante dans
l'inventaire → **aucun agent dessiné**, et la salle montre l'état de l'app
seul. Un champ inconnu fait refuser le fichier. Le texte se rend comme texte,
jamais comme balisage.

## 5. Interfaces

Backend :

- `ServiceDeclare` (`models/agent.py`) gagne `activite: str | None = None`.
- `models/activite.py` : `AgentDeProduit` (`id`, `nom`, `etat`, `depuis`,
  `libelle`) et `ActiviteDeService` (`project_id`, `service`, `agents`).
- `services/activite_produit.py` : `lire_activite(racine, chemin, maintenant)
  -> list[AgentDeProduit]`, qui renvoie `[]` sur tout échec et ne lève jamais.
- `GET /services/running/activite -> list[ActiviteDeService]`, une entrée par
  service à `activite` déclaré dont l'app tourne.

Frontend : `useActiviteProduit()`, relève toutes les 5 s en même temps que
`useAppsEnCours`, et `ActiviteDeService` dans `types/api.ts`.

## 6. Tickets

Étape 0, humaine : la **maquette** de la vue, sur le compte de Benjamin, avant
toute interface. Critères : une salle par app lancée avec ses ports, sa
mémoire, son démarrage ; trois états de salle (app seule, app avec agents au
repos, app avec agents actifs) ; la salle d'une app arrêtée ; clair et sombre.

| Ticket | Contenu | Critères vérifiables |
|---|---|---|
| ticket-671 | Contrat et lecteur | `activite` est accepté dans `services[]` et rendu par l'API ; un test par cause de refus (absent, trop gros, JSON invalide, schéma, version, périmé, futur, chemin hors projet, service arrêté) renvoie `[]` ; un fichier valide rend ses agents |
| ticket-672 | Salle par app, état seul (bloqué jusqu'à la maquette) | Une salle par entrée de `useAppsEnCours` ; sans fichier d'activité, aucun agent ; clavier et lecteur d'écran par la vue Liste existante |
| ticket-673 | Agents dessinés depuis le fichier | Un sprite par agent déclaré, sous `design/bureau/` ; test « sans donnée, rien » ; `actif` et `repos` se distinguent ; aucune couleur de texte `violet` (ADR-026) |

Chez les produits, hors d'ide-core (ADR-031) : un **émetteur** par produit,
déposé comme signalement à la session du projet, avec la déclaration
`activite` à poser à la main dans son `agents.json`.

- vigie et affut : envelopper `LLMClient.run` pour écrire `actif` avant l'appel
  et `repos` après, un fichier par process (backend, worker).
- carriere : envelopper l'appel du simulateur d'entretien ; ne jamais écrire de
  texte de l'utilisateur dans `libelle`.
- freelance : écrire `actif` pendant la tâche de prospection.

## 7. Ce que cette décision ne tranche pas

- Les agents de curio, habit-tracker et repo-health : non lus. Un émetteur ne se
  demande qu'à un produit qui fait tourner un agent.
- Le rôle des modules LLM de carriere autres que le simulateur.
- L'ordre de livraison des émetteurs : à Benjamin, produit par produit.
- Une mesure du coût : l'écriture d'un petit fichier toutes les 10 s n'est pas mesurée.
