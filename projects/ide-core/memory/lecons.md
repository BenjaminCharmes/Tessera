# Leçons du projet

Pièges observés sur ce projet, une ligne chacun. Le service écrit sous `## Proposées` ; un humain déplace une leçon sous `## En vigueur` pour qu'elle atteigne le codeur et le reviewer.

## Proposées
- Quand un validateur énumère plusieurs cas (A/B/C) et qu'un manque après refactorisation, tous les chemins doivent être traités ensemble. (source : ticket-1029, 2026-11-20)
- Quand un modèle Pydantic exposé par l'API est modifié, régénérer et committer le schéma OpenAPI. (source : ticket-1033, 2026-11-20)
- Quand on extrait une fonction dans un fichier de service, vérifier que ce fichier ne dépasse pas son plafond, car la contraction ailleurs ne le compense pas toujours. (source : ticket-1036, 2026-11-20)

## En vigueur
- Quand un verrou protège un état global partagé, intégrer un test de sa présence pour prévenir sa suppression accidentelle. (source : ticket-1023, 2026-11-20)
- Quand tu écris des données de test pour un module sensible, vérifie qu'elles ne déclenchent pas le contrôle de traces professionnelles. (source : ticket-933, 2026-11-11)
- Quand tu raccourcis des commentaires pour loger du code, c'est que tu ajoutes trop : extrais un module au lieu d'éroder la doc. (source : ticket-915, 2026-11-11)
- Quand tu rattrapes les exceptions d'une bibliothèque de parsing, nomme les types réellement levés, sans supposer qu'ils héritent de ValueError. (source : ticket-902, 2026-11-10)
- Quand tu crées plusieurs variantes d'un modèle de test, passe tous les champs requis sur chacune. (source : ticket-906, 2026-11-10)
- Quand tu ajoutes ou modifies une route ou un modèle de réponse FastAPI, régénère et commite `docs/openapi.json`, et range la route dans `frontend/src/test/contrat/perimetre.ts`. (source : ticket-860, ticket-864, 2026-11-06)
- Quand un ticket ferme une porte (route, commande, chemin), liste toutes celles de la même classe et ferme-les, ou dis pourquoi elles restent ouvertes. (source : ticket-808, audit externe, 2026-11-06)
- Quand tu déplaces du code pour tenir un plafond de longueur, mesure ensuite chaque fichier touché, source et cible, et lance les tests qui importent l'ancien emplacement. (source : ticket-875, ticket-888, ticket-894, ticket-900, 2026-11-10)
- Quand un test lit un log écrit par `get_logger()`, vérifie d'abord que ce logger est capturé par le test. (source : ticket-880, 2026-11-06)
- Quand tu protèges un chemin, compare-le après expansion de `~` et des variables d'environnement, et après résolution. (source : ticket-879, 2026-11-06)
- Quand une fonction n'est appelée que sous condition, teste-la en franchissant cette condition, jamais isolément. (source : ticket-892, 2026-11-09)
- Quand une revue relève une erreur dans un ADR ou dans `decisions.md`, corrige-la dans le même diff que le code. (source : ticket-894, 2026-11-09)
- Quand des droits d'accès sont posés sur un dossier avant qu'on le remplisse, repose-les après le remplissage. (source : ticket-895, 2026-11-09)
- Quand tu ajoutes une méthode à une classe moquée, mets à jour tous les doubles de cette classe. (source : ticket-987, 2026-11-17)
