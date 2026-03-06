# Tool Reference

This document contains detailed input and output fields for each MCP tool.

## Action Index

### Wallet

| Action | Description |
|---|---|
| [`create_key`](#create_key) | Create a new local signer key in system keychain. |
| [`list_keys`](#list_keys) | List all local signer keys and default status. |
| [`delete_key`](#delete_key) | Delete a local signer key by name. |
| [`set_default_key`](#set_default_key) | Set a local signer key as default. |
| [`export_key`](#export_key) | Export a local signer key to a file path. |

### Blockchain

| Action | Description |
|---|---|
| [`get_balance`](#get_balance) | Query native CNX balance for an address. |
| [`transfer_native`](#transfer_native) | Send native CNX with local signer key. |
| [`get_beneficial_address`](#get_beneficial_address) | Query node beneficial address. |
| [`set_beneficial_address`](#set_beneficial_address) | Submit transaction to set beneficial address. |
| [`get_node_staking_info`](#get_node_staking_info) | Query node staking information. |
| [`get_node_credits`](#get_node_credits) | Query node credits balance. |

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

### Blockchain

## get_balance

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `unit`: optional, `wei` or `ether` (default: `ether`).

Output fields:
- `network`
- `address`
- `balance_wei`
- `balance_formatted`
- `symbol` (`CNX`)
- `chain_id`

## transfer_native

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `to`: recipient EVM address.
- `amount`: numeric string.
- `unit`: optional, `wei` or `ether` (default: `ether`).
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Output fields:
- `network`
- `from_address`
- `to`
- `value_wei`
- `tx_hash`
- `chain_id`

## get_beneficial_address

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `node_address`: operational EVM address to query.

Output fields:
- `network`
- `node_address`
- `beneficial_address`
- `is_set`: `true` when beneficial address is not zero address.
- `contract_address`
- `chain_id`

## set_beneficial_address

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `beneficial_address`: target beneficial EVM address.
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Output fields:
- `network`
- `node_address`: signer address that submits the transaction.
- `beneficial_address`
- `tx_hash`
- `contract_address`
- `chain_id`

## get_node_staking_info

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `node_address`: node wallet EVM address.

Output fields:
- `network`
- `node_address`
- `staked_balance_wei`
- `staked_balance_formatted`
- `staked_credits`
- `status`: staking status enum value (`0` = unstaked, `1` = staked, `2` = pending unstake).
- `unstake_timestamp`: unix timestamp in seconds as a string (`0` when unset).
- `contract_address`
- `chain_id`

## get_node_credits

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `node_address`: node wallet EVM address to query credits for.

Output fields:
- `network`
- `node_address`
- `credits`
- `credits_formatted`
- `contract_address`
- `chain_id`

### Relay

## relay_get_account_balance

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `key_name`: optional signer key name. Uses default local key if omitted.

Output fields:
- `network`
- `address`
- `balance_wei`
- `token_expires_at`

## relay_withdraw_create

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `amount_wei`: amount in wei as a numeric string.
- `benefit_address`: optional destination EVM address. Uses `address` if omitted.
- `key_name`: optional signer key name. Uses default local key if omitted.

Output fields:
- `network`
- `address`
- `amount_wei`
- `benefit_address`
- `timestamp`
- `result`: raw Relay response payload for withdraw creation.

## relay_withdraw_list

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `page`: optional page number (default `1`).
- `page_size`: optional page size (default `10`).
- `key_name`: optional signer key name. Uses default local key if omitted.

Output fields:
- `network`
- `address`
- `page`
- `page_size`
- `total`
- `withdraw_records`

## relay_withdraw_latest_status

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `scan_page_size`: optional scan size from latest list page (default `20`).
- `key_name`: optional signer key name. Uses default local key if omitted.

Output fields:
- `network`
- `address`
- `kind`: `withdraw`
- `status`: status value from latest record (string).
- `found`: whether any withdraw record exists.
- `latest_record`

## relay_deposit_initiate

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `amount`: numeric string.
- `key_name`: optional signer key name. Uses default local key if omitted.
- `unit`: optional, `wei` or `ether` (default: `ether`).
- `gas_price_wei`: optional override.
- `gas_limit`: optional override.

Output fields:
- `network`
- `from_address`
- `to`: Relay deposit address used for transfer.
- `value_wei`
- `tx_hash`
- `chain_id`
- `deposit_address`

## relay_deposit_list

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `page`: optional page number (default `1`).
- `page_size`: optional page size (default `10`).
- `key_name`: optional signer key name. Uses default local key if omitted.

Output fields:
- `network`
- `address`
- `page`
- `page_size`
- `total`
- `deposit_records`

## relay_deposit_latest_status

Inputs:
- `network`: optional (`dymension` or `near`). Defaults to configured default network.
- `address`: EVM address.
- `scan_page_size`: optional scan size from latest list page (default `20`).
- `key_name`: optional signer key name. Uses default local key if omitted.

Output fields:
- `network`
- `address`
- `kind`: `deposit`
- `status`: status value from latest record (string).
- `found`: whether any deposit record exists.
- `latest_record`

### Wallet

## create_key

Inputs:
- `name`: signer key name.

Output fields:
- `name`
- `address`

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
