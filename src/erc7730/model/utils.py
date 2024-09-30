import requests
from pydantic import AnyUrl, RootModel

from erc7730.model.abi import ABI
from erc7730.model.context import ContractContext, Deployments, EIP712Context, EIP712JsonSchema
from erc7730.model.descriptor import ERC7730Descriptor


def get_chain_ids(descriptor: ERC7730Descriptor) -> set[int] | None:
    """Get deployment chaind ids for a descriptor."""
    if (deployments := get_deployments(descriptor)) is None:
        return None
    return {d.chainId for d in deployments.root if d.chainId is not None}


def get_deployments(descriptor: ERC7730Descriptor) -> Deployments | None:
    """Get deployments section for a descriptor."""
    if isinstance(context := descriptor.context, EIP712Context):
        return context.eip712.deployments
    if isinstance(context := descriptor.context, ContractContext):
        return context.contract.deployments
    raise ValueError(f"Invalid context type {type(descriptor.context)}")


def resolve_external_references(descriptor: ERC7730Descriptor) -> ERC7730Descriptor:
    if isinstance(descriptor.context, EIP712Context):
        return _resolve_external_references_eip712(descriptor)
    if isinstance(descriptor.context, ContractContext):
        return _resolve_external_references_contract(descriptor)
    raise ValueError("Invalid context type")


def _resolve_external_references_eip712(descriptor: ERC7730Descriptor) -> ERC7730Descriptor:
    schemas: list[EIP712JsonSchema | AnyUrl] = descriptor.context.eip712.schemas  # type:ignore
    schemas_resolved = []
    for schema in schemas:
        if isinstance(schemas, AnyUrl):
            resp = requests.get(_adapt_uri(schema), timeout=10)  # type:ignore
            resp.raise_for_status()
            model: type[RootModel[EIP712JsonSchema]] = RootModel[EIP712JsonSchema]
            json = resp.json()
            schema_resolved = model.model_validate(json).root
        else:
            schema_resolved = schema  # type:ignore
        schemas_resolved.append(schema_resolved)
    return descriptor.model_copy(
        update={
            "context": descriptor.context.model_copy(  # type:ignore
                update={"eip712": descriptor.context.eip712.model_copy(update={"schemas": schemas_resolved})}  # type:ignore
            )
        }
    )


def _resolve_external_references_contract(descriptor: ERC7730Descriptor) -> ERC7730Descriptor:
    abis: AnyUrl | list[ABI] = descriptor.context.contract.abi  # type:ignore
    if isinstance(abis, AnyUrl):
        resp = requests.get(_adapt_uri(abis), timeout=10)  # type:ignore
        resp.raise_for_status()
        json = resp.json()
        model: type[RootModel[list[ABI]]] = RootModel[list[ABI]]
        abis_resolved = model.model_validate(json).root
    else:
        abis_resolved = abis
    return descriptor.model_copy(
        update={
            "context": descriptor.context.model_copy(  # type:ignore
                update={"contract": descriptor.context.contract.model_copy(update={"abi": abis_resolved})}  # type:ignore
            )
        }
    )


def _adapt_uri(url: AnyUrl) -> AnyUrl:
    return AnyUrl(str(url).replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/"))
