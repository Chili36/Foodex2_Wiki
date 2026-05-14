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
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TRAILING_SOURCE_CITATION_RE = re.compile(
    r"\s*\((?:EFSA guidance|Training|ChemMon|VMPR|"
    r"\d{4} maintenance|docs/[^)]+|BUSINESS-RULES[^)]*|"
    r"VALIDATION_RULES_SUMMARY[^)]*)[^)]*\)\s*$"
)
SOURCE_ONLY_LINE_RE = re.compile(
    r"^\s*\((?:EFSA guidance|Training|ChemMon|VMPR|\d{4} maintenance)[^)]*\)\s*$"
)

PROMPT_CONTEXT_PAGE_CATEGORIES = {"runtime", "guidance", "validation", "domain_overlay"}
PROMPT_CONTEXT_OMITTED_SECTIONS = {
    "appendix a2 codes",
    "authority",
    "how to use this page during ingest",
    "maintenance history",
    "orientation",
    "read these pages with",
    "related projects",
    "relevant business rules",
    "relevant policy",
    "release context",
    "source layer",
    "supporting pages by signal",
    "worked examples",
}


@dataclass(frozen=True)
class WikiPage:
    name: str
    title: str
    summary: str
    sources: list[str]
    related: list[str]
    content: str
    body: str


@dataclass(frozen=True)
class WikiEdge:
    source: str
    target: str
    edge_type: str
    section: str | None = None
    label: str | None = None


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
            "KNOWLEDGE_ARCHITECTURE.md": self.root / "KNOWLEDGE_ARCHITECTURE.md",
            "INGEST_WORKFLOW.md": self.root / "INGEST_WORKFLOW.md",
            "SCHEMA.md": self.root / "SCHEMA.md",
            "RUNTIME_RULES.md": self.root / "RUNTIME_RULES.md",
        }
        self.page_categories: dict[str, str] = {
            "README.md": "orientation",
            "PROJECT_CONTEXT.md": "orientation",
            "KNOWLEDGE_ARCHITECTURE.md": "orientation",
            "INGEST_WORKFLOW.md": "orientation",
            "SCHEMA.md": "orientation",
            "RUNTIME_RULES.md": "runtime",
            "index.md": "orientation",
            "log.md": "maintenance",
            "policy-contract.md": "runtime",
            "foodex2-overview.md": "guidance",
            "base-term-selection.md": "guidance",
            "facet-coding-rules.md": "guidance",
            "implicit-vs-explicit-facets.md": "guidance",
            "code-string-format.md": "guidance",
            "process-facets.md": "guidance",
            "ingredient-facets.md": "guidance",
            "packaging-facets.md": "guidance",
            "chemical-monitoring-foodex2.md": "domain_overlay",
            "pesticides-foodex2.md": "domain_overlay",
            "contaminants-foodex2.md": "domain_overlay",
            "vmpr-foodex2.md": "domain_overlay",
            "vmpr-legislative-mapping.md": "domain_overlay",
            "additives-flavourings-foodex2.md": "domain_overlay",
            "business-rules.md": "validation",
            "validation-rules.md": "validation",
            "structural-validation.md": "validation",
            "term-type-facet-constraints.md": "validation",
            "process-validation-rules.md": "validation",
            "domain-specific-validation.md": "domain_overlay",
            "maintenance-history.md": "maintenance",
            "maintenance-2015.md": "maintenance",
            "maintenance-2016-2018.md": "maintenance",
            "maintenance-2019.md": "maintenance",
            "maintenance-2020.md": "maintenance",
            "maintenance-2021.md": "maintenance",
            "maintenance-2022.md": "maintenance",
            "maintenance-2023.md": "maintenance",
            "maintenance-2024.md": "maintenance",
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
        summaries["KNOWLEDGE_ARCHITECTURE.md"] = (
            "Architecture stance for compiled markdown knowledge, graph retrieval, long-source ingest, and when not to add heavier RAG infrastructure."
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

    def resolve_page_reference(self, reference: str) -> str | None:
        raw = reference.strip()
        if not raw:
            return None
        if raw.startswith("[[") and raw.endswith("]]"):
            raw = raw[2:-2]
        raw = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if not raw:
            return None

        normalized = self.normalize_page_name(raw)
        if normalized in self.allowed_page_names():
            return normalized

        if not Path(raw).suffix:
            normalized_with_md = self.normalize_page_name(f"{raw}.md")
            if normalized_with_md in self.allowed_page_names():
                return normalized_with_md
        return None

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

    def _classify_body_edge_type(self, *, source: str, section: str | None) -> str:
        if section == "Relevant Policy":
            return "policy_reference"
        if section == "Relevant Business Rules":
            return "business_rule_reference"
        if source == "index.md":
            return "index_reference"
        return "inline_link"

    def _extract_body_edges(self, page: WikiPage) -> list[WikiEdge]:
        edges: list[WikiEdge] = []
        current_section: str | None = None

        for line in page.body.splitlines():
            heading_match = HEADING_RE.match(line.strip())
            if heading_match:
                current_section = heading_match.group(1).strip()

            for match in WIKILINK_RE.finditer(line):
                raw_target = match.group(1)
                label = raw_target.split("|", 1)[1].strip() if "|" in raw_target else None
                target = self.resolve_page_reference(raw_target)
                if target is None or target == page.name:
                    continue
                edges.append(
                    WikiEdge(
                        source=page.name,
                        target=target,
                        edge_type=self._classify_body_edge_type(
                            source=page.name,
                            section=current_section,
                        ),
                        section=current_section,
                        label=label,
                    )
                )

            for match in MARKDOWN_LINK_RE.finditer(line):
                label = match.group(1).strip() or None
                target = self.resolve_page_reference(match.group(2))
                if target is None or target == page.name:
                    continue
                edges.append(
                    WikiEdge(
                        source=page.name,
                        target=target,
                        edge_type=self._classify_body_edge_type(
                            source=page.name,
                            section=current_section,
                        ),
                        section=current_section,
                        label=label,
                    )
                )
        return edges

    def _extract_page_edges(self, page: WikiPage) -> list[WikiEdge]:
        edges: list[WikiEdge] = []
        for reference in page.related:
            target = self.resolve_page_reference(reference)
            if target is None or target == page.name:
                continue
            edges.append(
                WikiEdge(
                    source=page.name,
                    target=target,
                    edge_type="related",
                    section="frontmatter",
                )
            )
        edges.extend(self._extract_body_edges(page))

        deduped: list[WikiEdge] = []
        seen: set[tuple[str, str, str, str | None, str | None]] = set()
        for edge in edges:
            key = (edge.source, edge.target, edge.edge_type, edge.section, edge.label)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)
        return deduped

    @cached_property
    def _graph(self) -> dict[str, Any]:
        pages = {
            name: self.read_page(name)
            for name in sorted(self.allowed_page_names())
        }
        edges: list[WikiEdge] = []
        for page in pages.values():
            edges.extend(self._extract_page_edges(page))

        outgoing: dict[str, list[WikiEdge]] = {name: [] for name in pages}
        incoming: dict[str, list[WikiEdge]] = {name: [] for name in pages}
        for edge in edges:
            outgoing.setdefault(edge.source, []).append(edge)
            incoming.setdefault(edge.target, []).append(edge)

        nodes = []
        for name, page in sorted(pages.items()):
            nodes.append(
                {
                    "page_name": name,
                    "title": page.title,
                    "summary": page.summary,
                    "incoming_count": len(incoming.get(name, [])),
                    "outgoing_count": len(outgoing.get(name, [])),
                }
            )

        hubs = sorted(
            (
                {
                    "page_name": name,
                    "title": pages[name].title,
                    "incoming_count": len(incoming.get(name, [])),
                    "outgoing_count": len(outgoing.get(name, [])),
                    "total_links": len(incoming.get(name, [])) + len(outgoing.get(name, [])),
                }
                for name in pages
            ),
            key=lambda item: (-int(item["total_links"]), item["page_name"]),
        )[:10]

        orphans = sorted(
            name
            for name in pages
            if not incoming.get(name) and not outgoing.get(name)
        )

        return {
            "nodes": nodes,
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.edge_type,
                    "section": edge.section,
                    "label": edge.label,
                }
                for edge in sorted(
                    edges,
                    key=lambda item: (
                        item.source,
                        item.target,
                        item.edge_type,
                        item.section or "",
                        item.label or "",
                    ),
                )
            ],
            "outgoing": outgoing,
            "incoming": incoming,
            "summary": {
                "page_count": len(pages),
                "edge_count": len(edges),
                "orphan_pages": orphans,
                "hub_pages": hubs,
            },
        }

    def graph_data(self) -> dict[str, Any]:
        return {
            "nodes": list(self._graph["nodes"]),
            "edges": list(self._graph["edges"]),
            "summary": dict(self._graph["summary"]),
        }

    def page_category(self, page_name: str) -> str:
        normalized = self.normalize_page_name(page_name)
        if normalized in self.page_categories:
            return self.page_categories[normalized]
        if (self.guidance_dir / normalized).exists():
            return "guidance"
        return "unknown"

    def compact_graph_data(self) -> dict[str, Any]:
        graph = self._graph
        nodes = [
            {
                "id": node["page_name"],
                "label": node["title"],
                "category": self.page_category(node["page_name"]),
                "incoming_count": node["incoming_count"],
                "outgoing_count": node["outgoing_count"],
                "total_links": node["incoming_count"] + node["outgoing_count"],
            }
            for node in graph["nodes"]
        ]
        edges = [
            {
                "source": edge["source"],
                "target": edge["target"],
                "type": edge["type"],
            }
            for edge in graph["edges"]
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "summary": dict(graph["summary"]),
        }

    def page_backlinks(self, page_name: str) -> dict[str, Any]:
        page = self.read_page(page_name)
        incoming_edges = self._graph["incoming"].get(page.name, [])
        backlinks = [
            {
                "source": edge.source,
                "source_title": self.read_page(edge.source).title,
                "type": edge.edge_type,
                "section": edge.section,
                "label": edge.label,
            }
            for edge in sorted(
                incoming_edges,
                key=lambda item: (item.source, item.edge_type, item.section or "", item.label or ""),
            )
        ]
        return {
            "page_name": page.name,
            "title": page.title,
            "summary": page.summary,
            "backlinks": backlinks,
            "backlink_count": len(backlinks),
        }

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

    def prompt_content_for_context_pack(self, page: WikiPage) -> str | None:
        if self.page_category(page.name) not in PROMPT_CONTEXT_PAGE_CATEGORIES:
            return None

        cleaned = self.clean_content_for_model(page)
        cleaned = self._drop_prompt_page_scaffolding(cleaned)
        cleaned = self._drop_prompt_irrelevant_sections(cleaned)
        cleaned = self._render_links_as_text(cleaned)
        cleaned = self._collapse_blank_lines(cleaned.splitlines())
        return cleaned or None

    def _drop_prompt_page_scaffolding(self, content: str) -> str:
        lines = content.splitlines()
        first_h1_idx = next(
            (
                idx
                for idx, line in enumerate(lines)
                if line.startswith("# ") and line.lstrip() == line
            ),
            None,
        )
        if first_h1_idx is None:
            return content.strip()

        first_h2_after_h1 = next(
            (
                idx
                for idx in range(first_h1_idx + 1, len(lines))
                if lines[idx].startswith("## ") and lines[idx].lstrip() == lines[idx]
            ),
            None,
        )
        if first_h2_after_h1 is not None:
            return "\n".join(lines[first_h2_after_h1:]).strip()

        return "\n".join(
            line for idx, line in enumerate(lines) if idx != first_h1_idx
        ).strip()

    def _drop_prompt_irrelevant_sections(self, content: str) -> str:
        kept: list[str] = []
        skip_until_level: int | None = None

        for line in content.splitlines():
            heading_match = MARKDOWN_HEADING_RE.match(line.strip())
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip().lower()
                if skip_until_level is not None and level > skip_until_level:
                    continue
                skip_until_level = None
                if title in PROMPT_CONTEXT_OMITTED_SECTIONS:
                    skip_until_level = level
                    continue
            elif skip_until_level is not None:
                continue

            kept.append(line)

        return "\n".join(kept).strip()

    def _render_links_as_text(self, content: str) -> str:
        def wikilink_label(match: re.Match[str]) -> str:
            target = match.group(1).strip()
            return target.split("|", 1)[1].strip() if "|" in target else target

        without_wikilinks = WIKILINK_RE.sub(wikilink_label, content)
        return MARKDOWN_LINK_RE.sub(lambda match: match.group(1).strip(), without_wikilinks)

    def _collapse_blank_lines(self, lines: list[str]) -> str:
        collapsed: list[str] = []
        blank_run = 0
        for line in lines:
            if line.strip():
                blank_run = 0
                collapsed.append(line.rstrip())
            else:
                blank_run += 1
                if blank_run <= 1:
                    collapsed.append("")
        return "\n".join(collapsed).strip()
