from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parents[1]

load_dotenv(APP_DIR / ".env")


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None and value != "" else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_model: str = _env("OPENAI_MODEL", "gpt-5.5")
    utility_model: str = _env("UTILITY_MODEL", "gpt-5.4-mini")
    self_evaluation_model: str = _env(
        "SELF_EVALUATION_MODEL",
        _env("UTILITY_MODEL", "gpt-5.4-mini"),
    )
    failure_analysis_model: str = _env("FAILURE_ANALYSIS_MODEL", _env("OPENAI_MODEL", "gpt-5.5"))
    model_options: str = _env(
        "AGENT_MODEL_OPTIONS",
        "gpt-5.5,gpt-5.4,gpt-5.4-mini,gpt-5.3-codex-spark",
    )
    max_tool_rounds: int = _env_int("AGENT_MAX_TOOL_ROUNDS", 12)
    post_validation_tool_budget: int = _env_int("AGENT_POST_VALIDATION_TOOL_BUDGET", 1)
    tool_reason_debug: bool = _env_bool("AGENT_TOOL_REASON_DEBUG", False)
    tool_trace_max_items: int = _env_int("AGENT_TOOL_TRACE_MAX_ITEMS", 8)
    tool_model_max_items: int = _env_int("AGENT_TOOL_MODEL_MAX_ITEMS", 12)
    tool_string_max_chars: int = _env_int("AGENT_TOOL_STRING_MAX_CHARS", 700)
    run_log_dir: str = _env("AGENT_RUN_LOG_DIR", str(APP_DIR / "logs"))
    failure_learning_log: str = _env(
        "AGENT_FAILURE_LEARNING_LOG",
        str(APP_DIR / "logs" / "failure_learning.jsonl"),
    )
    run_learning_log: str = _env(
        "AGENT_RUN_LEARNING_LOG",
        str(APP_DIR / "logs" / "run_learning.jsonl"),
    )

    wiki_api_url: str = _env("FOODEX2_WIKI_API_URL", "http://127.0.0.1:8010")
    catalog_api_url: str = _env("FOODEX2_CATALOG_API_URL", "http://localhost:5178")
    validator_api_url: str = _env("FOODEX2_VALIDATOR_API_URL", "http://localhost:5178")
    semantic_search_url: str = _env("FOODEX2_SEMANTIC_SEARCH_URL", "http://127.0.0.1:8001/search")
    semantic_collection: str = _env(
        "FOODEX2_SEMANTIC_COLLECTION", "mtx_monitoring_openai_current"
    )

    catalog_search_terms_path: str = _env("FOODEX2_CATALOG_SEARCH_TERMS_PATH", "/api/search")
    catalog_get_term_path: str = _env("FOODEX2_CATALOG_GET_TERM_PATH", "/api/term/{code}")
    catalog_get_parents_path: str = _env("FOODEX2_CATALOG_GET_PARENTS_PATH", "")
    catalog_get_children_path: str = _env("FOODEX2_CATALOG_GET_CHILDREN_PATH", "")
    catalog_get_implicit_facets_path: str = _env("FOODEX2_CATALOG_GET_IMPLICIT_FACETS_PATH", "")
    catalog_search_facets_path: str = _env("FOODEX2_CATALOG_SEARCH_FACETS_PATH", "/api/search")

    validator_validate_path: str = _env("FOODEX2_VALIDATOR_VALIDATE_PATH", "/api/validate")

    @property
    def model_option_list(self) -> list[str]:
        values = [item.strip() for item in self.model_options.split(",") if item.strip()]
        defaults = [self.openai_model, self.self_evaluation_model, self.utility_model]
        result: list[str] = []
        for item in [*defaults, *values]:
            if item and item not in result:
                result.append(item)
        return result


settings = Settings()
