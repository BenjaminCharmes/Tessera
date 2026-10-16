from pydantic import ValidationError


class ConfigurationError(RuntimeError):
    """Raised at startup when the settings cannot be built.

    The message names the faulty variables and never carries their values.
    """


def _variable_name(location: tuple[int | str, ...]) -> str:
    """Return the environment variable name for a pydantic error location."""
    return ".".join(str(part) for part in location).upper()


def describe_validation_error(error: ValidationError) -> str:
    """Rewrite a settings validation error without echoing any input value.

    Only the variable name and the pydantic error type are read: the message
    and the input of each error can quote what the user typed, which may be a
    token.
    """
    lines: list[str] = []
    for detail in error.errors():
        name = _variable_name(detail["loc"])
        if detail["type"] == "extra_forbidden":
            lines.append(
                f"variable inconnue dans .env : {name} "
                "(à retirer, ou à renommer si c'est un jeton de mise en ligne)"
            )
        else:
            lines.append(
                f"valeur invalide pour {name} dans .env "
                f"(erreur : {detail['type']}) — à corriger"
            )
    return "Configuration invalide :\n" + "\n".join(f"- {line}" for line in lines)
