import re


def snakify(name: str) -> str:
    """Convert camel case to snake case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def camelify(name: str) -> str:
    """Convert snake case to camel case."""
    return "".join(word.title() for word in name.split("_"))
