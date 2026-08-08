# Verified-source ingestion

`holes fetch` retrieves public Solidity source from the Etherscan V2
`getsourcecode` endpoint and writes a reviewable, self-contained directory.

```bash
export ETHERSCAN_API_KEY="your key"
holes fetch 1 0x1234567890abcdef1234567890abcdef12345678 \
  --output verified/ethereum-example
holes verified/ethereum-example --compile
```

The positional values are a positive chain ID and an exact 20-byte hexadecimal
address. Use `--api-key-env NAME` to read the credential from another environment
variable and `--timeout SECONDS` to change the 30-second HTTP timeout. The API
key is used only in the request and is never written to output.

The output directory must not exist. The command writes every Solidity source
using the paths in the verified standard JSON input, preserves that input as
`compiler-input.json`, and adds `provenance.json` with:

- provider and API version, chain ID, normalized address, and retrieval time;
- contract/compiler, optimizer, EVM, license, proxy, and implementation metadata;
- byte size and SHA-256 digest for every source;
- the path and SHA-256 digest of the preserved compiler input when available;
- one digest over the ordered source set.

Single-file verifications use the explorer's contract filename, with a safe
contract-name fallback. Absolute paths, parent traversal, duplicate normalized
paths, non-Solidity compiler types, malformed payloads, unverified contracts,
and responses larger than 20 MiB are rejected. Existing output is never merged
or overwritten.

## Trust boundary

Provenance records what the explorer returned; Contract Holes does not yet
recompile the source and compare runtime bytecode with an independent RPC node.
For proxies, it records the explorer's `Proxy` and `Implementation` fields but
does not automatically fetch or scan the implementation. Fetch each intended
address explicitly and review the provenance before treating it as an audit
input.

The command makes a network request containing the address, chain ID, and API
key. The normal scanner remains local. Use source and credentials only where you
are authorized, and follow the explorer's API terms. The endpoint parameters are
documented in the official
[Etherscan get-contract-source-code reference](https://docs.etherscan.io/api-reference/endpoint/getsourcecode).
