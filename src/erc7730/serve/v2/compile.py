import json

from pydantic import RootModel, ValidationError
from pydantic_string_url import HttpUrl

from erc7730.common.output import ListOutputAdder, Output
from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import erc7730_v2_descriptor_to_calldata_descriptors
from erc7730.model.calldata.descriptor import CalldataDescriptor
from erc7730.model.input.v2.context import InputContractContext
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.serve.v2.model import Compiled, CompileResult, ConversionFailed, Diagnostic, InvalidDescriptor

MAX_GENERATED_ITEMS = 10_000


def compile_json(body: bytes) -> CompileResult:
    descriptor = parse_descriptor(body)
    if isinstance(descriptor, InvalidDescriptor):
        return descriptor
    return compile_calldata(descriptor)


def parse_descriptor(body: bytes) -> InputERC7730Descriptor | InvalidDescriptor:
    try:
        data = json.loads(body)
    except ValueError as e:
        return InvalidDescriptor(f"Invalid JSON: {e}")
    # the TLV encoding of calldata descriptors only accepts ASCII
    text = json.dumps(data, ensure_ascii=False)
    if not text.isascii():
        return InvalidDescriptor(
            f"descriptors only accept ASCII text, found {next(c for c in text if not c.isascii())!r}"
        )
    try:
        descriptor = InputERC7730Descriptor.model_validate(data, strict=False)
    except ValidationError as e:
        return InvalidDescriptor(_errors(e))
    if descriptor.includes is not None:
        return InvalidDescriptor("includes: not supported, send the merged descriptor")
    if remote := sorted(name for name, enum in (descriptor.metadata.enums or {}).items() if isinstance(enum, HttpUrl)):
        return InvalidDescriptor(f"metadata.enums: remote enums are not supported: {', '.join(remote)}")
    if (items := _generated_items(descriptor)) > MAX_GENERATED_ITEMS:
        return InvalidDescriptor(
            f"descriptor too large: it would generate {items} items, the limit is {MAX_GENERATED_ITEMS}"
        )
    return descriptor


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
    # TLV lengths fit in one byte, and the TLV is only encoded during serialization
    try:
        payload = RootModel[list[CalldataDescriptor]](descriptors).model_dump(mode="json", exclude_none=True)
    except OverflowError:
        return InvalidDescriptor("a text is too long for the calldata TLV encoding")
    return Compiled(tuple(payload), diagnostics)


# the converter builds one calldata descriptor per deployment and format, each with a copy of every enum entry
def _generated_items(descriptor: InputERC7730Descriptor) -> int:
    context = descriptor.context
    deployments = len(context.contract.deployments) if isinstance(context, InputContractContext) else 0
    enum_entries = sum(len(enum) for enum in (descriptor.metadata.enums or {}).values() if isinstance(enum, dict))
    return deployments * len(descriptor.display.formats) * (1 + enum_entries)


def _errors(e: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(map(str, err['loc']))}: {err['msg']}" if err["loc"] else err["msg"] for err in e.errors()
    )
