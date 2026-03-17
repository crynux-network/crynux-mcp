from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from crynux_mcp.relay.models import RelayDepositListResult, RelayWithdrawCreateResult, RelayWithdrawListResult


class RelayApiClient:
    def __init__(self, *, base_url: str, timeout_seconds: int) -> None:
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("INVALID_RELAY_CONFIG: base_url is required.")
        self._base_url = normalized
        self._timeout_seconds = int(timeout_seconds)

    def connect_wallet(self, *, address: str, signature: str, timestamp: int) -> dict[str, Any]:
        return self._request_json(
            method="POST",
            path="/v1/client/connect_wallet",
            body={"address": address, "signature": signature, "timestamp": timestamp},
        )

    def get_account_balance(self, *, address: str, token: str) -> str:
        payload = self._request_json(
            method="GET",
            path=f"/v1/balance/{address}",
            token=token,
        )
        return str(payload)

    def create_withdraw(
        self,
        *,
        address: str,
        amount: str,
        benefit_address: str,
        network: str,
        timestamp: int,
        signature: str,
        token: str,
    ) -> RelayWithdrawCreateResult:
        payload = self._request_json(
            method="POST",
            path=f"/v1/relay_account/{address}/withdraw",
            token=token,
            body={
                "amount": amount,
                "benefit_address": benefit_address,
                "network": network,
                "timestamp": timestamp,
                "signature": signature,
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("RELAY_INVALID_RESPONSE: relay withdraw create response must be an object.")
        return RelayWithdrawCreateResult.create(
            amount_wei=amount,
            benefit_address=benefit_address,
            timestamp=timestamp,
            result=payload,
        )

    def list_withdraws(self, *, address: str, page: int, page_size: int, token: str) -> RelayWithdrawListResult:
        payload = self._request_json(
            method="GET",
            path=f"/v1/relay_account/{address}/withdraw/list",
            token=token,
            params={"page": page, "page_size": page_size},
        )
        if not isinstance(payload, dict):
            raise ValueError("RELAY_INVALID_RESPONSE: relay withdraw list response must be an object.")
        records = payload.get("withdraw_records", [])
        if not isinstance(records, list):
            records = []
        return RelayWithdrawListResult.create(
            page=page,
            page_size=page_size,
            total=int(payload.get("total", 0) or 0),
            withdraw_records=[item for item in records if isinstance(item, dict)],
        )

    def list_deposits(self, *, address: str, page: int, page_size: int, token: str) -> RelayDepositListResult:
        payload = self._request_json(
            method="GET",
            path=f"/v1/relay_account/{address}/deposit/list",
            token=token,
            params={"page": page, "page_size": page_size},
        )
        if not isinstance(payload, dict):
            raise ValueError("RELAY_INVALID_RESPONSE: relay deposit list response must be an object.")
        records = payload.get("deposit_records", [])
        if not isinstance(records, list):
            records = []
        return RelayDepositListResult.create(
            page=page,
            page_size=page_size,
            total=int(payload.get("total", 0) or 0),
            deposit_records=[item for item in records if isinstance(item, dict)],
        )

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any] | list[Any] | str | int | float:
        url = f"{self._base_url}{path}"
        if params:
            query = parse.urlencode({k: str(v) for k, v in params.items()})
            url = f"{url}?{query}"

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None if body is None else json.dumps(body, ensure_ascii=True).encode("utf-8")

        req = request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw) if raw else {}
                if not isinstance(payload, dict):
                    raise ValueError("RELAY_INVALID_RESPONSE: relay response body must be an object.")
                return payload.get("data", {})
        except error.HTTPError as exc:
            details = self._extract_http_error_detail(exc)
            if exc.code == 401:
                raise ValueError("RELAY_UNAUTHORIZED: relay token is invalid or expired.") from exc
            if exc.code == 400:
                raise ValueError(f"RELAY_BAD_REQUEST: {details}") from exc
            if exc.code == 403:
                raise ValueError(f"RELAY_FORBIDDEN: {details}") from exc
            if exc.code == 404:
                raise ValueError(f"RELAY_NOT_FOUND: {details}") from exc
            if exc.code >= 500:
                raise ValueError("RELAY_SERVER_ERROR: relay service is temporarily unavailable.") from exc
            raise ValueError(f"RELAY_HTTP_ERROR: {details}") from exc
        except error.URLError as exc:
            raise ValueError("RELAY_UNAVAILABLE: cannot reach relay endpoint.") from exc

    def _extract_http_error_detail(self, exc: error.HTTPError) -> str:
        try:
            raw = exc.read().decode("utf-8")
        except Exception:  # noqa: BLE001
            return f"status={exc.code}"
        if not raw:
            return f"status={exc.code}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, list) and detail:
                first = detail[0]
                if isinstance(first, dict):
                    return str(first.get("msg", raw))
                return str(first)
            if detail is not None:
                return str(detail)
        return raw


def select_latest_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None

    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        created_at = int(item.get("created_at", 0) or 0)
        identifier = int(item.get("id", 0) or 0)
        return (created_at, identifier)

    return max(records, key=sort_key)
