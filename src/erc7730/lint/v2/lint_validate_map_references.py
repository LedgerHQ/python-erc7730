"""
V2 linter that checks the map references keyed by the chain ID.

The ERC-7730 specification says that a wallet must consider the descriptor invalid when no map value matches the key.
A map keyed by ``@.chainId`` is resolved with the chain of the transaction, so it must have a value for each
deployment chain. Resolution already validates the map values themselves.
"""

from collections.abc import Iterator
from typing import final, override

from erc7730.common.output import OutputAdder
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.paths import ContainerField, ContainerPath
from erc7730.model.resolved.v2.context import ResolvedContractContext
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import ResolvedField, ResolvedFieldDescription, ResolvedMapReference

MISSING_MAP_VALUE_TITLE = "Missing map value"

CHAIN_ID_PATH = ContainerPath(field=ContainerField.CHAIN_ID)


@final
class ValidateMapReferencesLinter(ERC7730Linter):
    """Reports maps keyed by ``@.chainId`` that have no value for a deployment chain."""

    @override
    def lint(
        self, input_descriptor: InputERC7730Descriptor, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> None:
        context = descriptor.context
        deployments = (
            context.contract.deployments if isinstance(context, ResolvedContractContext) else context.eip712.deployments
        )
        maps = descriptor.metadata.maps or {}

        reported: set[tuple[str, int]] = set()
        for fmt in descriptor.display.formats.values():
            for map_ref in _map_references(fmt.fields):
                if map_ref.keyPath != CHAIN_ID_PATH:
                    continue
                if (map_def := maps.get(str(map_ref.map).split(".")[-1])) is None:
                    continue  # resolution reports an unknown map
                for deployment in deployments:
                    if str(deployment.chainId) in map_def.values or (str(map_ref.map), deployment.chainId) in reported:
                        continue
                    reported.add((str(map_ref.map), deployment.chainId))
                    out.error(
                        title=MISSING_MAP_VALUE_TITLE,
                        message=f"Map {map_ref.map} is keyed by {CHAIN_ID_PATH}, but it has no value for deployment "
                        f"chain {deployment.chainId}. Add a value for this chain, or the descriptor is invalid on it.",
                    )


def _map_references(fields: list[ResolvedField]) -> Iterator[ResolvedMapReference]:
    for field in fields:
        if not isinstance(field, ResolvedFieldDescription):
            yield from _map_references(field.fields)
        elif field.params is not None:
            for name in type(field.params).model_fields:
                if isinstance(value := getattr(field.params, name), ResolvedMapReference):
                    yield value
