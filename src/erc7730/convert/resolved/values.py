from erc7730.common.output import OutputAdder
from erc7730.convert.resolved.constants import ConstantProvider
from erc7730.model.input.display import InputFieldBase
from erc7730.model.paths import DataPath
from erc7730.model.paths.path_ops import data_or_container_path_concat
from erc7730.model.resolved.display import ResolvedValue, ResolvedValueConstant, ResolvedValuePath


def resolve_value(
    prefix: DataPath,
    input_field: InputFieldBase,
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedValue | None:
    if (input_path := input_field.path) is not None:
        if input_field.value is not None:
            return out.error(
                title="Invalid field",
                message="Field cannot have both a path and a value.",
            )

        if (path := constants.resolve_path(input_path, out)) is None:
            return None

        return ResolvedValuePath(path=data_or_container_path_concat(prefix, path))

    if (input_value := input_field.value) is not None:
        if (value := constants.resolve(input_value, out)) is None:
            return None

        if not isinstance(value, str | bool | int | float):
            return out.error(
                title="Invalid constant value",
                message="Constant value must be a scalar type (string, boolean or number).",
            )

        return ResolvedValueConstant(value=value)

    return out.error(title="Invalid field", message="Field must have either a path or a value.")
