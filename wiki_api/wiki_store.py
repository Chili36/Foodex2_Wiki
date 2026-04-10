from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
import re
from typing import Any

import yaml


INDEX_ENTRY_RE = re.compile(r"^- \[[^\]]+\]\(([^)]+)\):\s*(.+)$")
GUIDING_PRINCIPLES_HEADER = "## Guiding Principles"
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TRAILING_SOURCE_CITATION_RE = re.compile(
    r"\s*\((?:EFSA guidance|Training|ChemMon|VMPR|"
    r"\d{4} maintenance|docs/[^)]+|BUSINESS-RULES[^)]*|"
    r"VALIDATION_RULES_SUMMARY[^)]*)[^)]*\)\s*$"
)
SOURCE_ONLY_LINE_RE = re.compile(
    r"^\s*\((?:EFSA guidance|Training|ChemMon|VMPR|\d{4} maintenance)[^)]*\)\s*$"
)


@dataclass(frozen=True)
class WikiPage:
    name: str
    title: str
    summary: str
    sources: list[str]
    related: list[str]
    content: str
    body: str


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    lines = raw.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, raw
    closing_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            closing_idx = idx
            break
    if closing_idx is None:
        return {}, raw
    frontmatter = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :]).lstrip("\n")
    data = yaml.safe_load(frontmatter) or {}
    if not isinstance(data, dict):
        data = {}
    return data, body


class WikiStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.guidance_dir = self.root / "raw" / "efsa-guidance"
        self.index_path = self.root / "index.md"
        self.log_path = self.root / "log.md"
        self.root_docs: dict[str, Path] = {
            "README.md": self.root / "README.md",
            "PROJECT_CONTEXT.md": self.root / "PROJECT_CONTEXT.md",
            "INGEST_WORKFLOW.md": self.root / "INGEST_WORKFLOW.md",
            "SCHEMA.md": self.root / "SCHEMA.md",
            "RUNTIME_RULES.md": self.root / "RUNTIME_RULES.md",
        }

    @cached_property
    def _summaries(self) -> dict[str, str]:
        raw = self.index_path.read_text(encoding="utf-8")
        summaries: dict[str, str] = {}
        for line in raw.splitlines():
            match = INDEX_ENTRY_RE.match(line)
            if not match:
                continue
            target, summary = match.groups()
            name = Path(target).name
            summaries[name] = summary.strip()
        summaries["index.md"] = "Top-level catalog for the FoodEx2 wiki layer."
        summaries["log.md"] = "Chronological record of wiki ingests and changes."
        summaries["README.md"] = "Repo overview, current status, directory layout, and working conventions."
        summaries["PROJECT_CONTEXT.md"] = (
            "What this wiki is for, why it exists, and the LLM-wiki operating model behind it."
        )
        summaries["INGEST_WORKFLOW.md"] = (
            "Practical playbook for turning raw PDFs into stable topic pages."
        )
        summaries["SCHEMA.md"] = (
            "Page types, frontmatter fields, section conventions, and ingest schema for the FoodEx2 wiki."
        )
        summaries["RUNTIME_RULES.md"] = (
            "Compact prompt-facing rules file attached by context-pack before supporting guidance pages."
        )
        return summaries

    @cached_property
    def _guiding_principles(self) -> list[str]:
        raw = self.index_path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        in_section = False
        principles: list[str] = []
        for line in lines:
            if line.strip() == GUIDING_PRINCIPLES_HEADER:
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section and line.startswith("- "):
                principles.append(line[2:].strip())
        return principles

    def list_pages(self) -> list[str]:
        names = [*self.root_docs.keys(), *(page.name for page in self.guidance_dir.glob("*.md"))]
        return sorted(names)

    def allowed_page_names(self) -> set[str]:
        return {"index.md", "log.md", *self.list_pages()}

    def normalize_page_name(self, page_name: str) -> str:
        cleaned = page_name.strip().replace("\\", "/")
        if cleaned in {"index.md", "log.md", *self.root_docs.keys()}:
            return cleaned
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if cleaned.startswith("raw/efsa-guidance/"):
            cleaned = cleaned.split("/")[-1]
        else:
            cleaned = Path(cleaned).name
        return cleaned

    def read_page(self, page_name: str) -> WikiPage:
        normalized_name = self.normalize_page_name(page_name)
        if normalized_name not in self.allowed_page_names():
            raise FileNotFoundError(f"Unknown wiki page: {page_name}")
        if normalized_name == "index.md":
            path = self.index_path
        elif normalized_name == "log.md":
            path = self.log_path
        elif normalized_name in self.root_docs:
            path = self.root_docs[normalized_name]
        else:
            path = self.guidance_dir / normalized_name
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = split_frontmatter(raw)
        title = str(frontmatter.get("title") or page_name)
        sources = [
            str(item) for item in frontmatter.get("sources", []) if isinstance(item, str)
        ]
        related = [
            str(item) for item in frontmatter.get("related", []) if isinstance(item, str)
        ]
        summary = self._summaries.get(page_name, "")
        return WikiPage(
            name=normalized_name,
            title=title,
            summary=self._summaries.get(normalized_name, summary),
            sources=sources,
            related=related,
            content=raw,
            body=body,
        )

    def catalog(self) -> list[WikiPage]:
        return [self.read_page(name) for name in self.list_pages()]

    def guiding_principles(self) -> list[str]:
        return list(self._guiding_principles)

    def clean_content_for_model(self, page: WikiPage) -> str:
        cleaned = HTML_COMMENT_RE.sub("", page.body)
        cleaned_lines: list[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.rstrip()
            if SOURCE_ONLY_LINE_RE.match(line):
                continue
            line = TRAILING_SOURCE_CITATION_RE.sub("", line)
            cleaned_lines.append(line.rstrip())

        collapsed: list[str] = []
        blank_run = 0
        for line in cleaned_lines:
            if line.strip():
                blank_run = 0
                collapsed.append(line)
            else:
                blank_run += 1
                if blank_run <= 1:
                    collapsed.append("")
        return "\n".join(collapsed).strip()
