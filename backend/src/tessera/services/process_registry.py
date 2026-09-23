"""Les services qu'un projet a lancés — ticket-137.

ADR-042 : le backend lance lui-même les commandes déclarées, sans shell et
sans agent, et les processus sont ses **enfants** — ils meurent avec lui.
C'est ce qui rend inutile toute reprise après redémarrage : il n'y a jamais
de processus orphelin à retrouver.

Ce registre est en mémoire du process, comme `RunLock` et `RunRegistry`
(ADR-038, ADR-041). La différence tient en une phrase : un run se termine
tout seul, un serveur non. Rien ici n'attend la fin de quoi que ce soit.
"""
import asyncio
import os
import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tessera.services.groupe_de_processus import (
    creer_groupe,
    fermer_le_groupe,
    rattacher,
    rattacher_au_groupe,
    tuer_l_arbre,
)
from tessera.services.providers.perimetre import racine_autorisee
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Les opérateurs qu'un shell interpréterait et que `create_subprocess_exec`
#: ne fait pas. Cherchés **après** découpage, et seulement comme token entier :
#: `python -c "import time; time.sleep(30)"` est légitime, et une recherche
#: naïve dans la chaîne entière le refuserait — elle l'a fait.
OPERATEURS_DE_SHELL = frozenset({"&&", "||", "|", ";", ">", ">>", "<", "&"})

#: Combien de temps on laisse un service s'arrêter poliment avant de le tuer.
DELAI_D_ARRET_S = 5.0

#: Les séquences de couleur d'un terminal. Vite, entre autres, colore sa
#: sortie — et les codes tombent **au milieu** de l'URL qu'il annonce :
#: `http://localhost:[1m5175[22m/`. L'adresse en sortait corrompue,
#: et le `<pre>` du panneau affichait « [32m » un peu partout, faute
#: d'interpréter quoi que ce soit (ticket-148).
_COULEURS = re.compile(r"\[[0-9;?]*[ -/]*[@-~]")


def sans_couleurs(ligne: str) -> str:
    """La ligne telle qu'elle se lit, sans les codes d'échappement."""
    return _COULEURS.sub("", ligne)


#: Combien de lignes un service garde de sa propre sortie — ticket-148.
#: `EventHub` ne rejoue pas l'historique (choix assumé pour la supervision),
#: or un service écrit ses lignes utiles, **dont son adresse**, dans ses deux
#: premières secondes : qui n'écoutait pas à cet instant ne les verrait
#: jamais. La borne est ce qui empêche le registre de grossir sans fin.
LIGNES_CONSERVEES = 200


class CommandeInvalide(Exception):
    """La commande déclarée ne peut pas être lancée telle quelle."""


class ServiceDejaEnCours(Exception):
    """Ce service tourne déjà — le relancer en ferait un second."""

    def __init__(self, nom: str, pid: int | None) -> None:
        self.nom = nom
        self.pid = pid
        super().__init__(
            f"Le service « {nom} » tourne déjà (pid {pid}). Arrête-le avant de "
            "le relancer : un second lancement laisserait le premier derrière, "
            "avec son port et sans rien pour l'arrêter."
        )


@dataclass
class Service:
    """Un processus lancé pour un projet."""

    nom: str
    project_id: str
    #: `None` pour un service **déclaré mais pas lancé** : l'IDE doit savoir
    #: qu'il existe avant d'avoir cliqué (ticket-146).
    pid: int | None = None
    processus: Any = None
    demarre_a: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    sortie: list[str] = field(default_factory=list)
    #: Vrai quand c'est l'utilisateur qui a demandé l'arrêt. `terminate()`
    #: produit un code non nul sur certaines plateformes : sans ce drapeau, un
    #: service qu'on vient d'arrêter s'afficherait comme ayant échoué, et
    #: enverrait chercher des logs qui ne disent rien (ticket-151).
    arrete_a_la_main: bool = False
    #: Le groupe système qui contient ce service et toute sa descendance.
    #: Le fermer les tue tous, ce que `taskkill /T` ne sait pas faire quand
    #: un maillon intermédiaire a disparu (ticket-153).
    groupe: Any = None

    def noter(self, ligne: str) -> None:
        """Retient une ligne, en ne gardant que les plus récentes."""
        self.sortie.append(ligne)
        if len(self.sortie) > LIGNES_CONSERVEES:
            del self.sortie[: len(self.sortie) - LIGNES_CONSERVEES]

    @property
    def en_cours(self) -> bool:
        return self.processus is not None and self.processus.returncode is None

    def en_dict(self) -> dict[str, Any]:
        return {
            "nom": self.nom,
            "project_id": self.project_id,
            "pid": self.pid,
            "demarre_a": self.demarre_a.isoformat(),
            "en_cours": self.en_cours,
            "code_de_sortie": (
                self.processus.returncode if self.processus is not None else None
            ),
            "sortie": list(self.sortie),
            "arrete_a_la_main": self.arrete_a_la_main,
        }


def verifier_la_commande(commande: str) -> list[str]:
    """Découpe la commande, en refusant ce qui exige un shell.

    `create_subprocess_exec` ne passe par aucun shell : un `&&` arriverait
    tel quel en argument du premier programme. Refuser tôt vaut mieux que de
    lancer la moitié de ce qui était écrit.

    Le contrôle porte sur les **tokens**, jamais sur la chaîne brute : un
    point-virgule dans `python -c "import time; time.sleep(30)"` appartient au
    code Python, pas au shell.
    """
    if not commande.strip():
        raise CommandeInvalide("commande vide")
    args = shlex.split(commande)
    if not args:
        raise CommandeInvalide("commande vide")
    for token in args:
        if token in OPERATEURS_DE_SHELL:
            raise CommandeInvalide(
                f"« {token} » demande un shell, et l'IDE n'en utilise pas : "
                "déclare un service par commande dans `services`."
            )
    return args


def resoudre_le_cwd(racine: Path, cwd: Optional[str]) -> Path:
    """Le dossier de travail, refusé s'il sort du périmètre du projet.

    Même frontière qu'ADR-031 : ce que l'IDE lance ne travaille pas chez le
    voisin. Six dépôts clients côte à côte, et un `cwd` mal écrit démarre un
    serveur dans le mauvais.

    Le périmètre vient de `racine_autorisee`, qui porte déjà l'exception
    d'ADR-028 : un projet déclarant `git_root: ancestor` travaille dans le
    dépôt qui le contient — c'est ce que fait le projet bootstrap, dont le
    code est dans `backend/` et `frontend/`, au-dessus de lui. Réécrire cette
    résolution ici donnerait deux contrôles de périmètre, et c'est celui qu'on
    regarde le moins qui laisserait passer (ADR-034, ticket-143).
    """
    permise = racine_autorisee(racine)
    depart = racine.resolve()
    cible = (depart / (cwd or ".")).resolve()
    if cible != permise and permise not in cible.parents:
        raise CommandeInvalide(
            f"`cwd` sort du périmètre du projet : {cwd!r}"
        )
    return cible


def introuvable(programme: str) -> str:
    """Le message d'un exécutable qui ne se résout pas.

    Sans shell, `npm` n'existe pas sous Windows : c'est `npm.cmd`, et l'erreur
    brute — « fichier introuvable » — n'aide personne à le deviner. Le prix de
    ne pas passer par un shell (ADR-042) est de devoir nommer le programme
    exactement ; autant le dire.
    """
    message = f"« {programme} » est introuvable."
    if os.name == "nt" and not programme.lower().endswith((".cmd", ".bat", ".exe")):
        message += (
            f" Sous Windows et sans shell, essaie « {programme}.cmd » : "
            "npm, npx et yarn y sont des scripts, pas des exécutables."
        )
    return message


class ProcessRegistry:
    """Les services vivants, par projet."""

    def __init__(self) -> None:
        self._services: dict[str, list[Service]] = {}

    def services_de(self, project_id: str) -> list[Service]:
        """Tous les services enregistrés, **y compris ceux qui sont morts**.

        Filtrer sur `en_cours` les faisait disparaître : au premier essai
        réel, le backend d'`ide-core` mourait sur un port déjà pris et sortait
        de la liste, si bien que le lancement paraissait à moitié réussi sans
        rien dire du reste (ticket-144). `en_cours` et `code_de_sortie` disent
        lequel est lequel — c'est ce que l'affichage attend.
        """
        return list(self._services.get(project_id, []))

    def instantane(self) -> list[dict[str, Any]]:
        return [
            service.en_dict()
            for services in self._services.values()
            for service in services
        ]

    async def demarrer(
        self,
        project_id: str,
        nom: str,
        commande: str,
        racine: Path,
        cwd: Optional[str] = None,
        sur_ligne: Any = None,
        sur_fin: Any = None,
    ) -> Service:
        """Lance une commande déclarée, sans shell, sous la racine du projet.

        Refuse si ce service tourne déjà : deux lancements de suite laissaient
        douze processus là où trois suffisent, et la liste n'en montrait qu'un
        (ticket-153). L'interface l'empêchait en affichant « Arrêter », mais
        une protection qui ne vit que dans l'affichage n'en est pas une.
        """
        deja = next(
            (s for s in self.services_de(project_id) if s.nom == nom and s.en_cours),
            None,
        )
        if deja is not None:
            raise ServiceDejaEnCours(nom, deja.pid)

        args = verifier_la_commande(commande)
        dossier = resoudre_le_cwd(racine, cwd)

        try:
            processus = await self._lancer(args, dossier)
        except FileNotFoundError as exc:
            raise CommandeInvalide(introuvable(args[0])) from exc
        # Deux filets, pour deux pannes différentes : le groupe global tue
        # tout si le backend meurt (ticket-150) ; le groupe du service permet
        # de tuer son seul arbre à l'arrêt (ticket-153).
        rattacher(processus.pid)
        groupe = creer_groupe()
        if groupe is not None:
            rattacher_au_groupe(groupe, processus.pid)

        service = Service(
            nom=nom,
            project_id=project_id,
            pid=processus.pid,
            processus=processus,
            groupe=groupe,
        )
        # Purger l'entrée terminée du même nom : garder les morts ne doit pas
        # faire grossir la liste à chaque clic sur « Relancer ».
        restants = [
            s
            for s in self._services.get(project_id, [])
            if s.nom != nom or s.en_cours
        ]
        restants.append(service)
        self._services[project_id] = restants

        if sur_ligne is not None or sur_fin is not None:
            # La lecture tourne à côté : sans elle, le tube se remplit et le
            # service se bloque sur son propre `print` au bout de quelques
            # kilo-octets.
            asyncio.create_task(self._suivre(service, sur_ligne, sur_fin))
        return service

    async def _lancer(self, args: list[str], dossier: Path) -> Any:
        """Lance les arguments, en essayant l'équivalent Windows au besoin.

        `npm`, `npx` et `yarn` sont des scripts sous Windows : sans shell,
        seul `npm.cmd` se résout. Écrire `npm.cmd` dans un `agents.json`
        marcherait ici et nulle part ailleurs — or ce fichier est versionné et
        part sur d'autres machines. Le manifeste reste donc portable, et c'est
        le lancement qui s'adapte (ticket-143).
        """
        essais = [args]
        if os.name == "nt" and not args[0].lower().endswith(
            (".cmd", ".bat", ".exe")
        ):
            essais.append([args[0] + ".cmd", *args[1:]])

        derniere: FileNotFoundError | None = None
        for tentative in essais:
            try:
                return await asyncio.create_subprocess_exec(
                    *tentative,
                    cwd=str(dossier),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    # Son propre groupe, hors Windows : c'est ce qui rend
                    # `killpg` sûr à l'arrêt. Sans lui, le service hérite du
                    # groupe du backend, et l'arrêter emporterait le backend
                    # (ticket-153).
                    start_new_session=os.name != "nt",
                )
            except FileNotFoundError as exc:
                derniere = exc
        raise derniere if derniere else FileNotFoundError(args[0])

    async def _suivre(
        self, service: Service, sur_ligne: Any, sur_fin: Any
    ) -> None:
        """Relaie la sortie, puis annonce la fin.

        Le flux qui se ferme dit que le processus n'écrit plus, pas qu'il est
        terminé : `wait()` derrière donne le code de sortie, et c'est lui qui
        distingue « arrêté » de « mort tout seul » à l'écran (ticket-145).
        """
        flux = service.processus.stdout if service.processus else None
        try:
            while flux is not None:
                ligne = await flux.readline()
                if not ligne:
                    break
                texte = sans_couleurs(ligne.decode("utf-8", "replace")).rstrip()
                service.noter(texte)
                if sur_ligne is not None:
                    await sur_ligne(service, texte)
        except Exception as exc:  # noqa: BLE001 — lire ne doit rien casser
            _logger.warning("lecture_service_interrompue", extra={"erreur": str(exc)})

        try:
            if service.processus is not None:
                await service.processus.wait()
            if sur_fin is not None:
                await sur_fin(service)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("fin_service_non_annoncee", extra={"erreur": str(exc)})

    async def arreter(self, project_id: str) -> int:
        """Arrête les services d'un projet, **en gardant leur trace**.

        Les retirer effaçait tout — pid, code de sortie, sortie conservée — et
        `GET /services` reconstruisait alors le service déclaré de zéro, sans
        pid : l'écran affichait « pas lancé par l'IDE » pour un service qu'on
        venait d'arrêter soi-même (ticket-151).

        ticket-144 avait posé qu'un service mort reste visible. La règle valait
        pour celui qui meurt seul ; les deux chemins la suivent maintenant.
        """
        services = self._services.get(project_id, [])
        vivants = [service for service in services if service.en_cours]
        for service in vivants:
            service.arrete_a_la_main = True
            await self._terminer(service)
        return len(vivants)

    async def tout_arreter(self) -> int:
        """Arrête tout et **oublie tout** — le backend s'éteint.

        Distinct d'`arreter()`, qui garde la trace pour l'afficher : ici il
        n'y aura personne pour la lire, et le registre suivant repartira de
        zéro de toute façon (ticket-151).
        """
        total = 0
        for project_id in list(self._services):
            total += await self.arreter(project_id)
        self._services.clear()
        return total

    async def _terminer(self, service: Service) -> None:
        processus = service.processus
        if processus is None or processus.returncode is not None:
            return
        try:
            # L'arbre entier, pas le seul parent : `npm run dev` lance
            # `concurrently`, qui lance deux serveurs. `terminate()` frappait
            # le premier maillon et laissait les descendants avec leurs ports
            # — « 2 arrêtés » pendant que douze processus tournaient
            # (ticket-153).
            # Le groupe d'abord : il emporte la descendance que `taskkill`
            # ne retrouve plus quand un maillon a disparu.
            if service.groupe is not None:
                fermer_le_groupe(service.groupe)
                service.groupe = None
            await tuer_l_arbre(processus.pid)
            processus.terminate()
            await asyncio.wait_for(processus.wait(), timeout=DELAI_D_ARRET_S)
        except asyncio.TimeoutError:
            # Un service qui ignore `terminate` garderait son port : le tuer
            # est moins grave que de le laisser derrière soi.
            processus.kill()
            await processus.wait()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("arret_service_echoue", extra={"erreur": str(exc)})


#: L'instance que les routeurs partagent, comme `RUN_LOCK` et `EVENT_HUB`.
PROCESS_REGISTRY = ProcessRegistry()
