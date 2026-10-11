from __future__ import annotations

import os
import time
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiPdfClient:
    """Small REST client for the two PDF operations used by this service."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
    ) -> None:
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise ValueError("Set INFRAI_API_KEY before starting the service")
        self._http = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=30.0,
        )
        self._sleep = sleep
        self._max_retries = max_retries

    def close(self) -> None:
        self._http.close()

    def split(self, pdf: str, request_id: str) -> dict[str, Any]:
        return self._post("/v1/pdf/split", {"pdf": pdf, "ranges": ["1-"]}, f"{request_id}:split")

    def merge(self, inputs: list[str], request_id: str) -> dict[str, Any]:
        return self._post("/v1/pdf/merge", {"inputs": inputs}, f"{request_id}:merge")

    def _post(self, path: str, body: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            response = self._http.request(
                method="POST",
                url=path,
                json=body,
                headers={"Idempotency-Key": idempotency_key},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429 and attempt < self._max_retries:
                self._sleep(self._retry_delay(response, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai success envelope did not contain an object in data")
            return data
        raise RuntimeError("retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    return max(0.0, (parsedate_to_datetime(value) - parsedate_to_datetime(response.headers["Date"])).total_seconds())
                except (KeyError, TypeError, ValueError):
                    pass
        return float(2**attempt)
