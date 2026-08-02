"""DeepEval-compatible OpenAI chat wrapper with local-host enforcement."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import socket
import time
from typing import Any
from urllib import error, parse, request

# The default path promises no hosted calls. DeepEval telemetry is therefore
# disabled before importing any DeepEval module.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")

try:
    from deepeval.models import DeepEvalBaseLLM
except ImportError:  # Core index/chunk/staleness commands do not require DeepEval.
    DeepEvalBaseLLM = object  # type: ignore[assignment,misc]


def _is_private_host(url: str) -> bool:
    host = parse.urlparse(url).hostname
    if not host:
        return False
    if host.casefold() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def require_local_url(url: str) -> str:
    normalized = url.rstrip("/")
    if parse.urlparse(normalized).scheme not in {"http", "https"} or not _is_private_host(normalized):
        raise ValueError(
            f"default coverage path rejects non-local endpoint {url!r}; "
            "only localhost, loopback, private, or link-local LM Studio hosts are allowed"
        )
    return normalized


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.S | re.I)
    if fenced:
        stripped = fenced.group(1)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = min((index for index in (stripped.find("{"), stripped.find("[")) if index >= 0), default=-1)
        if start < 0:
            raise
        closing = "}" if stripped[start] == "{" else "]"
        end = stripped.rfind(closing)
        if end < start:
            raise
        return json.loads(stripped[start : end + 1])


def _transient_http_error(status: int, body: str) -> bool:
    lowered = body.casefold()
    return status in {408, 425, 429} or status >= 500 or any(
        marker in lowered
        for marker in (
            "peer_keepalive_timeout",
            "connection entered error state",
            "temporarily unavailable",
            "connection reset",
        )
    )


class LMStudioDeepEvalModel(DeepEvalBaseLLM):  # type: ignore[misc]
    """Custom DeepEval model backed by an LM Studio OpenAI-compatible server."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:1234/v1",
        api_key_env: str | None = None,
        temperature: float = 0.0,
        seed: int = 42,
        max_tokens: int = 2048,
        timeout: float = 180.0,
        max_retries: int = 3,
        allow_remote: bool = False,
    ) -> None:
        self.model_name = model
        self.base_url = base_url.rstrip("/") if allow_remote else require_local_url(base_url)
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        if DeepEvalBaseLLM is object:
            self.name = model
            self.model = self.load_model()
        else:
            super().__init__(model=model)

    def load_model(self, *args: Any, **kwargs: Any) -> "LMStudioDeepEvalModel":
        return self

    def get_model_name(self, *args: Any, **kwargs: Any) -> str:
        return self.model_name

    def supports_temperature(self) -> bool:
        return True

    def supports_json_mode(self) -> bool:
        return True

    def supports_structured_outputs(self) -> bool:
        return True

    def _completion(self, prompt: str, *, schema: Any = None) -> str:
        messages: list[dict[str, str]] = []
        if schema is not None:
            schema_json = (
                schema.model_json_schema()
                if hasattr(schema, "model_json_schema")
                else schema
                if isinstance(schema, dict)
                else {"type": "object"}
            )
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Return JSON only matching this schema: "
                        + json.dumps(schema_json, ensure_ascii=False)
                    ),
                }
            )
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }
        if schema is not None:
            schema_json = (
                schema.model_json_schema()
                if hasattr(schema, "model_json_schema")
                else schema
                if isinstance(schema, dict)
                else {"type": "object", "additionalProperties": True}
            )
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "coverage_response",
                    "strict": False,
                    "schema": schema_json,
                },
            }
        headers = {"Content-Type": "application/json"}
        if self.api_key_env and os.getenv(self.api_key_env):
            headers["Authorization"] = f"Bearer {os.environ[self.api_key_env]}"
        for attempt in range(self.max_retries + 1):
            req = request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if attempt >= self.max_retries or not _transient_http_error(exc.code, body):
                    raise RuntimeError(f"LM Studio returned HTTP {exc.code}: {body}") from exc
            except (error.URLError, TimeoutError, socket.timeout) as exc:
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"LM Studio is unavailable at {self.base_url}: {exc}"
                    ) from exc
            time.sleep(min(2**attempt, 8))
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LM Studio response did not contain assistant content") from exc

    def generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        text = self._completion(prompt, schema=schema)
        if schema is None:
            return text
        payload = _extract_json(text)
        return schema.model_validate(payload) if hasattr(schema, "model_validate") else payload

    async def a_generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.generate, prompt, schema=schema, **kwargs)

    def generate_json(
        self, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        original_seed = self.seed
        retry_prompt = prompt
        try:
            for attempt in range(self.max_retries + 1):
                self.seed = original_seed + attempt
                try:
                    payload = _extract_json(
                        self._completion(retry_prompt, schema=json_schema or dict)
                    )
                    if not isinstance(payload, dict):
                        raise ValueError("model returned JSON that was not an object")
                    return payload
                except (json.JSONDecodeError, ValueError):
                    if attempt >= self.max_retries:
                        raise
                    retry_prompt = (
                        prompt
                        + "\n\nYour previous structured response was invalid or truncated. "
                        "Return substantially more compact JSON. Use fewer items if needed, "
                        "but keep every emitted string complete and close all JSON strings/arrays."
                    )
        finally:
            self.seed = original_seed
        raise RuntimeError("unreachable JSON generation state")
