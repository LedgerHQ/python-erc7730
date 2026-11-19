from pydantic import RootModel, ValidationError

from erc7730.common.output import ListOutputAdder, Output
from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import erc7730_v2_descriptor_to_calldata_descriptors
from erc7730.model.calldata.descriptor import CalldataDescriptor
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.serve.v2.model import Compiled, CompileResult, ConversionFailed, Diagnostic, InvalidDescriptor


def compile_json(body: bytes) -> CompileResult:
    descriptor = parse_descriptor(body)
    if isinstance(descriptor, InvalidDescriptor):
        return descriptor
    return compile_calldata(descriptor)


def parse_descriptor(body: bytes) -> InputERC7730Descriptor | InvalidDescriptor:
    try:
        return InputERC7730Descriptor.model_validate_json(body, strict=False)
    except ValidationError as e:
        return InvalidDescriptor(_errors(e))


def compile_calldata(descriptor: InputERC7730Descriptor) -> CompileResult:
    out = ListOutputAdder()
    descriptors = erc7730_v2_descriptor_to_calldata_descriptors(descriptor, out=out)
    diagnostics = tuple(
        Diagnostic(level=o.level.name.lower(), title=o.title, message=o.message)
        for o in out.outputs
        if o.level >= Output.Level.WARNING
    )
    if out.has_errors:
        return ConversionFailed(diagnostics)
    # the TLV encoding of calldata descriptors only accepts ASCII, and only runs during serialization
    try:
        payload = RootModel[list[CalldataDescriptor]](descriptors).model_dump(mode="json", exclude_none=True)
    except UnicodeEncodeError as e:
        return InvalidDescriptor(f"calldata descriptors only accept ASCII text: {e.object[e.start : e.end]!r}")
    return Compiled(tuple(payload), diagnostics)


def _errors(e: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(map(str, err['loc']))}: {err['msg']}" if err["loc"] else err["msg"] for err in e.errors()
    )
