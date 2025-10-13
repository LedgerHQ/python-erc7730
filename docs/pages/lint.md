# Linter checks list
## ABI checks
### Could not fetch ABI
- **Level**: ⚠️ Warning 
- **Message**: `Fetching reference ABI for chain id <chain_id> failed, descriptor ABIs will not be validated: <error>`
- **Description**: ABI fetch from external source (Etherscan or equivalent) has failed. Subsequents checks are skipped for the current deployment.

### Proxy Contract
- **Level**: ⚠️ Warning 
- **Message**: `Contract <url> is likely to be a proxy, validation of descriptor ABIs skipped`
- **Description**: Contract detected as a potential proxy contract based on a simple heuristic. Subsequents checks are skipped.

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
