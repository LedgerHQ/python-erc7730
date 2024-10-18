from erc7730.model.paths import (
    ROOT_DATA_PATH,
    DataPath,
    DataPathElement,
    DescriptorPath,
    DescriptorPathElement,
)


def descriptor_path_strip_prefix(path: DescriptorPath, prefix: DescriptorPath) -> DescriptorPath:
    """
    Strip expected prefix from a descriptor path, raising an error if the prefix is not matching.

    :param path: path to strip
    :param prefix: prefix to strip
    :return: path without prefix
    :raises ValueError: if the path does not start with the prefix
    """
    if len(path.elements) < len(prefix.elements):
        raise ValueError(f"Path {path} does not start with prefix {prefix}.")
    for i, element in enumerate(prefix.elements):
        if path.elements[i] != element:
            raise ValueError(f"Path {path} does not start with prefix {prefix}.")
    return DescriptorPath(elements=path.elements[len(prefix.elements) :])


def data_path_strip_prefix(path: DataPath, prefix: DataPath) -> DataPath:
    """
    Strip expected prefix from a data path, raising an error if the prefix is not matching.

    :param path: path to strip
    :param prefix: prefix to strip
    :return: path without prefix
    :raises ValueError: if the path does not start with the prefix
    """
    if path.absolute != prefix.absolute or len(path.elements) < len(prefix.elements):
        raise ValueError(f"Path {path} does not start with prefix {prefix}.")
    for i, element in enumerate(prefix.elements):
        if path.elements[i] != element:
            raise ValueError(f"Path {path} does not start with prefix {prefix}.")
    return DataPath(absolute=path.absolute, elements=path.elements[len(prefix.elements) :])


def descriptor_path_starts_with(path: DescriptorPath, prefix: DescriptorPath) -> bool:
    """
    Check if descriptor path starts with a given prefix.

    :param path: path to inspect
    :param prefix: prefix to check
    :return: True if path starts with prefix
    """
    try:
        descriptor_path_strip_prefix(path, prefix)
        return True
    except ValueError:
        return False


def data_path_starts_with(path: DataPath, prefix: DataPath) -> bool:
    """
    Check if data path starts with a given prefix.

    :param path: path to inspect
    :param prefix: prefix to check
    :return: True if path starts with prefix
    """
    try:
        data_path_strip_prefix(path, prefix)
        return True
    except ValueError:
        return False


def descriptor_path_ends_with(path: DescriptorPath, suffix: DescriptorPathElement) -> bool:
    """
    Check if descriptor path ends with a given element.

    :param path: path to inspect
    :param suffix: suffix to check
    :return: True if path ends with suffix
    """
    return path.elements[-1] == suffix


def data_path_ends_with(path: DataPath, suffix: DataPathElement) -> bool:
    """
    Check if data path ends with a given element.

    :param path: path to inspect
    :param suffix: suffix to check
    :return: True if path ends with suffix
    """
    if not path.elements:
        return False
    return path.elements[-1] == suffix


def data_path_concat(parent: DataPath | None, child: DataPath) -> DataPath:
    """
    Concatenate two data paths.

    :param parent: parent path
    :param child: child path
    :return: concatenated path
    """
    if parent is None or child.absolute:
        return child
    return DataPath(absolute=parent.absolute, elements=[*parent.elements, *child.elements])


def data_path_append(parent: DataPath, child: DataPathElement) -> DataPath:
    """
    Concatenate two data paths.

    :param parent: parent path
    :param child: child path
    :return: concatenated path
    """
    return parent.model_copy(update={"elements": [*parent.elements, child]})


def data_path_as_root(path: DataPath) -> DataPath:
    """
    Convert a data path to an absolute path.

    :param path: data path
    :return: absolute path
    """
    return data_path_concat(ROOT_DATA_PATH, path)
