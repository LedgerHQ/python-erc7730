from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import (
    erc7730_v2_descriptor_to_calldata_descriptors,
)
from erc7730.convert.calldata.v1.tlv import tlv_field
from erc7730.model.calldata.v1.param import (
    CalldataDescriptorParamTokenV1,
    CalldataDescriptorParamType,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

TOKEN_TICKER_DESCRIPTOR = """
{
  "$schema": "specs/erc7730-v2.schema.json",
  "context": {
    "$id": "token-ticker-test",
    "contract": {
      "deployments": [
        { "chainId": 1, "address": "0x0000000000000000000000000000000000000001" }
      ]
    }
  },
  "metadata": { "owner": "Test Owner" },
  "display": {
    "formats": {
      "getTokenTicker(address token)": {
        "intent": "Get token ticker",
        "fields": [
          { "path": "token", "label": "Token", "format": "tokenTicker" }
        ]
      }
    }
  }
}
"""


def test_convert_token_ticker() -> None:
    descriptor = InputERC7730Descriptor.model_validate_json(TOKEN_TICKER_DESCRIPTOR)

    descriptors = erc7730_v2_descriptor_to_calldata_descriptors(descriptor, chain_id=1)

    assert len(descriptors) == 1
    fields = descriptors[0].fields
    assert len(fields) == 1

    field = fields[0]
    assert field.name == "Token"
    assert isinstance(field.param, CalldataDescriptorParamTokenV1)
    assert field.param.native_currencies is None

    # PARAM_TYPE tag (0x02) must serialize the TOKEN parameter type (0x0a)
    tlv = tlv_field(field)
    assert bytes([0x02, 0x01, CalldataDescriptorParamType.TOKEN]) in tlv
