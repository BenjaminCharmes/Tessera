---
agent: codeur
created: 2026-11-23
depends_on:
- ticket-1037
estimated_days: 2
id: ticket-1038
plan: true
pr_number: null
priority: high
status: done
title: Documentation agents read a large file section by section, on request
type: feat
---

# ticket-1038 — Les agents de documentation lisent un gros fichier section par section, à la demande

## Objectif

Qu'un agent de documentation lise le texte des sections qu'il veut corriger,
même dans un fichier de 180 000 caractères, sans recevoir toute la
documentation du projet à chaque appel.

## Contexte

Mesuré le 23/11 sur ide-core, en reconstruisant hors ligne le message du
ticket-1036 puis en le rejouant sur le même modèle :

- Le message pèse 220 000 caractères, dont 198 000 de documentation : environ
  135 000 jetons par appel, 2 à 3 appels par ticket. Du 18 au 20/11, 63 appels
  de documentation pour les tickets 1000 à 1036, et deux passes seulement ont
  écrit un fichier. Depuis le 13/11, 53 passes sur 62 n'ont rien écrit.
- `contenu_et_reduits` (`documentation_contenu.py`) remplit un budget unique de
  200 000 caractères (`BORNE_DOC`) dans l'ordre alphabétique. `docs/architecture.md`
  (182 000) arrive après 31 000 caractères déjà pris : il ne tient jamais et
  se réduit à ses 204 titres. `docs/guide-utilisateur.md` (137 000) prend
  ensuite presque tout le reste, et `docs/historique.md` (7 000) puis
  `docs/ticket-strategy.md` (3 900) sont réduits à leur tour. Le journal dit
  « documentation trop longue » pour un fichier de 3 900 caractères : c'est le
  budget qui est épuisé, pas le fichier qui est long.
- `doc-technique` ne lit donc jamais une ligne du fichier dont il a la charge,
  mais reçoit en entier le guide utilisateur. Il ne peut pas citer un texte
  dans `ancien` : il ne lui reste que `apres_section`, donc ajouter, jamais
  corriger. Le fichier ne peut que grandir.
- Le rejeu du 23/11 a rendu une édition `apres_section` valide pour
  `doc-technique` et `{"editions": []}` pour `doc-fonctionnelle` ; le 20/11, le
  même lot avait rendu zéro fichier. Le résultat n'est pas stable sur un
  message de cette taille.

Découper `docs/architecture.md` en plusieurs fichiers ne suffit pas : le total
(320 000 caractères avec le guide) resterait au-dessus de tout budget, et le
problème reviendrait au prochain fichier qui grossit. Les autres projets, dont
la documentation est courte, ne sont pas touchés et ne doivent pas payer un
appel de plus.

## Solution proposée

1. **Une borne par fichier, plus de budget glouton.** Un fichier sous la borne
   (valeur de départ : 20 000 caractères) est donné en entier ; au-dessus, il
   est donné par ses titres, quel que soit son rang alphabétique. La borne
   totale ne sert plus qu'en dernier recours.
2. **Des sections à la demande.** Quand au moins un fichier est donné par ses
   titres, la réponse d'un rôle peut porter, à la place des éditions, une
   liste `sections` de `{fichier, titre}`. Le service rappelle alors le rôle
   une fois, avec le même message augmenté du texte entier de ces sections
   (du titre jusqu'au titre suivant de niveau égal ou supérieur, comme le fait
   déjà `_inserer` dans `documentation_editions.py`), dans une limite totale
   (valeur de départ : 40 000 caractères, le surplus est nommé).
3. **Une demande est contrôlée comme une édition** : seul un fichier de
   documentation sous la racine se lit (`_documentable`, comme
   `titres_fichiers_vises`), un titre absent ou ambigu est ignoré et signalé au
   rôle dans le rappel.
4. Sans fichier donné par ses titres, rien ne change : un appel par rôle.
5. Les prompts `agents/prompts/doc-technique.md` et
   `agents/prompts/doc-fonctionnelle.md` décrivent la demande de sections et
   disent qu'un `ancien` se recopie d'une section reçue.
6. Le message du journal distingue « fichier donné par ses titres » de
   l'ancien « documentation trop longue ».
7. Une ADR au prochain numéro libre de `memory/decisions.md` amende ADR-057.

`services/documentation/documentation.py` est à son plafond dans
`test_longueur_des_fichiers.py` : le code nouveau vit dans un module voisin.

## Critères d'acceptation

- [ ] Un test donne un dossier `docs/` avec un fichier au-dessus de la borne
      par fichier et, après lui dans l'ordre alphabétique, un fichier de moins
      de 5 000 caractères : le message porte le petit fichier en entier et le
      gros par ses titres.
- [ ] Un test fait répondre un rôle par une liste `sections` : le service
      rappelle ce rôle une fois, le message du rappel contient le texte entier
      des sections demandées et pas le corps d'une autre section du même
      fichier, et une édition `ancien` qui cite ce texte s'applique.
- [ ] Un test demande une section d'un fichier hors documentation, un chemin
      avec `..` et un titre absent : aucun de ces contenus n'entre dans le
      rappel, et rien n'est lu hors de la racine.
- [ ] Un test vérifie que, sans fichier au-dessus de la borne, chaque rôle
      n'est appelé qu'une fois.
- [ ] `agents/prompts/doc-technique.md` et `agents/prompts/doc-fonctionnelle.md`
      décrivent le format `sections` et son usage.
- [ ] Une ADR au prochain numéro libre de `memory/decisions.md` décrit la borne
      par fichier et la lecture par sections, et dit qu'elle amende ADR-057.

## Ce que ça ne fait pas

- Ne découpe ni ne réécrit `docs/architecture.md`.
- Ne restreint pas les fichiers qu'un rôle peut modifier.
- Ne rattrape pas les tickets comptés comme documentés depuis le 13/11 sans
  l'avoir été.
- Ne choisit pas les sections à la place de l'agent : pas de sélection par
  mots-clés.

## Vérification après merge (session ide-core, hors critères)

Au premier run ide-core suivant le rechargement du backend : lire dans
`agent_calls` les jetons d'entrée des deux rôles (attendu : nettement sous
50 000, contre 135 000) et dans `pipeline-log.md` l'issue de chaque rôle.

## Dépendances

ticket-1037 : sans lui, le journal ne dit pas ce qu'un rôle a rendu.

## Estimation

2 jours.

## Risques

- Un rôle peut demander des sections sans rapport et ne rien écrire : un
  appel de plus pour rien, mais chacun pèse cinq fois moins qu'aujourd'hui.
- `ancien` reste contrôlé sur le fichier entier : un texte recopié d'une
  section mais présent ailleurs est refusé comme aujourd'hui, avec son
  contexte au tour de correction.