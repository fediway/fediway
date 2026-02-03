import re


def camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(name: str) -> str:
    return "".join(word.capitalize() for word in name.split("_"))


def humanize(name: str) -> str:
    return name.replace("_", " ").title()
