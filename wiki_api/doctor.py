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

from .wiki_store import (
    MARKDOWN_LINK_RE,
    PROMPT_CONTEXT_PAGE_CATEGORIES,
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


def run_doctor(root: Path | str = ".", *, check_external_links: bool = False) -> DoctorReport:
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
    issues.extend(_check_source_references(store, pages.values()))

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
    args = parser.parse_args(argv)

    report = run_doctor(Path(args.root), check_external_links=args.check_external_links)
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
