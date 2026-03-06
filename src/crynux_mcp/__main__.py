from __future__ import annotations

import argparse

from crynux_mcp.security.key_store import (
    create_key,
    delete_key,
    list_keys,
    prompt_and_add_key,
    set_default_key,
)
from crynux_mcp.server import run


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crynux-mcp")
    subparsers = parser.add_subparsers(dest="command")

    key_parser = subparsers.add_parser("key", help="Manage signer private key in system keychain.")
    key_subparsers = key_parser.add_subparsers(dest="key_command", required=True)
    add_parser = key_subparsers.add_parser("add", help="Import a private key with a name.")
    add_parser.add_argument("--name", required=True, help="Key name to store.")

    create_parser = key_subparsers.add_parser("create", help="Generate and store a new private key.")
    create_parser.add_argument("--name", required=True, help="Key name to create.")

    key_subparsers.add_parser("list", help="List all stored key names.")

    default_parser = key_subparsers.add_parser("set-default", help="Set the default key by name.")
    default_parser.add_argument("--name", required=True, help="Key name to set as default.")

    delete_parser = key_subparsers.add_parser("delete", help="Delete a stored key by name.")
    delete_parser.add_argument("--name", required=True, help="Key name to delete.")

    return parser


def _run_key_command(args: argparse.Namespace) -> int:
    if args.key_command == "add":
        record = prompt_and_add_key(args.name)
        print(f"Signer key '{record['name']}' imported. Address: {record['address']}")
        return 0

    if args.key_command == "create":
        record = create_key(args.name)
        print(f"Signer key '{record['name']}' created. Address: {record['address']}")
        return 0

    if args.key_command == "list":
        records = list_keys()
        if not records:
            print("No signer keys found.")
            return 1
        for record in records:
            default_suffix = " (default)" if record["is_default"] else ""
            print(f"{record['name']}{default_suffix}: {record['address']}")
        return 0

    if args.key_command == "delete":
        delete_key(args.name)
        print(f"Signer key '{args.name}' deleted.")
        return 0

    if args.key_command == "set-default":
        record = set_default_key(args.name)
        print(f"Signer key '{record['name']}' is now default. Address: {record['address']}")
        return 0

    raise ValueError(f"Unsupported key command: {args.key_command}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "key":
        try:
            raise SystemExit(_run_key_command(args))
        except ValueError as exc:
            print(str(exc))
            raise SystemExit(1) from exc
    run()


if __name__ == "__main__":
    main()
