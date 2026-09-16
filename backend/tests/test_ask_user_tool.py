"""Outil `ask_user` expose aux agents du pipeline — ticket-066."""
from vibe_ide.services.providers.ask_user import (
    ASK_USER_TOOL_NAME,
    build_ask_user_server,
    build_ask_user_tool,
)


def _texte(resultat: dict[str, object]) -> str:
    blocs = resultat.get("content", [])
    return " ".join(b.get("text", "") for b in blocs)  # type: ignore[union-attr]


async def test_l_outil_relaie_la_question_et_rend_la_reponse() -> None:
    demandees: list[str] = []

    async def _demander(question: str) -> str:
        demandees.append(question)
        return "utilise ISO 8601"

    outil = build_ask_user_tool(_demander)
    resultat = await outil.handler({"question": "Quel format de date ?"})

    assert demandees == ["Quel format de date ?"]
    assert "utilise ISO 8601" in _texte(resultat)


async def test_une_question_vide_est_refusee_sans_suspendre_le_run() -> None:
    # Un agent qui appelle l'outil sans question suspendrait le run sur un
    # ecran vide, que personne ne saurait quoi repondre.
    appels: list[str] = []

    async def _demander(question: str) -> str:
        appels.append(question)
        return "jamais"

    outil = build_ask_user_tool(_demander)
    resultat = await outil.handler({"question": "   "})

    assert appels == []
    assert "question" in _texte(resultat).lower()


def test_le_nom_qualifie_est_celui_attendu_par_le_sdk() -> None:
    # Ce nom est ce qui doit figurer dans `allowed_tools` : s'il diverge, le
    # SDK expose l'outil mais en refuse l'appel.
    assert ASK_USER_TOOL_NAME == "mcp__vibe_ide__ask_user"


def test_le_serveur_expose_l_outil() -> None:
    async def _demander(question: str) -> str:
        return "oui"

    serveur = build_ask_user_server(_demander)

    assert serveur["type"] == "sdk"
    assert serveur["name"] == "vibe_ide"


# ------------------------------------------------------------------
# Integration dans les options du SDK
# ------------------------------------------------------------------


def test_sans_canal_l_outil_n_est_pas_expose() -> None:
    # Donner `ask_user` a un run sans canal branche promettrait a l'agent une
    # reponse que personne ne pourrait lui apporter : il attendrait le delai
    # complet a chaque question, pour rien.
    from vibe_ide.services.providers.agent_sdk import _build_options

    options = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read"],
    )

    assert options.mcp_servers == {}
    assert ASK_USER_TOOL_NAME not in (options.allowed_tools or [])


def test_avec_un_canal_l_outil_est_expose_et_autorise() -> None:
    # Le nom qualifie doit etre dans `allowed_tools` *et* dans `tools` : sans
    # les deux, le SDK expose l'outil puis en refuse l'appel.
    from vibe_ide.services.providers.agent_sdk import _build_options

    async def _demander(question: str) -> str:
        return "oui"

    options = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read"], ask_user=_demander,
    )

    assert "vibe_ide" in options.mcp_servers
    assert ASK_USER_TOOL_NAME in (options.allowed_tools or [])
    assert ASK_USER_TOOL_NAME in (options.tools or [])
