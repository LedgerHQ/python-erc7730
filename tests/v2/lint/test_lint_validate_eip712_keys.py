import pytest

from erc7730.common.output import ListOutputAdder
from erc7730.lint.v2.lint_validate_eip712_keys import validate_eip712_key

VALID_KEYS = [
    "Mail(Person from,Person to,string contents)Person(string name,address wallet)",
    "PermitBatch(PermitDetails[] details,address spender,uint256 sigDeadline)"
    "PermitDetails(address token,uint160 amount,uint48 expiration,uint48 nonce)",
    "Empty()",
    "Simple(uint256 value)",
    "Bytes(bytes1 a,bytes32 b,bytes c,string d,bool e,address f,int8 g,int256 h)",
    "Arrays(uint256[] a,uint256[2] b,uint256[2][] c)",
    "Weird$Type_1(uint256 _value$1)",
    # dependent types sorted by name, transitively referenced
    "Root(A a)A(B b)B(uint256 c)",
    # colon namespaced type names, as used by Hyperliquid in the registry
    "HyperliquidTransaction:Withdraw(string hyperliquidChain,string destination,string amount,uint64 time)",
    "Root(Ns:Dep d)Ns:Dep(uint256 a)",
]

INVALID_KEYS = [
    # not an encodeType string at all
    ("TestMessage", "Invalid EIP-712 key"),
    ("Mail(string contents", "Invalid EIP-712 key"),
    ("Mail string contents)", "Invalid EIP-712 key"),
    ("1Mail(string contents)", "Invalid EIP-712 key"),
    ("", "Invalid EIP-712 key"),
    # whitespace
    (" Mail(string contents)", "Invalid EIP-712 key"),
    ("Mail(string contents) ", "Invalid EIP-712 key"),
    ("Mail(Person from)  Person(string name)", "Invalid EIP-712 key"),
    ("Mail(string  contents)", "Invalid EIP-712 key"),
    ("Mail( string contents)", "Invalid EIP-712 key"),
    ("Mail(string contents )", "Invalid EIP-712 key"),
    ("Mail(string contents, address to)", "Invalid EIP-712 key"),
    ("Mail(string)", "Invalid EIP-712 key"),
    # malformed colon namespacing
    (":Mail(string contents)", "Invalid EIP-712 key"),
    ("Mail:(string contents)", "Invalid EIP-712 key"),
    ("Ns::Mail(string contents)", "Invalid EIP-712 key"),
    # duplicates
    ("Mail(Person a)Person(string n)Person(string n)", "Duplicate type in EIP-712 key"),
    ("Mail(string a,uint256 a)", "Duplicate member in EIP-712 key"),
    # invalid atomic types
    ("Mail(uint value)", "Invalid type in EIP-712 key"),
    ("Mail(int value)", "Invalid type in EIP-712 key"),
    ("Mail(byte value)", "Invalid type in EIP-712 key"),
    ("Mail(uint7 value)", "Invalid type in EIP-712 key"),
    ("Mail(uint264 value)", "Invalid type in EIP-712 key"),
    ("Mail(bytes0 value)", "Invalid type in EIP-712 key"),
    ("Mail(bytes33 value)", "Invalid type in EIP-712 key"),
    ("Mail(fixed128x18 value)", "Invalid type in EIP-712 key"),
    # undefined struct types
    ("Mail(Person from)", "Undefined type in EIP-712 key"),
    ("Mail(Person[] from)", "Undefined type in EIP-712 key"),
    # unused struct types
    ("Mail(string contents)Person(string name)", "Unused type in EIP-712 key"),
    # ordering
    ("Mail(Person from,Wallet to)Wallet(address a)Person(string n)", "Invalid type order in EIP-712 key"),
]


@pytest.mark.parametrize("key", VALID_KEYS)
def test_valid_keys(key: str) -> None:
    out = ListOutputAdder()
    validate_eip712_key(key, out)
    assert out.outputs == []


@pytest.mark.parametrize("key,title", INVALID_KEYS, ids=[key for key, _ in INVALID_KEYS])
def test_invalid_keys(key: str, title: str) -> None:
    out = ListOutputAdder()
    validate_eip712_key(key, out)
    assert [output.title for output in out.outputs] == [title]
