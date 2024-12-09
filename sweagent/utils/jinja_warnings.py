from sweagent.utils.log import get_logger


def _warn_probably_wrong_jinja_syntax(template: str | None) -> None:
    """Warn if the template uses {var} instead of {{var}}."""
    if template is None:
        return
    if "{" not in template:
        return
    for s in ["{%", "{ %", "{{"]:
        if s in template:
            return
    logger = get_logger("swea-config", emoji="🔧")
    logger.warning("Probably wrong Jinja syntax in template: %s. Make sure to use {{var}} instead of {var}.", template)
