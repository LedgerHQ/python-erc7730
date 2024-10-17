from erc7730.model.path import DataPath, DataPathElement, DescriptorPath



def strip_prefix(path: DescriptorPath, prefix: DescriptorPath) -> DescriptorPath:
    """
    Strip expected prefix from a descriptor, raising an error if the prefix is not matching.

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


def concat_data_path(parent: DataPath, child: DataPath) -> DataPath:
    """
    Concatenate two data paths.

    :param parent: parent path
    :param child: child path
    :return: concatenated path
    """
    raise NotImplementedError()


def append_data_path(parent: DataPath, child: DataPathElement) -> DataPath:
    """
    Concatenate two data paths.

    :param parent: parent path
    :param child: child path
    :return: concatenated path
    """
    return parent.model_copy(update={"elements": parent.elements + [child]})
