"""Shared validation and I/O helpers for coverage evaluation commands."""
from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml

from evals.coverage.coverage_index import REPO_ROOT
from evals.coverage.local_model import require_local_url


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload


def resolve_env(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("env:"):
        key = value[4:]
        resolved = os.getenv(key)
        if not resolved:
            raise ValueError(f"required environment variable {key} is not set")
        return resolved
    if isinstance(value, dict):
        return {key: resolve_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_env(item) for item in value]
    return value


def local_model_config(config: dict[str, Any]) -> dict[str, Any]:
    resolved = resolve_env(config)
    provider = str(resolved.get("provider") or "").casefold()
    if provider not in {"lmstudio", "lm-studio"}:
        raise ValueError(f"default coverage models must use provider lmstudio, got {provider!r}")
    model = str(resolved.get("model") or "").strip()
    if not model:
        raise ValueError("local model config needs a model")
    base_url = require_local_url(
        str(resolved.get("base_url") or "http://127.0.0.1:1234/v1")
    )
    return {**resolved, "provider": "lmstudio", "model": model, "base_url": base_url}


def service_model_name(config: dict[str, Any]) -> str:
    model = str(config["model"])
    return model if model.casefold().startswith("lmstudio:") else f"lmstudio:{model}"


def post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    require_local_url(url)
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"wiki endpoint returned HTTP {exc.code}: {body}") from exc
    except (error.URLError, TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"wiki endpoint unavailable at {url}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("wiki endpoint returned non-object JSON")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path
