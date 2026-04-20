"""Shared Accubid Anywhere API client."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from aiohttp import ClientError, ClientSession, ClientTimeout

from .auth import AccubidAuth
from .config import Config
from .errors import ApiError
from .log_config import get_logger
from .request_context import (
    get_actor_token,
    get_request_outbound_token,
    reset_request_outbound_token,
    set_request_outbound_token,
)
from .resilience import CircuitBreaker, RateLimiter

logger = get_logger()


def _unverified_jwt_payload_dict(token: str | None) -> dict[str, Any] | None:
    """Middle segment of a JWT decoded as JSON (no signature verification)."""
    if not token or not isinstance(token, str):
        return None
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    try:
        seg = parts[1].strip()
        pad = 4 - (len(seg) % 4)
        if pad != 4:
            seg += "=" * pad
        raw = base64.urlsafe_b64decode(seg)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return None


def _outbound_token_diagnostics() -> dict[str, Any]:
    """Fields from the bearer sent to Accubid (exchanged token), not the inbound actor JWT."""
    raw = get_request_outbound_token()
    if not raw:
        return {}
    payload = _unverified_jwt_payload_dict(raw)
    if payload is None:
        return {"outbound_token_shape": "opaque_or_malformed"}
    out: dict[str, Any] = {"outbound_token_shape": "jwt"}
    if payload.get("azp") is not None:
        out["outbound_azp"] = payload["azp"]
    aud = payload.get("aud")
    if aud is not None:
        out["outbound_aud"] = aud
    sc = payload.get("scope")
    if sc is not None:
        out["outbound_scope_claim"] = sc
    return out


def _build_accubid_api_error_details(
    *,
    method: str,
    endpoint_path: str,
    url: str,
    safe_body: str,
    full_text_len: int,
    status_code: int,
) -> dict[str, Any]:
    """Merge Trimble response with safe actor JWT fields for 900909 / subscription diagnostics."""
    truncated = full_text_len > len(safe_body)
    details: dict[str, Any] = {
        "method": method,
        "endpoint_path": endpoint_path,
        "request_url": url,
        "response_body": safe_body,
        "response_body_truncated": truncated,
        "status_code": status_code,
    }
    actor_raw = get_actor_token()
    actor_payload = _unverified_jwt_payload_dict(actor_raw) if actor_raw else None
    if actor_payload:
        if actor_payload.get("azp") is not None:
            details["actor_azp"] = actor_payload["azp"]
        if actor_payload.get("sub") is not None:
            details["actor_sub"] = actor_payload["sub"]
        if actor_payload.get("account_id") is not None:
            details["actor_account_id"] = actor_payload["account_id"]
        sc = actor_payload.get("scope")
        if sc is not None:
            details["actor_scopes"] = sc

    details.update(_outbound_token_diagnostics())

    if "900909" in safe_body:
        outbound_azp = details.get("outbound_azp")
        actor_azp = (actor_payload or {}).get("azp", "unknown")
        shape = details.get("outbound_token_shape")
        if outbound_azp:
            scope_hint = ""
            out_sc = str(details.get("outbound_scope_claim") or "")
            if (
                endpoint_path.startswith("/databases")
                and "anywhere-database" not in out_sc.replace(" ", "").lower()
            ):
                scope_hint = (
                    " Token-exchange scope for REST Database API usually must include **anywhere-database** "
                    "(copy your working Postman `scope=` query into ACCUBID_SCOPE). "
                )
            details["hint"] = (
                "Trimble 900909: Accubid rejected the outbound access token "
                f"(JWT azp={outbound_azp})."
                + scope_hint
                + " Confirm that OAuth app is subscribed to Accubid Anywhere **API products** you call "
                "(Database vs agentic-only scopes differ). "
                f"actor_azp={actor_azp} is the inbound Agent Studio token only."
            )
        elif shape == "opaque_or_malformed":
            details["hint"] = (
                "Trimble 900909: outbound bearer was not a decodable JWT. "
                "Confirm token exchange at id.trimble.com "
                "returns a JWT access_token. "
                f"actor_azp={actor_azp} is inbound Studio only."
            )
        else:
            details["hint"] = (
                f"Trimble 900909: subscription inactive for the token Accubid received. "
                f"actor_azp={actor_azp} is the inbound Actor Studio JWT (diagnostic only). "
                "If using token exchange, ensure CLIENT_ID is subscribed and OBO scope includes accubid_agentic_ai."
            )
    return details


class AccubidClient:
    """HTTP wrapper for Accubid Anywhere endpoints."""

    def __init__(self, auth: AccubidAuth):
        self.auth = auth
        self._timeout = ClientTimeout(total=Config.ACCUBID_REQUEST_TIMEOUT_SECONDS)
        self._session: Optional[ClientSession] = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=Config.ACCUBID_CIRCUIT_BREAKER_FAILURES,
            cooldown_seconds=Config.ACCUBID_CIRCUIT_BREAKER_COOLDOWN_SECONDS,
            state_file=Config.ACCUBID_CIRCUIT_STATE_FILE or None,
        )
        self._rate_limiter = RateLimiter(requests_per_second=Config.ACCUBID_RATE_LIMIT_RPS)
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_state_file = Config.ACCUBID_CACHE_STATE_FILE
        self._load_cache()

    def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            self._session = ClientSession(timeout=self._timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._cache.clear()
        self._persist_cache()

    def _load_cache(self) -> None:
        if not self._cache_state_file or not Config.ACCUBID_CACHE_ENABLED:
            return
        path = Path(self._cache_state_file)
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for key, record in payload.items():
                if not isinstance(record, dict):
                    continue
                expires_at = float(record.get("expires_at", 0))
                if expires_at <= time.time():
                    continue
                self._cache[key] = (expires_at, record.get("payload"))
        except Exception:
            self._cache = {}

    def _persist_cache(self) -> None:
        if not self._cache_state_file or not Config.ACCUBID_CACHE_ENABLED:
            return
        path = Path(self._cache_state_file)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                key: {"expires_at": expires_at, "payload": payload}
                for key, (expires_at, payload) in self._cache.items()
                if expires_at > time.time()
            }
            path.write_text(json.dumps(serializable), encoding="utf-8")
        except Exception:
            # Cache persistence should not break request processing.
            pass

    def _cache_get(self, key: str) -> Any:
        if not Config.ACCUBID_CACHE_ENABLED:
            return None
        cached = self._cache.get(key)
        if cached is None:
            return None
        expires_at, payload = cached
        if expires_at <= time.time():
            self._cache.pop(key, None)
            self._persist_cache()
            return None
        return payload

    def _cache_set(self, key: str, payload: Any) -> None:
        if not Config.ACCUBID_CACHE_ENABLED:
            return
        ttl = max(0, Config.ACCUBID_CACHE_TTL_SECONDS)
        if ttl == 0:
            return
        self._cache[key] = (time.time() + ttl, payload)
        self._persist_cache()

    def _auth_headers_dict(self, token: str) -> Dict[str, str]:
        if Config.debug_log_outbound_token():
            logger.info(
                "ACCUBID_DEBUG_LOG_OUTBOUND_TOKEN: bearer for next Accubid request "
                "(Postman: paste as Bearer; turn off env when finished): %s",
                token,
            )
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        area: str,
        endpoint_path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = Config.accubid_api_url(area, endpoint_path)
        session = self._get_session()
        token = await self.auth.get_access_token()
        reset_out = set_request_outbound_token(token)
        headers = self._auth_headers_dict(token)
        attempts = 1 + max(0, Config.ACCUBID_CLIENT_RETRY_COUNT)
        last_error: Optional[Exception] = None

        try:
            for attempt in range(attempts):
                try:
                    await self._circuit_breaker.before_request()
                    await self._rate_limiter.acquire()
                    async with session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_body,
                    ) as response:
                        if response.status == 204:
                            await self._circuit_breaker.on_success()
                            return []
                        if response.status >= 400:
                            text = await response.text()
                            await self._circuit_breaker.on_failure()
                            safe_body = text[:2048]
                            err_details = _build_accubid_api_error_details(
                                method=method,
                                endpoint_path=endpoint_path,
                                url=url,
                                safe_body=safe_body,
                                full_text_len=len(text),
                                status_code=response.status,
                            )
                            if response.status == 401 and "900909" in safe_body:
                                logger.warning(
                                    "accubid_api_trimble_900909 endpoint=%s request_url=%s "
                                    "outbound_azp=%s actor_azp=%s actor_sub=%s outbound_token_shape=%s",
                                    endpoint_path,
                                    url,
                                    err_details.get("outbound_azp"),
                                    err_details.get("actor_azp"),
                                    err_details.get("actor_sub"),
                                    err_details.get("outbound_token_shape"),
                                )
                            raise ApiError(
                                message=f"Accubid API error {response.status} for {method} {endpoint_path}",
                                status_code=response.status,
                                details=err_details,
                            )
                        if response.content_type and "json" in response.content_type:
                            payload = await response.json()
                            await self._circuit_breaker.on_success()
                            return payload
                        text = await response.text()
                        await self._circuit_breaker.on_success()
                        return {"raw": text}
                except (ClientError, asyncio.TimeoutError, ApiError) as exc:
                    if isinstance(exc, (ClientError, asyncio.TimeoutError)):
                        await self._circuit_breaker.on_failure()
                    last_error = exc
                    retryable = Config.ACCUBID_CLIENT_RETRYABLE_STATUS_CODES
                    if isinstance(exc, ApiError) and exc.status_code not in retryable:
                        break
                    if attempt < attempts - 1:
                        backoff = min(
                            Config.ACCUBID_CLIENT_RETRY_MAX_SECONDS,
                            Config.ACCUBID_CLIENT_RETRY_BASE_SECONDS * (2**attempt),
                        )
                        await asyncio.sleep(backoff)
                        continue
                    break

            if isinstance(last_error, ApiError):
                raise last_error
            raise ApiError(
                message=str(last_error) if last_error else "Unknown request error",
                details={"method": method, "endpoint_path": endpoint_path},
            )
        finally:
            reset_request_outbound_token(reset_out)

    async def get(self, area: str, endpoint_path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("GET", area, endpoint_path, params=params)

    async def post(self, area: str, endpoint_path: str, json_body: Dict[str, Any]) -> Any:
        return await self._request("POST", area, endpoint_path, json_body=json_body)

    # database
    async def get_databases(self) -> Any:
        cache_key = "database:/databases"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        payload = await self.get("database", "/databases")
        self._cache_set(cache_key, payload)
        return payload

    # project
    async def get_folders(self, database_token: str, parent_folder_id: Optional[str] = None) -> Any:
        cache_key = f"project:/Folders/{database_token}/{parent_folder_id or ''}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        if parent_folder_id:
            payload = await self.get("project", f"/Folders/{database_token}/{parent_folder_id}")
        else:
            payload = await self.get("project", f"/Folders/{database_token}")
        self._cache_set(cache_key, payload)
        return payload

    async def create_folder(self, payload: Dict[str, Any]) -> Any:
        return await self.post("project", "/Folder", payload)

    async def get_projects(
        self,
        database_token: str,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> Any:
        params = {}
        if search:
            params["search"] = search
        if sort_by:
            params["sortBy"] = sort_by
        if sort_direction:
            params["sortDirection"] = sort_direction
        return await self.get("project", f"/Projects/{database_token}", params=params or None)

    async def get_project(self, database_token: str, project_id: str) -> Any:
        return await self.get("project", f"/Project/{database_token}/{project_id}")

    async def create_project(self, payload: Dict[str, Any]) -> Any:
        return await self.post("project", "/Project", payload)

    async def get_last_projects(
        self,
        database_token: str,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> Any:
        params = {}
        if search:
            params["search"] = search
        if sort_by:
            params["sortBy"] = sort_by
        if sort_direction:
            params["sortDirection"] = sort_direction
        return await self.get("project", f"/LastProjects/{database_token}", params=params or None)

    async def get_project_estimate_bid_summaries(self, database_token: str) -> Any:
        return await self.get("project", f"/ProjectEstimateBidSummaries/{database_token}")

    # estimate
    async def get_estimates(
        self,
        database_token: str,
        project_id: str,
        *,
        search: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> Any:
        params = {}
        if search:
            params["search"] = search
        if sort_by:
            params["sortBy"] = sort_by
        if sort_direction:
            params["sortDirection"] = sort_direction
        return await self.get("estimate", f"/Estimates/{database_token}/{project_id}", params=params or None)

    async def get_estimate(self, database_token: str, estimate_id: str) -> Any:
        return await self.get("estimate", f"/Estimate/{database_token}/{estimate_id}")

    async def create_estimate(self, payload: Dict[str, Any]) -> Any:
        return await self.post("estimate", "/Estimate", payload)

    async def get_estimates_by_due_date(
        self, database_token: str, start_date: str, end_date: str
    ) -> Any:
        return await self.get(
            "estimate",
            f"/EstimatesByDueDate/{database_token}/{start_date}/{end_date}",
        )

    async def trigger_estimate_extension_file(
        self,
        database_token: str,
        estimate_id: str,
        connection_id: str,
        bid_summary_id: Optional[str] = None,
    ) -> Any:
        if bid_summary_id:
            path = (
                f"/ExtensionItemDetailsFileSignalR/{database_token}/"
                f"{estimate_id}/{bid_summary_id}/{connection_id}"
            )
        else:
            path = f"/ExtensionItemDetailsFileSignalR/{database_token}/{estimate_id}/{connection_id}"
        return await self.get("estimate", path)

    async def send_estimate_notification_test(self, connection_id: str) -> Any:
        return await self.get("estimate", f"/NotificationTest/{connection_id}")

    # closeout
    async def get_final_price(self, database_token: str, bid_summary_id: str) -> Any:
        return await self.get("closeout", f"/FinalPrice/{database_token}/{bid_summary_id}")

    async def get_bid_breakdown_views(self, database_token: str, estimate_id: str) -> Any:
        return await self.get("closeout", f"/BidBreakdownView/{database_token}/{estimate_id}")

    async def get_bid_breakdown(
        self,
        database_token: str,
        bid_summary_id: str,
        bid_breakdown_view_id: str,
        page_index: Optional[int] = None,
    ) -> Any:
        params = {"pageIndex": page_index} if page_index is not None else None
        return await self.get(
            "closeout",
            f"/BidBreakdown/{database_token}/{bid_summary_id}/{bid_breakdown_view_id}",
            params=params,
        )

    # changeorder
    async def get_contracts(
        self,
        database_token: str,
        project_id: str,
        *,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> Any:
        params = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if sort_by:
            params["sortBy"] = sort_by
        if sort_direction:
            params["sortDirection"] = sort_direction
        return await self.get("changeorder", f"/Contracts/{database_token}/{project_id}", params=params or None)

    async def get_pcos(
        self,
        database_token: str,
        contract_id: str,
        *,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> Any:
        params = {}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        if sort_by:
            params["sortBy"] = sort_by
        if sort_direction:
            params["sortDirection"] = sort_direction
        return await self.get("changeorder", f"/PCOs/{database_token}/{contract_id}", params=params or None)

    async def get_pco(self, database_token: str, pco_id: str) -> Any:
        return await self.get("changeorder", f"/PCO/{database_token}/{pco_id}")

    async def get_contract_cost_distribution(self, database_token: str, contract_id: str) -> Any:
        return await self.get("changeorder", f"/ContractCostDistribution/{database_token}/{contract_id}")

    async def get_contract_quote_labels(self, database_token: str, contract_id: str) -> Any:
        return await self.get("changeorder", f"/ContractQuoteLabels/{database_token}/{contract_id}")

    async def get_contract_subcontract_labels(self, database_token: str, contract_id: str) -> Any:
        return await self.get(
            "changeorder",
            f"/ContractSubcontractLabels/{database_token}/{contract_id}",
        )

    async def get_contract_statuses(self, database_token: str, contract_id: str) -> Any:
        return await self.get("changeorder", f"/ContractStatuses/{database_token}/{contract_id}")

    async def trigger_pco_extension_file(
        self, database_token: str, pco_id: str, connection_id: str
    ) -> Any:
        return await self.get(
            "changeorder",
            f"/ExtensionItemDetailsFileSignalR/{database_token}/{pco_id}/{connection_id}",
        )

    async def send_changeorder_notification_test(self, connection_id: str) -> Any:
        return await self.get("changeorder", f"/NotificationTest/{connection_id}")
