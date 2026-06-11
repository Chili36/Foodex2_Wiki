from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import ssl
import sys
from typing import Iterable, Literal
import urllib.error
import urllib.parse
import urllib.request

from .rag_index import (
    DEFAULT_WIKI_CATEGORIES,
    DEFAULT_WIKI_CHUNK_MAX_CHARS,
    get_wiki_rag_status,
)
from .wiki_store import (
    MARKDOWN_LINK_RE,
    PROMPT_CONTEXT_PAGE_CATEGORIES,
    SOURCE_TIER_VALUES,
    WIKILINK_RE,
    WikiPage,
    WikiStore,
)


Severity = Literal["error", "warning"]

EXTERNAL_LINK_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
INDEX_ENTRY_RE = re.compile(r"^- \[[^\]]+\]\(([^)]+)\):")
FENCED_CODE_RE = re.compile(r"(^|\n)(```|~~~).*?(?=\n\2|\Z)(?:\n\2)?", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
VIRTUAL_SOURCE_PREFIXES = ("docs/",)
VIRTUAL_SOURCE_NAMES = {
    "BUSINESS-RULES.md",
    "BUSINESS-RULES-COMPACT.json",
}
HTTP_TIMEOUT_SECONDS = 8
HTTP_USER_AGENT = "FoodEx2-Wiki-Doctor/1.0"


@dataclass(frozen=True)
class DoctorIssue:
    severity: Severity
    check: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "check": self.check,
            "location": self.location,
            "message": self.message,
        }


@dataclass(frozen=True)
class DoctorReport:
    issues: list[DoctorIssue]

    @property
    def errors(self) -> list[DoctorIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[DoctorIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def as_dict(self) -> dict[str, object]:
        return {
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.as_dict() for issue in self.issues],
        }


def run_doctor(
    root: Path | str = ".",
    *,
    check_external_links: bool = False,
    check_rag_index: bool = False,
    rag_collection: str | None = None,
    rag_qdrant_url: str | None = None,
    rag_embedding_model: str | None = None,
    rag_embedding_dimension: int | None = None,
    rag_categories: str = DEFAULT_WIKI_CATEGORIES,
    rag_max_chars: int = DEFAULT_WIKI_CHUNK_MAX_CHARS,
) -> DoctorReport:
    store = WikiStore(root)
    issues: list[DoctorIssue] = []

    pages = {page.name: page for page in store.catalog()}
    all_page_names = store.allowed_page_names()

    issues.extend(_check_category_registration(store, pages))
    issues.extend(_check_index_registration(store, pages))
    issues.extend(_check_wikilinks(store, pages.values()))
    issues.extend(_check_markdown_links(store, pages.values()))
    if check_external_links:
        issues.extend(_check_external_markdown_links(pages.values()))
    issues.extend(_check_prompt_projection(store, pages.values()))
    issues.extend(_check_graph_connectivity(store))
    issues.extend(_check_source_tiers(pages.values()))
    issues.extend(_check_source_references(store, pages.values()))
    if check_rag_index:
        issues.extend(
            _check_rag_index(
                root=Path(root),
                collection=rag_collection,
                qdrant_url=rag_qdrant_url,
                embedding_model=rag_embedding_model,
                embedding_dimension=rag_embedding_dimension,
                categories=rag_categories,
                max_chars=rag_max_chars,
            )
        )

    # Keep index/log in the allowed-page consistency check even though catalog() intentionally
    # omits them as root docs.
    for expected in ("index.md", "log.md"):
        if expected not in all_page_names:
            issues.append(
                DoctorIssue(
                    "error",
                    "allowed_pages",
                    expected,
                    "Core wiki page is missing from allowed_page_names().",
                )
            )

    return DoctorReport(sorted(issues, key=lambda item: (item.severity, item.check, item.location)))


def _check_rag_index(
    *,
    root: Path,
    collection: str | None,
    qdrant_url: str | None,
    embedding_model: str | None,
    embedding_dimension: int | None,
    categories: str,
    max_chars: int,
) -> Iterable[DoctorIssue]:
    status = get_wiki_rag_status(
        root=root,
        collection=collection,
        qdrant_url=qdrant_url,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        categories=categories,
        max_chars=max_chars,
    )
    if status["ok"]:
        return []

    issues: list[DoctorIssue] = []
    collection_name = str(status.get("collection", "wiki-rag"))
    for message in status.get("errors", []):
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                collection_name,
                f"Could not inspect Qdrant wiki index: {message}",
            )
        )

    indexed = status.get("indexed", {})
    if indexed.get("collection_exists") and indexed.get("chunk_count") == 0:
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                collection_name,
                "Qdrant wiki index exists but contains no indexed markdown chunks.",
            )
        )

    drift = status.get("drift", {})
    for page_name in drift.get("missing_pages", []):
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                str(page_name),
                "Markdown page is selected for wiki RAG but is missing from Qdrant.",
            )
        )
    for page_name in drift.get("stale_pages", []):
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                str(page_name),
                "Markdown page has stale, missing, or embedding-mismatched Qdrant chunks.",
            )
        )
    for page_name in drift.get("orphaned_pages", []):
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                str(page_name),
                "Qdrant contains chunks for a page no longer selected for wiki RAG.",
            )
        )

    payloadless = indexed.get("payloadless_points", 0)
    if payloadless:
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                collection_name,
                f"Qdrant contains {payloadless} point(s) without wiki chunk payload metadata.",
            )
        )
    duplicate_chunk_ids = indexed.get("duplicate_chunk_ids", [])
    if duplicate_chunk_ids:
        issues.append(
            DoctorIssue(
                "error",
                "rag_index",
                collection_name,
                f"Qdrant contains duplicate wiki chunk ids: {', '.join(duplicate_chunk_ids[:10])}",
            )
        )
    return issues


def _check_category_registration(
    store: WikiStore, pages: dict[str, WikiPage]
) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    all_page_names = store.allowed_page_names()
    explicitly_categorized = set(store.page_categories)

    for name in sorted(explicitly_categorized - all_page_names):
        issue_list.append(
            DoctorIssue(
                "error",
                "category_registration",
                name,
                "page_categories contains a page that is not served by the wiki store.",
            )
        )

    for name in sorted(pages):
        if name not in explicitly_categorized:
            issue_list.append(
                DoctorIssue(
                    "error",
                    "category_registration",
                    name,
                    "Served page is missing explicit page_categories registration.",
                )
            )
        elif store.page_category(name) == "unknown":
            issue_list.append(
                DoctorIssue(
                    "error",
                    "category_registration",
                    name,
                    "Served page resolves to unknown page category.",
                )
            )

    return issue_list


def _check_index_registration(store: WikiStore, pages: dict[str, WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    index_targets = _index_targets(store.index_path)

    for name in sorted(pages):
        if name not in index_targets:
            issue_list.append(
                DoctorIssue(
                    "error",
                    "index_registration",
                    name,
                    "Served page is missing from index.md.",
                )
            )

    for name in sorted(index_targets):
        if name == "foodex2_docs":
            continue
        if store.resolve_page_reference(name) is None:
            target_path = store.root / name
            if not target_path.exists():
                issue_list.append(
                    DoctorIssue(
                        "error",
                        "index_registration",
                        name,
                        "index.md links to a page or local path that does not exist.",
                    )
                )

    return issue_list


def _index_targets(index_path: Path) -> set[str]:
    targets: set[str] = set()
    for line in index_path.read_text(encoding="utf-8").splitlines():
        match = INDEX_ENTRY_RE.match(line)
        if not match:
            continue
        raw = match.group(1).split("#", 1)[0].strip()
        targets.add(Path(raw).name)
    return targets


def _check_wikilinks(store: WikiStore, pages: Iterable[WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    for page in pages:
        references = [*page.related, *WIKILINK_RE.findall(_without_markdown_code(page.body))]
        for reference in references:
            cleaned = reference.strip()
            if cleaned.startswith("[[") and cleaned.endswith("]]"):
                cleaned = cleaned[2:-2]
            target = cleaned.split("|", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            if target.endswith(".md"):
                issue_list.append(
                    DoctorIssue(
                        "error",
                        "wikilinks",
                        page.name,
                        f"Wikilink should be extensionless: [[{cleaned}]].",
                    )
                )
            if store.resolve_page_reference(cleaned) is None:
                issue_list.append(
                    DoctorIssue(
                        "error",
                        "wikilinks",
                        page.name,
                        f"Unresolved wikilink reference: [[{cleaned}]].",
                    )
                )
    return issue_list


def _check_markdown_links(store: WikiStore, pages: Iterable[WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    for page in pages:
        page_path = _page_path(store, page.name)
        for match in MARKDOWN_LINK_RE.finditer(_without_markdown_code(page.body)):
            raw_target = match.group(2).strip()
            target_without_anchor = raw_target.split("#", 1)[0]
            if not target_without_anchor or _is_external_link(target_without_anchor):
                continue
            if store.resolve_page_reference(target_without_anchor) is not None:
                continue

            candidate = (page_path.parent / target_without_anchor).resolve()
            try:
                candidate.relative_to(store.root.resolve())
            except ValueError:
                issue_list.append(
                    DoctorIssue(
                        "error",
                        "markdown_links",
                        page.name,
                        f"Local markdown link escapes the repo: {raw_target}",
                    )
                )
                continue
            if not candidate.exists():
                issue_list.append(
                    DoctorIssue(
                        "error",
                        "markdown_links",
                        page.name,
                        f"Broken local markdown link: {raw_target}",
                    )
                )
    return issue_list


def _check_external_markdown_links(pages: Iterable[WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    links: dict[str, set[str]] = {}
    for page in pages:
        for match in MARKDOWN_LINK_RE.finditer(_without_markdown_code(page.body)):
            raw_target = match.group(2).strip()
            target_without_fragment = urllib.parse.urldefrag(raw_target)[0]
            if target_without_fragment.startswith(("http://", "https://")):
                links.setdefault(target_without_fragment, set()).add(page.name)

    for url, locations in sorted(links.items()):
        problem = _external_url_problem(url)
        if not problem:
            continue
        issue_list.append(
            DoctorIssue(
                "warning",
                "external_links",
                ", ".join(sorted(locations)),
                problem,
            )
        )
    return issue_list


def _external_url_problem(url: str) -> str | None:
    last_error: str | None = None
    for method in ("HEAD", "GET"):
        status_or_error = _external_status(url, method)
        if isinstance(status_or_error, int):
            status = status_or_error
            if status < 400 or status in {401, 403}:
                return None
            if method == "HEAD":
                continue
            return f"External markdown link returned HTTP {status}: {url}"
        last_error = status_or_error
    return f"External markdown link could not be checked: {url} ({last_error})"


def _external_status(url: str, method: str) -> int | str:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": HTTP_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            return _external_status_without_certificate_validation(url, method)
        return str(exc.reason)
    except TimeoutError:
        return "timed out"


def _external_status_without_certificate_validation(url: str, method: str) -> int | str:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": HTTP_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
            context=ssl._create_unverified_context(),
        ) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        return str(exc.reason)
    except TimeoutError:
        return "timed out"


def _is_external_link(target: str) -> bool:
    return bool(EXTERNAL_LINK_RE.match(target))


def _without_markdown_code(content: str) -> str:
    without_blocks = FENCED_CODE_RE.sub("\n", content)
    return INLINE_CODE_RE.sub("", without_blocks)


def _page_path(store: WikiStore, page_name: str) -> Path:
    normalized = store.normalize_page_name(page_name)
    if normalized == "index.md":
        return store.index_path
    if normalized == "log.md":
        return store.log_path
    if normalized in store.root_docs:
        return store.root_docs[normalized]
    return store.guidance_dir / normalized


def _check_prompt_projection(store: WikiStore, pages: Iterable[WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    for page in pages:
        category = store.page_category(page.name)
        projected = store.prompt_content_for_context_pack(page)
        if category in PROMPT_CONTEXT_PAGE_CATEGORIES and not projected:
            issue_list.append(
                DoctorIssue(
                    "error",
                    "prompt_projection",
                    page.name,
                    "Prompt-facing page category produced empty context-pack content.",
                )
            )
        if category not in PROMPT_CONTEXT_PAGE_CATEGORIES and projected:
            issue_list.append(
                DoctorIssue(
                    "error",
                    "prompt_projection",
                    page.name,
                    "Non-prompt page category unexpectedly produced context-pack content.",
                )
            )
    return issue_list


def _check_graph_connectivity(store: WikiStore) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    graph = store.graph_data()
    for page_name in graph["summary"].get("orphan_pages", []):
        issue_list.append(
            DoctorIssue(
                "error",
                "graph_connectivity",
                str(page_name),
                "Page has neither incoming nor outgoing graph links.",
            )
        )
    return issue_list


def _check_source_references(store: WikiStore, pages: Iterable[WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    known_files = _known_source_files(store.root)
    for page in pages:
        for source in page.sources:
            if _is_virtual_source(source):
                continue
            if _source_exists(store.root, source, known_files):
                continue
            issue_list.append(
                DoctorIssue(
                    "warning",
                    "source_references",
                    page.name,
                    f"Source reference does not resolve to a committed file: {source}",
                )
            )
    return issue_list


def _check_source_tiers(pages: Iterable[WikiPage]) -> Iterable[DoctorIssue]:
    issue_list: list[DoctorIssue] = []
    for page in pages:
        if page.source_tier is None:
            continue
        if page.source_tier in SOURCE_TIER_VALUES:
            continue
        issue_list.append(
            DoctorIssue(
                "error",
                "source_tier",
                page.name,
                (
                    f"Unknown source_tier `{page.source_tier}`. "
                    f"Allowed values: {', '.join(sorted(SOURCE_TIER_VALUES))}."
                ),
            )
        )
    return issue_list


def _known_source_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for directory in [root, root / "foodex2_docs", root / "raw" / "efsa-guidance"]:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file():
                files[_source_key(path.name)] = path
    return files


def _is_virtual_source(source: str) -> bool:
    return source in VIRTUAL_SOURCE_NAMES or source.startswith(VIRTUAL_SOURCE_PREFIXES)


def _source_exists(root: Path, source: str, known_files: dict[str, Path]) -> bool:
    direct_candidates = [
        root / source,
        root / "foodex2_docs" / source,
        root / "raw" / "efsa-guidance" / source,
    ]
    if any(candidate.exists() for candidate in direct_candidates):
        return True
    return _source_key(Path(source).name) in known_files


def _source_key(name: str) -> str:
    key = name.lower()
    key = key.replace("‐", "-").replace("–", "-").replace("—", "-")
    key = re.sub(r"\s+", " ", key)
    key = re.sub(r"\s*-\s*-\s*", " - ", key)
    key = re.sub(r"\s*-\s*", " - ", key)
    return key.strip()


def _render_text(report: DoctorReport) -> str:
    lines = [
        f"Wiki doctor: {len(report.errors)} error(s), {len(report.warnings)} warning(s)",
    ]
    if not report.issues:
        lines.append("All deterministic wiki maintenance checks passed.")
        return "\n".join(lines)

    for severity in ("error", "warning"):
        matching = [issue for issue in report.issues if issue.severity == severity]
        if not matching:
            continue
        lines.append("")
        lines.append(f"{severity.title()}s:")
        for issue in matching:
            lines.append(f"- [{issue.check}] {issue.location}: {issue.message}")
    return "\n".join(lines)


def _render_github(report: DoctorReport) -> str:
    lines = [_render_text(report)]
    for issue in report.errors:
        location = issue.location.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        message = issue.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        lines.append(f"::error title={issue.check},file={location}::{message}")
    for issue in report.warnings:
        location = issue.location.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        message = issue.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        lines.append(f"::warning title={issue.check},file={location}::{message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic FoodEx2 wiki maintenance checks.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "--format",
        choices=("text", "json", "github"),
        default="text",
        help="Output format. Use github for GitHub Actions annotations.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Exit non-zero when warnings are present.",
    )
    parser.add_argument(
        "--check-external-links",
        action="store_true",
        help="Also check external http(s) markdown links and report failures as warnings.",
    )
    parser.add_argument(
        "--check-rag-index",
        action="store_true",
        help="Also compare the curated markdown wiki with the configured Qdrant wiki index.",
    )
    parser.add_argument("--rag-collection", default=None, help="Qdrant wiki collection override.")
    parser.add_argument("--rag-qdrant-url", default=None, help="Qdrant URL override.")
    parser.add_argument("--rag-embedding-model", default=None, help="Expected wiki embedding model.")
    parser.add_argument(
        "--rag-embedding-dimension",
        type=int,
        default=None,
        help="Expected wiki embedding dimension.",
    )
    parser.add_argument(
        "--rag-categories",
        default=DEFAULT_WIKI_CATEGORIES,
        help="Comma-separated wiki categories included in the Qdrant markdown index.",
    )
    parser.add_argument(
        "--rag-max-chars",
        type=int,
        default=DEFAULT_WIKI_CHUNK_MAX_CHARS,
        help="Markdown chunk max character length used by the wiki indexer.",
    )
    args = parser.parse_args(argv)

    report = run_doctor(
        Path(args.root),
        check_external_links=args.check_external_links,
        check_rag_index=args.check_rag_index,
        rag_collection=args.rag_collection,
        rag_qdrant_url=args.rag_qdrant_url,
        rag_embedding_model=args.rag_embedding_model,
        rag_embedding_dimension=args.rag_embedding_dimension,
        rag_categories=args.rag_categories,
        rag_max_chars=args.rag_max_chars,
    )
    if args.format == "json":
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    elif args.format == "github":
        print(_render_github(report))
    else:
        print(_render_text(report))

    if report.errors or (args.strict_warnings and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
