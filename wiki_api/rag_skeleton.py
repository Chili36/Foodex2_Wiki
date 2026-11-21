"""Apply the selection-policy skeleton to `/wiki/ask-rag` retrieval results.

Chunk retrieval has no page selector, so nothing guarantees that the core
construction pages reach the answerer, and nothing applies the selector's
domain-overlay rule. This module applies the invariants that
`selection-policy.md` already declares:

- every required role's default page (base term, facet, validation) is
  present. Unlike `/wiki/context-pack`, another role member does not count:
  without a selector, a nearest-chunk hit on e.g. `code-string-format.md` is
  not evidence that facet guidance is covered;
- `RUNTIME_RULES.md` is always in front, as in `/wiki/context-pack`;
- when the question names its reporting domain, overlays owned by other
  domains are dropped (`domain_overlays`).

`drop_pages` is deliberately not applied here: maintenance pages are
legitimate ask-rag evidence for ontology-change questions.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .selection_policy import SelectionPolicy, enforce_skeleton
from .wiki_store import WikiStore

RUNTIME_RULES_PAGE_NAME = "RUNTIME_RULES.md"
_REPORTING_DOMAIN_RE = re.compile(
    r"reporting\s+domain\s*:\s*([A-Za-z][A-Za-z0-9 _-]*?)\s*(?:[.;,\n]|$)",
    re.IGNORECASE,
)


def detect_reporting_domain(question: str) -> str | None:
    match = _REPORTING_DOMAIN_RE.search(question)
    if not match:
        return None
    domain = match.group(1).strip().lower()
    return domain or None


def _backfill_item(store: WikiStore, page_name: str) -> dict[str, Any]:
    page = store.read_page(page_name)
    category = store.page_category(page.name)
    body = store.prompt_content_for_context_pack(page) or store.clean_content_for_model(page)
    header = [f"Page: {page.title}", f"File: {page.name}"]
    if category:
        header.append(f"Category: {category}")
    if page.source_tier:
        header.append(f"Source tier: {page.source_tier}")
    if page.summary:
        header.append(f"Summary: {page.summary}")
    content = "\n".join(header) + (f"\n\n{body}" if body else "")
    return {
        "answerer_page": {"page_name": page.name, "content": content},
        "page_summary": {
            "page_name": page.name,
            "title": page.title,
            "summary": page.summary,
            "category": category,
            "source_tier": page.source_tier,
            "sources": page.sources,
            "related": page.related,
            "content": content,
        },
    }


def apply_rag_skeleton(
    *,
    question: str,
    context: dict[str, Any],
    limit: int,
    store: WikiStore,
    policy: SelectionPolicy,
    reporting_domain: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the context with the skeleton applied, plus a trace block.

    ``limit`` stays a cap on distinct non-runtime pages: required roles win
    over the lowest-ranked optional pages when backfilling needs room.
    """
    items = [
        {"answerer_page": answerer_page, "page_summary": page_summary}
        for answerer_page, page_summary in zip(
            context["answerer_pages"], context["page_summaries"]
        )
    ]

    domain_source = "request" if reporting_domain else None
    domain = (reporting_domain or "").strip().lower() or None
    if domain is None:
        domain = detect_reporting_domain(question)
        domain_source = "question" if domain else None
    own_overlays = policy.overlays_for(domain) if domain else None
    dropped_overlays: list[str] = []
    if own_overlays is not None:
        foreign = policy.all_domain_overlay_pages() - set(own_overlays)
        dropped_overlays = list(
            dict.fromkeys(
                item["answerer_page"]["page_name"]
                for item in items
                if item["answerer_page"]["page_name"] in foreign
            )
        )
        items = [
            item for item in items if item["answerer_page"]["page_name"] not in foreign
        ]

    retrieved_pages = list(
        dict.fromkeys(item["answerer_page"]["page_name"] for item in items)
    )
    skeleton_policy = replace(
        policy,
        drop_pages=(),
        required_roles=tuple(
            replace(role, members=(role.default,)) for role in policy.required_roles
        ),
    )
    skeleton_input = [page for page in retrieved_pages if page != RUNTIME_RULES_PAGE_NAME]
    skeleton = enforce_skeleton(
        skeleton_input,
        skeleton_policy,
        max_pages=max(limit, len(policy.required_roles)),
    )
    trimmed = set(skeleton.trimmed)
    items = [item for item in items if item["answerer_page"]["page_name"] not in trimmed]

    # Pinned pages are always hydrated from the store: a retrieved chunk of a
    # required page is one section, not coverage of the page.
    pinned = {RUNTIME_RULES_PAGE_NAME, *(role.default for role in policy.required_roles)}
    hydrated_retrieved: list[str] = []
    rebuilt: list[dict[str, Any]] = []
    for item in items:
        page_name = item["answerer_page"]["page_name"]
        if page_name not in pinned:
            rebuilt.append(item)
        elif page_name not in hydrated_retrieved:
            hydrated_retrieved.append(page_name)
            rebuilt.append(_backfill_item(store, page_name))
    items = rebuilt
    items.extend(_backfill_item(store, entry["page"]) for entry in skeleton.backfilled)

    runtime_added = RUNTIME_RULES_PAGE_NAME not in retrieved_pages
    runtime_items = [
        item for item in items if item["answerer_page"]["page_name"] == RUNTIME_RULES_PAGE_NAME
    ] or [_backfill_item(store, RUNTIME_RULES_PAGE_NAME)]
    items = runtime_items + [
        item for item in items if item["answerer_page"]["page_name"] != RUNTIME_RULES_PAGE_NAME
    ]

    added_pages = [entry["page"] for entry in skeleton.backfilled]
    if runtime_added:
        added_pages.insert(0, RUNTIME_RULES_PAGE_NAME)
    # Characters of store-hydrated pinned pages sent to the answerer.
    added_chars = sum(
        len(item["answerer_page"]["content"])
        for item in items
        if item["answerer_page"]["page_name"] in pinned
    )
    updated = {
        **context,
        "answerer_pages": [item["answerer_page"] for item in items],
        "page_summaries": [item["page_summary"] for item in items],
        "pages_used": list(
            dict.fromkeys(item["answerer_page"]["page_name"] for item in items)
        ),
    }
    trace = {
        "skeleton_version": policy.skeleton_version,
        "reporting_domain": domain,
        "reporting_domain_source": domain_source,
        "reporting_domain_known": own_overlays is not None,
        "dropped_domain_overlays": dropped_overlays,
        "backfilled": skeleton.backfilled,
        "trimmed": skeleton.trimmed,
        "runtime_rules_added": runtime_added,
        "added_pages": added_pages,
        "hydrated_retrieved_pages": hydrated_retrieved,
        "added_chars": added_chars,
        "retrieval_covered_roles": skeleton.selector_covered_roles,
    }
    return updated, trace
