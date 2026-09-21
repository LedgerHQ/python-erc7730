# Linter checks list
## ABI checks
The three "not verified" / "not supported" checks below are reported as errors instead when `--require-verified` is passed.

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

### Deployments differ
- **Level**: ⚠️ Warning 
- **Message**: `Deployments do not all expose the same functions, display fields are validated against each distinct reference ABI: <chain id>:<address>, ...; <chain id>:<address>, ...`
- **Description**: The deployments of the descriptor do not have the same reference ABI. Display fields are validated once per distinct ABI, so findings may apply to some chains only (the contract URL in each finding tells which).

### Extra function
- **Level**: ⚠️ Warning 
- **Message**: `Function <function> (selector: <selector>) defined in descriptor ABIs does not exist in reference ABI (see <url>)`
- **Description**: A function found in the externally fetched ABI is not present in the provided ABI.

### Function mismatch
- **Level**: ⚠️ Warning 
- **Message**: `Function <function> (selector: <selector>) defined in descriptor ABIs does not match reference ABI (see <url>)`
- **Description**: A function found in the provided ABI does not match the one present in the externally fetched ABI.

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
