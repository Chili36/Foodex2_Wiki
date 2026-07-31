from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed
    except (TimeoutError, socket.timeout) as exc:
        return 598, {"detail": f"request timed out after {timeout:.1f}s: {exc}"}
    except error.URLError as exc:
        return 599, {"detail": str(exc)}


def _trace_value(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _run_case(
    *,
    url: str,
    question: str,
    selector_model: str,
    answerer_model: str,
    max_pages: int,
    include_page_content: bool,
    use_graph_expansion: bool,
    timeout: float,
) -> dict[str, Any]:
    payload = {
        "question": question,
        "max_pages": max_pages,
        "include_page_content": include_page_content,
        "use_graph_expansion": use_graph_expansion,
        "selector_model": selector_model,
        "answerer_model": answerer_model,
    }
    started = time.perf_counter()
    status_code, data = _post_json(url, payload, timeout)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    trace = data.get("trace", {}) if isinstance(data, dict) else {}
    return {
        "selector_model": selector_model,
        "answerer_model": answerer_model,
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "trace_total_ms": _trace_value(trace, "total", "request_wall_time_ms"),
        "total_tokens": _trace_value(trace, "total", "total_tracked_tokens"),
        "selector_tokens": _trace_value(trace, "retrieval", "token_summary", "total_tracked_tokens"),
        "answerer_tokens": _trace_value(trace, "answerer", "token_summary", "total_tracked_tokens"),
        "selector_trace_model": _trace_value(trace, "retrieval", "model"),
        "answerer_trace_model": _trace_value(trace, "answerer", "model"),
        "pages_used": data.get("pages_used", []) if isinstance(data, dict) else [],
        "citations": data.get("citations", []) if isinstance(data, dict) else [],
        "answer": data.get("answer", "") if isinstance(data, dict) else "",
        "error": data.get("detail") if isinstance(data, dict) else data,
        "raw": data,
    }


def _print_table(results: list[dict[str, Any]]) -> None:
    headers = [
        "selector",
        "answerer",
        "status",
        "tokens",
        "selector",
        "answerer",
        "ms",
        "pages",
        "citations",
    ]
    rows = []
    for result in results:
        rows.append(
            [
                result["selector_model"],
                result["answerer_model"],
                str(result["status_code"]),
                str(result["total_tokens"] or ""),
                str(result["selector_tokens"] or ""),
                str(result["answerer_tokens"] or ""),
                str(result["trace_total_ms"] or result["elapsed_ms"]),
                str(len(result["pages_used"])),
                ", ".join(result["citations"][:3]),
            ]
        )
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run /wiki/ask against a series of selector/answerer model choices."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8010/wiki/ask",
        help="Full /wiki/ask URL.",
    )
    parser.add_argument("--question", required=True, help="Question to send to /wiki/ask.")
    parser.add_argument(
        "--models",
        default="",
        help="Comma-separated models to use for both selector_model and answerer_model.",
    )
    parser.add_argument(
        "--selector-model",
        default="",
        help="Fixed selector model. Use with --answerer-models to compare answerers.",
    )
    parser.add_argument(
        "--answerer-models",
        default="",
        help="Comma-separated answerer models. Requires --selector-model unless --models is used.",
    )
    parser.add_argument("--max-pages", type=int, default=7)
    parser.add_argument("--include-page-content", action="store_true")
    graph_expansion_group = parser.add_mutually_exclusive_group()
    graph_expansion_group.add_argument(
        "--graph-expansion",
        dest="use_graph_expansion",
        action="store_true",
        help="Use remaining max-pages slots for ranked related-page summaries.",
    )
    graph_expansion_group.add_argument(
        "--no-graph-expansion",
        dest="use_graph_expansion",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(use_graph_expansion=False)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file for full responses.",
    )
    args = parser.parse_args()

    cases: list[tuple[str, str]] = []
    models = _split_csv(args.models)
    if models:
        cases = [(model, model) for model in models]
    else:
        answerer_models = _split_csv(args.answerer_models)
        if not args.selector_model or not answerer_models:
            parser.error("provide --models or provide both --selector-model and --answerer-models")
        cases = [(args.selector_model.strip(), model) for model in answerer_models]

    results = []
    for selector_model, answerer_model in cases:
        result = _run_case(
            url=args.url,
            question=args.question,
            selector_model=selector_model,
            answerer_model=answerer_model,
            max_pages=args.max_pages,
            include_page_content=args.include_page_content,
            use_graph_expansion=args.use_graph_expansion,
            timeout=args.timeout,
        )
        results.append(result)
        status = result["status_code"]
        tokens = result["total_tokens"] or ""
        elapsed = result["trace_total_ms"] or result["elapsed_ms"]
        print(
            f"completed {selector_model} / {answerer_model}: "
            f"status={status} tokens={tokens} ms={elapsed}",
            flush=True,
        )

    _print_table(results)
    print()
    for result in results:
        print(f"## {result['selector_model']} / {result['answerer_model']}")
        if result["status_code"] == 200:
            print(result["answer"].strip())
        else:
            print(f"ERROR: {result['error']}")
        print()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote full results to {args.output}")

    return 0 if all(result["status_code"] == 200 for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
