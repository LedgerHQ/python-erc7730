from typing import Any


def has_property(target: Any, name: str) -> bool:
    """
    Check if the target has a property with the given name.

    :param target: object of dict like
    :param name: attribute name
    :return: true if the target has the property
    """
    if isinstance(target, dict):
        return name in target
    return hasattr(target, name)


def get_property(target: Any, name: str) -> Any:
    """
    Get the property with the given name on target object.

    :param target: object of dict like
    :param name: attribute name
    :return: value for property on target object
    """
    if isinstance(target, dict):
        return target[name]
    return getattr(target, name)
