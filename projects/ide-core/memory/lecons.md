# Leçons du projet

Pièges observés sur ce projet, une ligne chacun. Le service écrit sous `## Proposées` ; un humain déplace une leçon sous `## En vigueur` pour qu'elle atteigne le codeur et le reviewer.

## Proposées

## En vigueur
- Quand on rattrape les exceptions d'une bibliothèque de parsing, ajouter explicitement les types d'exception réellement levés au lieu de supposer qu'ils héritent de ValueError. (source : ticket-902, 2026-11-10)
- Quand on crée plusieurs variantes d'un modèle de test, tous les champs requis doivent être passés sur chaque variante, pas seulement celle qui l'utilise logiquement. (source : ticket-906, 2026-11-10)
- Quand tu ajoutes ou modifies une route ou un modèle de réponse FastAPI, régénère et commite `docs/openapi.json`, et range la route dans `frontend/src/test/contrat/perimetre.ts` (couverte ou hors périmètre). (source : ticket-860, ticket-864, 2026-11-06)
- Quand un ticket ferme une voie d'attaque ou une porte (route, commande, chemin), liste dans le diff ou le ticket toutes les routes, commandes et chemins de la même classe et ferme-les ou dis pourquoi ils restent ouverts : une faille corrigée sur une seule route laisse sa voisine ouverte. (source : ticket-808 vs PATCH /pipeline, audit externe, 2026-11-06)
- Quand tu déplaces, extrais ou centralises du code pour tenir un plafond de longueur, mesure ensuite chaque fichier touché, la source comme la cible, et lance les tests qui importent l'ancien emplacement : le déplacement seul ne suffit pas toujours. (source : ticket-875, ticket-888, ticket-894, ticket-900, 2026-11-10)
- Quand un test doit lire un log écrit par `get_logger()`, vérifie d'abord que ce logger est capturé par le test avant d'écrire l'assertion. (source : ticket-880, 2026-11-06)
- Quand tu protèges un chemin, compare-le après expansion de `~` et des variables d'environnement, et après résolution : sinon la protection se contourne. (source : ticket-879, 2026-11-06)
- Quand une fonction n'est appelée que sous condition, teste-la en franchissant cette condition, jamais en l'appelant isolément. (source : ticket-892, 2026-11-09)
- Quand une revue relève une erreur dans un ADR ou dans `decisions.md`, corrige-la dans le même diff que le code. (source : ticket-894, 2026-11-09)
- Quand des droits d'accès sont posés sur un dossier avant qu'on le remplisse, repose-les après le remplissage, pour que chaque fichier les porte. (source : ticket-895, 2026-11-09)
