# Crynux MCP Server

[![](https://dcbadge.limes.pink/api/server/https://discord.gg/zmU9GRwU6f)](https://discord.gg/zmU9GRwU6f)
[![PyPI - Version](https://img.shields.io/pypi/v/crynux-mcp?style=for-the-badge)](https://pypi.org/project/crynux-mcp/)

MCP server for Crynux Network operations, designed for LLM clients (such as Cursor, VS Code, and Claude Desktop) to perform most Crynux Network/Crynux Portal actions through standardized MCP tools.

## Features

### Wallet

- Wallet management with system keychain (create keys, sign transactions, list/delete/export keys, set default key)

### Blockchain

- Native CNX balance query on Crynux L2 networks
- Latest block height query on Crynux L2 networks
- Native CNX transfer
- Beneficial address query and on-chain update
- Node staking query
- Node credits query

### Relay

- Relay account balance query
- Relay withdraw create/list/latest-status query
- Relay deposit initiate/list/latest-status query

## Tools

For the full action list and detailed input/output fields, see [`docs/tools.md`](./docs/tools.md).

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

In your AI client, check MCP tool list and confirm wallet, blockchain, and Relay actions are available.
Use [`docs/tools.md`](./docs/tools.md) as the source of truth for the full action catalog.

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

Example: query Relay account balance

- `network`: `dymension`
- `address`: your wallet EVM address
- `key_name`: `main` (optional)

Relay auth token is obtained and refreshed internally for authenticated Relay actions.

Example: create Relay withdraw request

- `network`: `dymension`
- `address`: your wallet EVM address
- `amount_wei`: for example `1000000000000000000` (1 CNX)
- `benefit_address`: optional destination address
- `key_name`: `main` (optional)

Example: initiate Relay deposit (on-chain transfer)

- `network`: `dymension`
- `amount`: for example `1`
- `unit`: `ether`
- `key_name`: `main` (optional)

Signer key source for transfer:

- Named key in system keychain set by `crynux-mcp key add` or `crynux-mcp key create` (preferred)
- `CRYNUX_PRIVATE_KEY` env var fallback

### Step 8) Optional local manual run

You can start the MCP server process directly for debugging:

```bash
python -m crynux_mcp
```

## Spec and transport

- MCP protocol target: `2025-11-25`
- Runtime transport: `stdio` (local process, no HTTP server required)

## Release

Maintainer release instructions are in [`RELEASE.md`](./RELEASE.md).

## Network configuration

Chain metadata is stored in:

- `src/crynux_mcp/config/chains.json`

Update this file to change RPC URLs, chain IDs, or contract addresses.

Relay API configuration is stored in:

- `src/crynux_mcp/config/relay.json`

Update this file to change Relay URL, timeout, and per-network deposit addresses.

## Tests

```bash
pytest
```
