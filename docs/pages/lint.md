# Linter checks list
## ABI checks
The reference ABI is fetched from Sourcify for each deployment. In v2, the descriptor carries no ABI: its functions are the `display.formats` keys, and the display fields checks below validate them against the reference ABI. The "Extra function" and "Function mismatch" checks compare the ABI embedded in a v1 descriptor against the reference ABI, so they only apply to v1 descriptors.

The four "not verified" / "not supported" / "could not fetch" checks below are reported as errors instead when `--require-verified` is passed, so that a strict run never passes without having checked every deployment.

### Contract not verified
- **Level**: ⚠️ Warning 
- **Message**: `contract <address> on chain <chain_id> is not verified on Sourcify, descriptor ABIs will not be validated`
- **Description**: The contract is not verified on Sourcify, so there is no reference ABI. Subsequent checks are skipped for the current deployment.

### Proxy implementation not verified
- **Level**: ⚠️ Warning 
- **Message**: `contract <address> on chain <chain_id> is a proxy, and its implementation <address> is not verified on Sourcify, descriptor ABIs will not be validated`
- **Description**: Sourcify resolved the contract as a proxy, but one of its implementations is not verified, so the reference ABI would be incomplete. Subsequent checks are skipped for the current deployment.

### Chain not supported
- **Level**: ℹ️ Info 
- **Message**: `chain <chain_id> is not supported by Sourcify, descriptor ABIs will not be validated`
- **Description**: Sourcify does not support the chain of the deployment, so no reference ABI can be fetched. Subsequent checks are skipped for the current deployment.

### Could not fetch ABI
- **Level**: ⚠️ Warning 
- **Message**: `Fetching reference ABI for chain id <chain_id> failed, descriptor ABIs will not be validated: <error>`
- **Description**: ABI fetch from Sourcify has failed for another reason, such as a rate limit, a network error or a proxy resolution error. Subsequent checks are skipped for the current deployment.

### Deployment ABIs differ
- **Level**: ⚠️ Warning 
- **Message**: `The reference ABIs of the deployments do not all expose the same functions, display fields are validated against each distinct reference ABI: <chain id>:<address>, ...; <chain id>:<address>, ...`
- **Description**: The deployments of the descriptor do not have the same reference ABI. Display fields are validated once per distinct ABI, so findings may apply to some chains only (the contract URL in each finding tells which).

### Extra function
- **Level**: ⚠️ Warning 
- **Message**: `Function <function> (selector: <selector>) defined in descriptor ABIs does not exist in reference ABI (see <url>)`
- **Description**: A function found in the externally fetched ABI is not present in the ABI embedded in the v1 descriptor.

### Function mismatch
- **Level**: ⚠️ Warning 
- **Message**: `Function <function> (selector: <selector>) defined in descriptor ABIs does not match reference ABI (see <url>)`
- **Description**: A function found in the ABI embedded in the v1 descriptor does not match the one present in the externally fetched ABI.

## Deprecated fields checks
Both checks only apply to v2 descriptors. The ERC-7730 specification deprecates these fields, so the v2 linter rejects them.

### Deprecated ABI field
- **Level**: 🛑 Error 
- **Message**: ``The `context.contract.abi` field is deprecated and must not be set in v2 descriptors. Remove it: function signatures are declared by the `display.formats` keys, and ABIs are resolved from the verified contract.``
- **Description**: The descriptor sets the deprecated `context.contract.abi` field. Remove it.

### Deprecated schemas field
- **Level**: 🛑 Error 
- **Message**: ``The `context.eip712.schemas` field is deprecated and must not be set in v2 descriptors. Remove it: message types are declared by the `display.formats` keys, which must be EIP-712 `encodeType` strings.``
- **Description**: The descriptor sets the deprecated `context.eip712.schemas` field. Remove it.

## Display fields checks

### Invalid EIP712 Schema
- **Level**: 🛑 Error 
- **Message**: `Primary type <type> is not present in schema types. Please make sure the EIP-712 schema includes a definition for the primary type.`
- **Description**: Computed primary type is not present in EIP-712 format. Sanity check that prevents subsequent checks to be run.

### Missing Display Format
- **Level**: 🛑 Error 
- **Message**: `Schema primary type <type> must have a display format defined.`
- **Description**: Primary type has no display format. Sanity check that prevents subsequent checks to be run.

### Invalid Display Field
- **Level**: 🛑 Error 
- **Message**: `A display field is defined for <path>, but it does not exist in <type/selector>. Please check the field path is valid according to the EIP-712 schema/ABI.`
- **Description**: Extra display format for unknown field

### Invalid Display Format
- **Level**: 🛑 Error 
- **Message**: `Type <type> is not in EIP712 schemas. Please check the type is valid according to the EIP-712 schema.`
- **Description**: Extra display format for unknown primary type

### Invalid Selector
- **Level**: 🛑 Error 
- **Message**: `Selector <selector> not found in ABI.`
- **Description**: Extra display format for unknown selector

### Optional Display field missing
- **Level**: ℹ️ Informational
 - **Message**: ``No display field is defined for path <path> in <type/selector>. If intentionally excluded, please add it to `excluded` list to avoid this warning.``
- **Description**: No display format defined for optional field.

### Missing display field
- **Level**: ⚠️ Warning 
 - **Message**: ``No display field is defined for path <path> in <type/selector>. If intentionally excluded, please add it to `excluded` list to avoid this warning.``
- **Description**: No display format for non-optional field.

## Max length checks

### Object too long
- **Level**: ⚠️ Warning 
 - **Message**: ``<object> `<value>` exceeds <size> characters and may be truncated on Ledger devices.``
- **Description**: Owner/Legal name/URL/Contract id/Display intent/Display id/Display label is too long.

## Type classifier checks
Linter tries to guess the type of the contract, and provides warning about missing fields that are usually present for the guessed type of contracts. For now only Permits contracts are identified using a simple heuristic

### Expected Display field missing
- **Level**: ⚠️ Warning 
 - **Message**: `Contract detected as Permit but no spender/amount/expiration field displayed`
