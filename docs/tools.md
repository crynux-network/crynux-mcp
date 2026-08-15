# Tool Reference

This document contains detailed input and output fields for each MCP tool.

## Action Index

### Wallet

| Action | Description |
|---|---|
| [`create_key`](#create_key) | Create a new local signer key in system keychain. |
| [`sign_message`](#sign_message) | Sign an arbitrary message with a local keychain key. |
| [`list_keys`](#list_keys) | List all local signer keys and default status. |
| [`delete_key`](#delete_key) | Delete a local signer key by name. |
| [`set_default_key`](#set_default_key) | Set a local signer key as default. |
| [`export_key`](#export_key) | Export a local signer key to a file path. |

### Blockchain

| Action | Description |
|---|---|
| [`get_balance`](#get_balance) | Query native CNX balance for an address. |
| [`get_latest_block_number`](#get_latest_block_number) | Query latest on-chain block height for a network. |
| [`transfer_native`](#transfer_native) | Send native CNX with local signer key. |
| [`sign_transaction`](#sign_transaction) | Sign an arbitrary EVM transaction with a local key. |
| [`send_raw_transaction`](#send_raw_transaction) | Broadcast a signed raw transaction. |
| [`get_beneficial_address`](#get_beneficial_address) | Query node beneficial address. |
| [`set_beneficial_address`](#set_beneficial_address) | Submit transaction to set beneficial address. |
| [`get_node_staking_info`](#get_node_staking_info) | Query node staking information. |
| [`stake_node`](#stake_node) | Stake or update node stake on the NodeStaking contract only. This does not join Relay, does not start a Crynux node process, and Relay will not dispatch tasks. |
| [`try_unstake_node`](#try_unstake_node) | Start node unstake (`tryUnstake`). |
| [`force_unstake_node`](#force_unstake_node) | Complete node unstake after delay (`forceUnstake`). |
| [`get_delegated_staking_infos`](#get_delegated_staking_infos) | List delegated staking positions for an address. |
| [`delegated_stake`](#delegated_stake) | Create or update delegated stake to a target total amount. |
| [`delegated_unstake`](#delegated_unstake) | Cancel delegated stake on a node. |

### Relay

| Action | Description |
|---|---|
| [`relay_get_account_balance`](#relay_get_account_balance) | Query Relay account balance. |
| [`relay_withdraw_create`](#relay_withdraw_create) | Create Relay withdraw request. |
| [`relay_withdraw_list`](#relay_withdraw_list) | List Relay withdraw records. |
| [`relay_withdraw_latest_status`](#relay_withdraw_latest_status) | Query latest Relay withdraw status. |
| [`relay_deposit_initiate`](#relay_deposit_initiate) | Initiate Relay deposit with on-chain transfer. |
| [`relay_deposit_list`](#relay_deposit_list) | List Relay deposit records. |
| [`relay_deposit_latest_status`](#relay_deposit_latest_status) | Query latest Relay deposit status. |

## Detailed Parameters

Address resolution rule for actions that accept both `address` and `key_name`:
- Provide either `address` or `key_name`.
- If both are provided, `key_name` is used to resolve the effective address.

Supported blockchain networks:
- `crynux-on-base` (`network_kind`: `mainnet`)
- `crynux-on-base-sepolia` (`network_kind`: `testnet`)

Default network: `crynux-on-base`.

Relay environment rule for all Relay actions:
- `relay_env`: optional, `staging` or `production` (default: `production`).
- `relay_base_url`: optional Relay API base URL override for this call.
- Use the Relay root URL only, for example `http://127.0.0.1:8080`.
- Do not include `/v1` or `/v2` in `relay_base_url`.
- When `relay_base_url` is set, it overrides only the HTTP base URL. Deposit address and env/network pairing still follow `relay_env`.

Relay env and network pairing rule for actions that take both `network` and `relay_env`:
- `relay_env=staging` MUST be used only with chains whose `network_kind` is `testnet`.
- `relay_env=production` MUST be used only with chains whose `network_kind` is `mainnet`.
- Current concrete pairs: `staging` with `crynux-on-base-sepolia`, `production` with `crynux-on-base`.
- Mismatch fails immediately with `INVALID_RELAY_NETWORK_PAIRING` before any Relay HTTP call or on-chain transfer.

Deposit address rule:
- Deposit address is selected from the configured Relay environment (`relay_env`), not from the blockchain network key.
- On-chain transfer in `relay_deposit_initiate` still uses the selected `network`.

### Blockchain

## get_balance

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional EVM address.
- `key_name`: optional signer key name. Uses key address when provided.

Output fields:
- `balance_wei`
- `symbol` (`CNX`)

## get_latest_block_number

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.

Output fields:
- `block_number`: latest finalized block number returned by RPC.

## transfer_native

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `to`: recipient EVM address.
- `amount`: numeric string.
- `unit`: optional, `wei` or `ether` (default: `ether`).
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Output fields:
- `from_address`
- `to`
- `value_wei`
- `tx_hash`

## sign_transaction

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `to`: optional recipient EVM address. Omit only for contract-creation transactions that include `data`.
- `value`: optional native value as a numeric string (default `0`).
- `unit`: optional, `wei` or `ether` (default: `wei`).
- `data`: optional calldata hex string (default `0x`).
- `nonce`: optional. Defaults to the signer pending nonce from RPC.
- `gas_price_wei`: optional override. Defaults to current network gas price.
- `gas_limit`: optional override. Defaults to RPC `estimateGas`.

Behavior:
- Builds a legacy EVM transaction for the selected network `chain_id`.
- Signs the transaction with the local keychain private key.
- Does not broadcast the transaction.
- Returns `raw_transaction` for later broadcast with `send_raw_transaction`.
- The private key is never included in the tool response.

Output fields:
- `from_address`
- `to`: empty string for contract-creation transactions
- `value_wei`
- `data`
- `nonce`
- `gas`
- `gas_price_wei`
- `chain_id`
- `raw_transaction`: signed raw transaction hex with `0x` prefix
- `tx_hash`: transaction hash of the signed transaction

## send_raw_transaction

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `raw_transaction`: signed raw transaction hex with `0x` prefix.

Output fields:
- `tx_hash`

## get_beneficial_address

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional operational EVM address to query.
- `key_name`: optional signer key name. Uses key address when provided.

Output fields:
- `address`
- `beneficial_address`
- `is_set`: `true` when beneficial address is not zero address.

## set_beneficial_address

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `beneficial_address`: target beneficial EVM address.
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Output fields:
- `address`: signer address that submits the transaction.
- `beneficial_address`
- `tx_hash`

## get_node_staking_info

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional node wallet EVM address.
- `key_name`: optional signer key name. Uses key address when provided.

Output fields:
- `address`
- `staked_balance_wei`
- `staked_balance_formatted`
- `status`: staking status enum value (`0` = unstaked, `1` = staked, `2` = pending unstake).
- `unstake_timestamp`: unix timestamp in seconds as a string (`0` when unset). This is set when `tryUnstake` succeeds.
- `force_unstake_delay_seconds`: configured wait period after `tryUnstake` before `forceUnstake` is allowed.
- `force_unstake_available_at`: unix timestamp when `forceUnstake` becomes available (`0` when status is not pending unstake).
- `force_unstake_available_in_seconds`: remaining seconds until `forceUnstake` is available (`0` when already available or status is not pending unstake).
- `can_force_unstake`: `true` when status is pending unstake and the wait period has passed.

## stake_node

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `amount`: target total node stake amount as a numeric string. This is the final stake amount after the transaction, not the incremental delta.
- `unit`: optional, `wei` or `ether` (default: `ether`).
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Behavior:
- Calls `stake` on the NodeStaking contract for the signer wallet.
- This only updates on-chain node stake. It does not join Relay, does not start a Crynux node process, and Relay will not dispatch tasks because of this call.
- Requires current status `Unstaked` (`0`) or `Staked` (`1`).
- If no stake exists, this creates a new node stake.
- If a stake already exists, this updates the stake to the new total amount.
- When increasing stake, the transaction value is `new_total - previous_total`.
- When decreasing stake, the transaction value is `0` and the contract refunds the difference.
- Target amount MUST be greater than or equal to the contract minimum stake amount.

Output fields:
- `address`: signer address that submits the transaction. This is the node wallet being staked.
- `previous_amount_wei`
- `stake_amount_wei`: target total amount after the transaction.
- `value_sent_wei`: native CNX value attached to the transaction.
- `tx_hash`

## try_unstake_node

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Behavior:
- Calls `tryUnstake` for the signer wallet.
- Requires current status `Staked` (`1`).
- Moves status to `PendingUnstaked` (`2`) and records `unstake_timestamp`.

Output fields:
- `address`
- `tx_hash`

## force_unstake_node

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Behavior:
- Calls `forceUnstake` for the signer wallet.
- Requires current status `PendingUnstaked` (`2`).
- Requires the wait period after `tryUnstake` to have passed.
- Withdraws the full node stake to the beneficial address if set, otherwise to the node wallet.

Output fields:
- `address`
- `unstaked_amount_wei`
- `tx_hash`

## get_delegated_staking_infos

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional delegator wallet EVM address.
- `key_name`: optional signer key name. Uses key address when provided.

Output fields:
- `address`: delegator wallet address.
- `total_stake_wei`
- `total_stake_formatted`
- `stakes`: array of delegated staking positions.

Each stake entry contains:
- `node_address`
- `stake_amount_wei`
- `stake_amount_formatted`

## delegated_stake

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `node_address`: node wallet EVM address to stake to.
- `amount`: target total stake amount as a numeric string. This is the final stake amount after the transaction, not the incremental delta.
- `unit`: optional, `wei` or `ether` (default: `ether`).
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Behavior:
- If no existing stake exists for the signer and `node_address`, this creates a new delegated stake.
- If a stake already exists, this updates the stake to the new total amount.
- When increasing stake, the transaction value is `new_total - previous_total`.
- When decreasing stake, the transaction value is `0` and the contract refunds the difference.
- To cancel a stake completely, use `delegated_unstake`.

Output fields:
- `address`: signer address that submits the transaction.
- `node_address`
- `previous_amount_wei`
- `stake_amount_wei`: target total amount after the transaction.
- `value_sent_wei`: native CNX value attached to the transaction.
- `tx_hash`

## delegated_unstake

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `node_address`: node wallet EVM address to unstake from.
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Behavior:
- Cancels the signer wallet's delegated stake on `node_address`.
- Withdraws the full staked amount back to the signer wallet.

Output fields:
- `address`: signer address that submits the transaction.
- `node_address`
- `unstaked_amount_wei`
- `tx_hash`

### Relay

## relay_get_account_balance

Inputs:
- `address`: optional EVM address.
- `key_name`: optional signer key name. Uses key address when provided.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional Relay API base URL override for this call.

Output fields:
- `balance_wei`

## relay_withdraw_create

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional node wallet EVM address.
- `amount_wei`: amount in wei as a numeric string.
- `key_name`: optional signer key name. Uses key address when provided.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional Relay API base URL override for this call.

Behavior:
- The tool enforces the Relay env and network pairing rule before calling Relay.
- The tool queries the on-chain beneficial address for the resolved node wallet before creating the Relay withdraw.
- If the on-chain beneficial address is unset (`0x0000000000000000000000000000000000000000`), the tool uses the resolved node wallet address as `benefit_address`.
- If the on-chain beneficial address is set, the tool uses that address as `benefit_address`.

Output fields:
- `amount_wei`
- `benefit_address`: final destination address sent to Relay after on-chain lookup.
- `timestamp`
- `result`: raw Relay response payload for withdraw creation.

## relay_withdraw_list

Inputs:
- `address`: optional EVM address.
- `page`: optional page number (default `1`).
- `page_size`: optional page size (default `10`).
- `key_name`: optional signer key name. Uses key address when provided.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional Relay API base URL override for this call.

Output fields:
- `page`
- `page_size`
- `total`
- `withdraw_records`
- Each record includes its own `network` field.

## relay_withdraw_latest_status

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional EVM address.
- `scan_page_size`: optional scan size from latest list page (default `20`).
- `key_name`: optional signer key name. Uses key address when provided.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional Relay API base URL override for this call.

Behavior:
- The tool enforces the Relay env and network pairing rule before calling Relay.

Output fields:
- `kind`: `withdraw`
- `status`: status value from latest record (string). Status codes: `0` = `Processing`, `1` = `Success`, `2` = `Failed`.
- `found`: whether any withdraw record exists.
- `latest_record`

## relay_deposit_initiate

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `amount`: numeric string.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `unit`: optional, `wei` or `ether` (default: `ether`).
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional. Does not change deposit address selection.

Behavior:
- The tool enforces the Relay env and network pairing rule before transferring.
- Deposit address is taken from the selected `relay_env`.
- On-chain transfer is sent on the selected `network`.

Output fields:
- `from_address`
- `to`: Relay deposit address used for transfer.
- `value_wei`
- `tx_hash`

## relay_deposit_list

Inputs:
- `address`: optional EVM address.
- `page`: optional page number (default `1`).
- `page_size`: optional page size (default `10`).
- `key_name`: optional signer key name. Uses key address when provided.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional Relay API base URL override for this call.

Output fields:
- `page`
- `page_size`
- `total`
- `deposit_records`
- Each record includes its own `network` field.

## relay_deposit_latest_status

Inputs:
- `network`: optional (`crynux-on-base` or `crynux-on-base-sepolia`). Defaults to configured default network.
- `address`: optional EVM address.
- `scan_page_size`: optional scan size from latest list page (default `20`).
- `key_name`: optional signer key name. Uses key address when provided.
- `relay_env`: optional (`staging` or `production`). Defaults to configured default Relay env.
- `relay_base_url`: optional Relay API base URL override for this call.

Behavior:
- The tool enforces the Relay env and network pairing rule before calling Relay.

Output fields:
- `kind`: `deposit`
- `status`: status value from latest record (string). Status codes: `0` = `Processing`, `1` = `Success`, `2` = `Failed`.
- `found`: whether any deposit record exists.
- `latest_record`

### Wallet

## create_key

Inputs:
- `name`: signer key name.

Output fields:
- `name`
- `address`

## sign_message

Inputs:
- `message`: message to sign.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `message_encoding`: optional encoding mode:
  - `utf8` (default): EIP-191 personal_sign over UTF-8 text
  - `hex`: EIP-191 personal_sign over raw bytes provided as hex
  - `hash`: sign a 32-byte digest directly without EIP-191 prefix

Behavior:
- Loads the private key from the local system keychain inside the MCP process.
- Returns only the signer address and signature.
- The private key is never included in the tool response.

Output fields:
- `address`: signer address derived from the local key
- `message`: the exact message string that was signed
- `message_encoding`: encoding mode used for signing
- `signature`: hex signature with `0x` prefix

## list_keys

Inputs:
- No input fields.

Output fields:
- `keys`: array of key records.
- `count`: number of keys.

Each key record contains:
- `name`
- `address`
- `is_default`

## delete_key

Inputs:
- `name`: signer key name to delete.

Output fields:
- `name`
- `deleted`

## set_default_key

Inputs:
- `name`: signer key name to set as default.

Output fields:
- `name`
- `address`
- `is_default`

## export_key

Inputs:
- `name`: signer key name to export.
- `filename`: destination file path.

Output fields:
- `name`
- `filename`
- `written`
