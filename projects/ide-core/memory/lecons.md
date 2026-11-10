# Leçons du projet

Pièges observés sur ce projet, une ligne chacun. Le service écrit sous `## Proposées` ; un humain déplace une leçon sous `## En vigueur` pour qu'elle atteigne le codeur et le reviewer.

## Proposées
- Quand on abaisse le plafond de longueur d'un fichier lors d'une refactorisation, mesurer le bilan net en lignes avant de soumettre — l'extraction seule peut ne pas suffire. (source : ticket-875, 2026-11-06)
- Quand on ajoute du logging via `get_logger()`, vérifier d'abord que ce log sera visible aux tests avant de les écrire. (source : ticket-880, 2026-11-06)
- Quand on protège un chemin sans développer les variables d'environnement et le ~, la protection peut être contournée. (source : ticket-879, 2026-11-06)
- Quand on centralise une fonction et l'importe partout, vérifier que chaque fichier reste sous 300 lignes. (source : ticket-888, 2026-11-06)
- Quand une mise à jour SDK est corrigée après rejet, soumettre avec le lockfile complet et le rapport d'API, pas l'un sans l'autre. (source : ticket-893, 2026-11-09)
- Quand une fonction n'est appelée que sous condition, la tester en franchissant cette condition, jamais en l'appelant isolément. (source : ticket-892, 2026-11-09)
- Quand le jeton change après qu'une ressource aie échoué en 401, vérifier que l'état d'échec se réinitialise pour permettre une nouvelle tentative avec le nouveau jeton. (source : ticket-897, 2026-11-09)
- Quand les gardes de permission se multiplient dans agent_sdk.py, créer une fonction qui agrège les hooks pour respecter le plafond. (source : ticket-899, 2026-11-09)
- Quand une revue identifie une erreur dans un ADR ou decisions.md (chemin corrompu, caractère binaire), la corriger dans le même diff que le code. (source : ticket-894, 2026-11-09)
- Quand les restrictions d'accès sont posées avant un peuplement, les reposer après pour qu'elles s'appliquent à chaque fichier. (source : ticket-895, 2026-11-09)
- Quand on extrait du code vers un fichier existant pour alléger le sien, vérifier que le fichier cible ne dépasse pas sa limite de taille. (source : ticket-900, 2026-11-10)
- Quand on rattrape les exceptions d'une bibliothèque de parsing, ajouter explicitement les types d'exception réellement levés au lieu de supposer qu'ils héritent de ValueError. (source : ticket-902, 2026-11-10)

## En vigueur
- Quand tu ajoutes ou modifies une route ou un modèle de réponse FastAPI, régénère et commite `docs/openapi.json`, et range la route dans `frontend/src/test/contrat/perimetre.ts` (couverte ou hors périmètre). (source : ticket-860, ticket-864, 2026-11-06)
- Quand un ticket ferme une voie d'attaque ou une porte (route, commande, chemin), liste dans le diff ou le ticket toutes les routes, commandes et chemins de la même classe et ferme-les ou dis pourquoi ils restent ouverts : une faille corrigée sur une seule route laisse sa voisine ouverte. (source : ticket-808 vs PATCH /pipeline, audit externe, 2026-11-06)
- Quand tu déplaces, extrais ou centralises du code pour tenir un plafond de longueur, mesure ensuite chaque fichier touché, la source comme la cible, et lance les tests qui importent l'ancien emplacement : le déplacement seul ne suffit pas toujours. (source : ticket-875, ticket-888, ticket-894, ticket-900, 2026-11-10)
- Quand un test doit lire un log écrit par `get_logger()`, vérifie d'abord que ce logger est capturé par le test avant d'écrire l'assertion. (source : ticket-880, 2026-11-06)
- Quand tu protèges un chemin, compare-le après expansion de `~` et des variables d'environnement, et après résolution : sinon la protection se contourne. (source : ticket-879, 2026-11-06)
- Quand une fonction n'est appelée que sous condition, teste-la en franchissant cette condition, jamais en l'appelant isolément. (source : ticket-892, 2026-11-09)
- Quand une revue relève une erreur dans un ADR ou dans `decisions.md`, corrige-la dans le même diff que le code. (source : ticket-894, 2026-11-09)
- Quand des droits d'accès sont posés sur un dossier avant qu'on le remplisse, repose-les après le remplissage, pour que chaque fichier les porte. (source : ticket-895, 2026-11-09)
