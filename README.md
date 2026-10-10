# Tessera

> Un IDE qui fait travailler des agents IA sur vos tickets — et qui s'est
> construit lui-même.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![TypeScript strict](https://img.shields.io/badge/TypeScript-strict-blue)
![Tauri v2](https://img.shields.io/badge/Tauri-v2-orange)
![Licence PolyForm NC](https://img.shields.io/badge/licence-PolyForm%20NC-lightgrey)

Une *tessera*, c'est la tuile taillée d'une mosaïque : la plus petite pièce
qui, posée à côté des autres, finit par faire une image. Un ticket est extrait
de la file, traité, reposé.

## Ce que ça fait

Vous écrivez un ticket en Markdown. Tessera le confie à une chaîne d'agents —
**codeur → testeur → sécurité → reviewer → validateur** — qui travaillent sur
une branche git dédiée et la terminent par un commit.

Trois choix le distinguent d'un assistant de code classique :

- **Les agents écrivent vraiment les fichiers.** Ce qui est relu, audité et
  validé, c'est le **diff git réel** — pas la prose de l'agent expliquant ce
  qu'il pense avoir fait.
- **Un run ne salit jamais votre arbre.** Chaque run a sa branche et finit par
  un commit, approuvé ou non. Rien n'est perdu, rien ne bloque le ticket
  suivant.
- **Vous décidez jusqu'où il va.** Chaque projet déclare son niveau : s'arrêter
  au commit, ouvrir la PR, ou merger — et seulement si la CI est verte.

Après un run approuvé, la livraison enchaîne seule jusqu'où le projet
l'autorise : rebase, PR, attente de CI, merge. Certains conflits simples — dans
le journal (`memory/pipeline-log.md`) et la liste de documentation
(`memory/documentation.json`) — sont résolus automatiquement en union. Les autres
sont tentés par un agent, et leur résolution est toujours relue.

## Démarrer

Il vous faut Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 24, et un
abonnement Claude — aucune clef API n'est nécessaire dans le mode par défaut.

```bash
git clone https://github.com/BenjaminCharmes/Tessera.git
cd Tessera
make setup

make dev            # backend   → http://localhost:8000
make dev-frontend   # interface → http://localhost:5173
```

`make tauri-dev` lance l'application desktop, qui a besoin du backend dans un
autre terminal. Le détail — Docker, Windows, build de production — est dans le
[guide utilisateur](docs/guide-utilisateur.md).

### Un modèle local pour les rôles de jugement

Les rôles qui ne font qu'un appel texte → JSON — audit sécurité, validateur,
documentation, analyse de projet — peuvent tourner sur un modèle servi par
[Ollama](https://ollama.com), à coût nul. Le projet le déclare rôle par rôle
dans son `agents.json` (`"provider": "ollama"`), avec un repli sur Claude pour
les machines qui n'ont pas Ollama :

```bash
ollama pull qwen3-coder:30b     # ~19 Go, un seul modèle pour tous ces rôles
```

`OLLAMA_BASE_URL` (défaut `http://127.0.0.1:11434`) dit où est le serveur.
L'IDE ne télécharge jamais un modèle lui-même : absent, le repli prend le
relais et le signale. Le codeur, le reviewer et le chat restent sur Claude —
ils ont besoin des outils fichier que seul le SDK fournit.

**Sérialisation des requêtes** : quand plusieurs runs appellent le même serveur
Ollama, l'IDE les sérialise (une à la fois par serveur) pour éviter la compétition
pour le modèle et la mémoire. Un réglage `OLLAMA_MAX_CONCURRENT` contrôle ce
comportement. Si le serveur est saturé ou trop lent, l'IDE bascule rapidement sur
le repli pour ne pas bloquer le run — voir la [configuration](docs/configuration.md#ollama).



Si le serveur Ollama est lent ou indisponible, l'agent bascule rapidement sur le repli — voir `OLLAMA_SLOT_WAIT_S` dans la [configuration](docs/configuration.md).

## Documentation

| | |
|---|---|
| [Guide utilisateur](docs/guide-utilisateur.md) | installer, lancer, utiliser au quotidien |
| [Architecture](docs/architecture.md) | comment c'est fait, et pourquoi |
| [Configuration](docs/configuration.md) | variables d'environnement et commandes |
| [Référence API](docs/api.md) | les endpoints HTTP et WebSocket |
| [Stratégie de tickets](docs/ticket-strategy.md) | comment un ticket est écrit |
| [Historique](docs/historique.md) | ce qui a été livré, étape par étape |

Les décisions d'architecture en vigueur sont dans
[`projects/ide-core/memory/decisions.md`](projects/ide-core/memory/decisions.md) :
ce sont des contraintes, pas des archives.

## Self-hosting

Tessera est son propre premier projet. `projects/ide-core/` contient les
tickets qui ont servi à le construire — plus d'une centaine, chacun avec sa
section « ce que ça ne fait pas ». L'IDE mange sa propre cuisine, ce qui force
à le rendre utilisable vite.

## Contribuer

Les rapports de bug sont ce qui aide le plus. Avant d'écrire du code, lisez
[CONTRIBUTING.md](CONTRIBUTING.md) — en particulier le premier paragraphe sur
la licence.

Une faille de sécurité se signale **en privé** : voir [SECURITY.md](SECURITY.md).

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE.md). Le code est lisible, utilisable et
modifiable **à des fins non commerciales**. Il ne peut être ni vendu, ni
exploité dans un produit ou un service commercial.

Un dépôt public n'est pas un dépôt libre de droits : ce qui n'est pas accordé
ici reste réservé. Pour un usage commercial, écrivez-moi.
