from erc7730.common.abi import compute_signature
from erc7730.common.client import get_contract_abis
from erc7730.model.abi import Function, InputOutput
from erc7730.model.context import Deployment
from erc7730.model.display import FieldFormat
from erc7730.model.input.context import InputContract, InputContractContext
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import InputDisplay, InputField, InputFieldDescription, InputFormat
from erc7730.model.metadata import Metadata
from erc7730.model.types import ContractAddress


def generate_contract(chain_id: int, contract_address: ContractAddress) -> InputERC7730Descriptor:
    """
    Generate an ERC-7730 descriptor for the given contract address.

    :param chain_id: contract chain id
    :param contract_address: contract address
    :return: a generated ERC-7730 descriptor
    """
    if (abis := get_contract_abis(chain_id, contract_address)) is None:
        raise Exception("Failed to fetch contract ABIs")

    return InputERC7730Descriptor(
        context=InputContractContext(
            contract=InputContract(
                abi=abis,
                deployments=[Deployment(chainId=chain_id, address=contract_address)],
            )
        ),
        metadata=Metadata(),
        display=InputDisplay(
            formats={
                compute_signature(abi): InputFormat(fields=_generate_abi_fields(abi))
                for abi in abis
                if isinstance(abi, Function)
            }
        ),
    )


def _generate_abi_fields(function: Function) -> list[InputField]:
    if not (inputs := function.inputs):
        return []
    return [_generate_abi_field(input) for input in inputs]


def _generate_abi_field(input: InputOutput) -> InputField:
    # TODO must recursive into ABI types
    return InputFieldDescription(
        path=input.name,
        label=input.name,
        format=FieldFormat.RAW,  # TODO adapt format based on type
    )
