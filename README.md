Crynux MCP Server

MCP server for Crynux Network operations.

## Scope

- Native CNX balance query on Crynux EVM networks
- Native CNX transfer signed by a private key from local system keychain
- Beneficial address query and on-chain update
- Node staking query
- Node credits query
- Relay API integration is not implemented yet

## Spec and transport

- MCP protocol target: `2025-11-25`
- Runtime transport: `stdio` (local process, no HTTP server required)

## Tools

### `get_balance`

Query the native CNX balance for an EVM address on a configured Crynux network.

### `transfer_native`

Send native CNX from the local signer wallet to a recipient EVM address.

### `get_beneficial_address`

Query the configured beneficial address for an operational EVM address.

### `set_beneficial_address`

Submit an on-chain transaction to set a beneficial address.

### `get_node_staking_info`

Query node staking details.

### `get_node_credits`

Query node credits.

### `create_key`

Create a new signer key in local system keychain with a provided name.

### `list_keys`

List all local signer keys (name, address, and default flag).

### `delete_key`

Delete a local signer key by name.

### `set_default_key`

Set a local signer key as the default key.

### `export_key`

Export a named local signer key to a specified file path.

For detailed tool inputs/outputs, see [`docs/tools.md`](./docs/tools.md).

## Security notes

- The server never intentionally logs raw private keys.
- `transfer_native` reads signer key from your local system keychain.
- Optional fallback: if no keychain entry exists, it reads `CRYNUX_PRIVATE_KEY` from MCP server environment.
- The model only sees transfer fields (`network`, `to`, `amount`, and optional gas fields), not raw key material.
- Use dedicated low-risk wallets for AI operations, not treasury wallets.

## Get Started

### Step 1) Prerequisites

- Install Python 3.11 or newer.
- Open a terminal.

### Step 2) Install the package

Install from PyPI (recommended):

```bash
python -m pip install crynux-mcp
```

If you are developing this repository, install from source in editable mode:

```bash
python -m pip install -e ".[dev]"
```

### Step 3) Choose your AI client and add MCP config

You only need one client config (Cursor, VS Code, or Claude Desktop).

#### Cursor

Create or edit `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "crynux-mcp": {
      "command": "python",
      "args": ["-m", "crynux_mcp"]
    }
  }
}
```

#### VS Code

Create or edit `.vscode/mcp.json` in your project (or your user `mcp.json`):

```json
{
  "servers": {
    "crynuxMcp": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "crynux_mcp"]
    }
  }
}
```

#### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crynux-mcp": {
      "command": "python",
      "args": ["-m", "crynux_mcp"]
    }
  }
}
```

### Step 4) Manage signer keys (cross-platform)

Run these commands in your terminal:

```bash
crynux-mcp key add --name main
crynux-mcp key create --name trading-bot
crynux-mcp key list
crynux-mcp key set-default --name main
crynux-mcp key delete --name trading-bot
```

`key add` prompts for your private key with hidden input and stores it in your OS keychain.
`key create` generates a new private key and stores it directly in your OS keychain.

- Windows: Credential Manager
- macOS: Keychain
- Linux: Secret Service compatible keyring

Optional advanced fallback (if you do not want keychain): set `CRYNUX_PRIVATE_KEY` in MCP server env.

### Step 5) Restart your AI client

After saving MCP config, fully restart the client so it reloads servers.

### Step 6) Verify the server is loaded

In your AI client, check MCP tool list and confirm these tools appear:

- `get_balance`
- `transfer_native`
- `get_beneficial_address`
- `set_beneficial_address`
- `get_node_staking_info`
- `get_node_credits`

### Step 7) First tool calls

Example: query balance

- `network`: `dymension`
- `address`: your EVM address
- `unit`: `ether`

Example: send native CNX

- `network`: `dymension`
- `key_name`: `main` (optional, uses default local key if omitted)
- `to`: recipient EVM address
- `amount`: for example `0.1`
- `unit`: `ether`

Example: query beneficial address

- `network`: `dymension`
- `node_address`: your operational EVM address

Example: set beneficial address

- `network`: `dymension`
- `key_name`: `main` (optional, uses default local key if omitted)
- `beneficial_address`: your payout EVM address

Example: query node staking info

- `network`: `dymension`
- `node_address`: your node wallet EVM address

Example: query node credits

- `network`: `dymension`
- `node_address`: your node wallet EVM address

Signer key source for transfer:

- Named key in system keychain set by `crynux-mcp key add` or `crynux-mcp key create` (preferred)
- `CRYNUX_PRIVATE_KEY` env var fallback

### Step 8) Optional local manual run

You can start the MCP server process directly for debugging:

```bash
python -m crynux_mcp
```

## Release

Maintainer release instructions are in [`RELEASE.md`](./RELEASE.md).

## Network configuration

Chain metadata is stored in:

- `src/crynux_mcp/config/chains.json`

Update this file to change RPC URLs, chain IDs, or contract addresses.

## Tests

```bash
pytest
```
