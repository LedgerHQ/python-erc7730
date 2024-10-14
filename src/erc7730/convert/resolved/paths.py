from erc7730.model.path import DescriptorPath


def strip_prefix(path: DescriptorPath, prefix: DescriptorPath) -> DescriptorPath:
    if len(path.elements) < len(prefix.elements):
        raise ValueError(f"Path {path} does not start with prefix {prefix}.")
    for i, element in enumerate(prefix.elements):
        if path.elements[i] != element:
            raise ValueError(f"Path {path} does not start with prefix {prefix}.")
    return DescriptorPath(elements=path.elements[len(prefix.elements) :])
