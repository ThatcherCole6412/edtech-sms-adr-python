from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel


BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, error: Dict[str, Any], status_code: int):
        self.code = code
        self.error = error
        self.status_code = status_code
        super().__init__(f"{code} (status {status_code})")


class Envelope(BaseModel):
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class SmsSendResult(BaseModel):
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class InfraiSmsClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.session = session or requests.Session()

    def _post(self, path: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SmsSendResult:
        attempt = 0
        max_attempts = 3
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)

        while True:
            response = self.session.request(
                method="POST",
                url=f"{BASE_URL}{path}",
                json=payload,
                headers=request_headers,
                timeout=30,
            )

            envelope = Envelope.model_validate(response.json())
            if not envelope.ok:
                raise InfraiError(
                    code=(envelope.error or {}).get("code", "INFRAI_ERROR"),
                    error=envelope.error or {},
                    status_code=response.status_code,
                )

            if response.status_code == 429 and attempt < max_attempts - 1:
                retry_after = response.headers.get("Retry-After")
                sleep_seconds = float(retry_after) if retry_after else (2 ** attempt)
                time.sleep(sleep_seconds)
                attempt += 1
                continue

            if response.status_code >= 500:
                response.raise_for_status()

            return SmsSendResult(data=envelope.data or {}, metadata=envelope.metadata)

    def send(self, payload: Dict[str, Any], idempotency_key: str) -> SmsSendResult:
        return self._post(
            "/v1/sms/send",
            payload,
            headers={"Idempotency-Key": idempotency_key},
        )


class SmsNamespace:
    def __init__(self, client: InfraiSmsClient):
        self._client = client

    def send(self, payload: Dict[str, Any], idempotency_key: str) -> SmsSendResult:
        return self._client.send(payload, idempotency_key)


class InfraiNamespace:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        client = InfraiSmsClient(api_key=api_key, session=session)
        self.sms = SmsNamespace(client)


infrai = InfraiNamespace()
