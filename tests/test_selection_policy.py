import pytest

from wiki_api.selection_policy import (
    RequiredRole,
    SelectionPolicy,
    enforce_skeleton,
    load_selection_policy,
    load_selector_guidance,
)
from wiki_api.wiki_store import WikiStore


def test_selection_policy_page_is_served_as_orientation():
    store = WikiStore(".")
    assert "selection-policy.md" in store.allowed_page_names()
    assert store.page_category("selection-policy.md") == "orientation"


POLICY = SelectionPolicy(
    skeleton_version=1,
    required_roles=(
        RequiredRole(name="base_term", members=("base-term-selection.md",), default="base-term-selection.md"),
        RequiredRole(
            name="facet",
            members=("facet-coding-rules.md", "ingredient-facets.md"),
            default="facet-coding-rules.md",
        ),
        RequiredRole(
            name="validation",
            members=("term-type-facet-constraints.md", "process-validation-rules.md"),
            default="term-type-facet-constraints.md",
        ),
    ),
    drop_pages=("maintenance-*", "README.md"),
)


def test_covered_roles_are_not_backfilled():
    pages = ["index.md", "base-term-selection.md", "ingredient-facets.md", "process-validation-rules.md"]
    result = enforce_skeleton(pages, POLICY)
    assert result.final_pages == pages
    assert result.backfilled == []
    assert result.dropped == []
    assert result.selector_covered_roles == ["base_term", "facet", "validation"]


def test_missing_roles_backfilled_in_role_order():
    result = enforce_skeleton(["index.md", "base-term-selection.md"], POLICY)
    assert result.final_pages == [
        "index.md",
        "base-term-selection.md",
        "facet-coding-rules.md",
        "term-type-facet-constraints.md",
    ]
    assert result.backfilled == [
        {"role": "facet", "page": "facet-coding-rules.md"},
        {"role": "validation", "page": "term-type-facet-constraints.md"},
    ]
    assert result.selector_covered_roles == ["base_term"]


def test_drop_list_literal_and_glob():
    result = enforce_skeleton(
        ["index.md", "base-term-selection.md", "maintenance-2024.md", "README.md",
         "ingredient-facets.md", "term-type-facet-constraints.md"],
        POLICY,
    )
    assert result.dropped == ["maintenance-2024.md", "README.md"]
    assert "maintenance-2024.md" not in result.final_pages
    assert "README.md" not in result.final_pages
    assert result.backfilled == []


def test_drop_then_backfill_when_leak_was_only_coverage():
    result = enforce_skeleton(["index.md", "maintenance-2024.md"], POLICY)
    assert result.dropped == ["maintenance-2024.md"]
    assert [item["role"] for item in result.backfilled] == ["base_term", "facet", "validation"]
    assert result.final_pages == [
        "index.md",
        "base-term-selection.md",
        "facet-coding-rules.md",
        "term-type-facet-constraints.md",
    ]


def test_load_selection_policy_from_wiki():
    store = WikiStore(".")
    policy = load_selection_policy(store)
    assert policy.skeleton_version == 1
    role_names = [role.name for role in policy.required_roles]
    assert role_names == ["base_term", "facet", "validation"]
    for role in policy.required_roles:
        assert role.default in role.members
    assert "maintenance-*" in policy.drop_pages
    assert "selection-policy.md" in policy.drop_pages


def test_load_selection_policy_rejects_missing_block(tmp_path):
    root = tmp_path
    (root / "raw" / "efsa-guidance").mkdir(parents=True)
    for name in ("README.md", "PROJECT_CONTEXT.md", "KNOWLEDGE_ARCHITECTURE.md", "SCHEMA.md",
                 "INGEST_WORKFLOW.md", "MAINTENANCE_WORKFLOW.md", "RUNTIME_RULES.md",
                 "index.md", "log.md"):
        (root / name).write_text("---\ntitle: x\n---\n# x\n")
    (root / "raw" / "efsa-guidance" / "selection-policy.md").write_text(
        "---\ntitle: x\n---\n# No policy block here\n"
    )
    store = WikiStore(root)
    with pytest.raises(ValueError, match="policy block"):
        load_selection_policy(store)


def test_load_selection_policy_raises_value_error_when_page_missing(tmp_path):
    # Same minimal scaffold as test_load_selection_policy_rejects_missing_block,
    # but selection-policy.md is never created on disk. The guarantee under
    # test is that load_selection_policy raises ValueError (so the
    # context-pack endpoint's `except ValueError` catches it and returns
    # 503), not any particular underlying exception type — WikiStore may
    # raise FileNotFoundError from its registration/allowed-names path for
    # an unregistered page rather than failing inside read_page itself.
    root = tmp_path
    (root / "raw" / "efsa-guidance").mkdir(parents=True)
    for name in ("README.md", "PROJECT_CONTEXT.md", "KNOWLEDGE_ARCHITECTURE.md", "SCHEMA.md",
                 "INGEST_WORKFLOW.md", "MAINTENANCE_WORKFLOW.md", "RUNTIME_RULES.md",
                 "index.md", "log.md"):
        (root / name).write_text("---\ntitle: x\n---\n# x\n")
    store = WikiStore(root)
    with pytest.raises(ValueError, match="could not be read"):
        load_selection_policy(store)


def test_load_selector_guidance_from_wiki():
    store = WikiStore(".")
    guidance = load_selector_guidance(store)
    assert "Reading The Candidate List" in guidance
    assert "Completeness Rubric" in guidance
    assert "```" not in guidance  # prose only, no fenced blocks


def test_load_selector_guidance_missing_section_raises(tmp_path):
    # Reuse the minimal temp-root scaffolding from
    # test_load_selection_policy_rejects_missing_block, but write a
    # selection-policy.md WITH a valid yaml block and WITHOUT a
    # "## Selector Guidance" section.
    root = tmp_path
    (root / "raw" / "efsa-guidance").mkdir(parents=True)
    for name in ("README.md", "PROJECT_CONTEXT.md", "KNOWLEDGE_ARCHITECTURE.md", "SCHEMA.md",
                 "INGEST_WORKFLOW.md", "MAINTENANCE_WORKFLOW.md", "RUNTIME_RULES.md",
                 "index.md", "log.md"):
        (root / name).write_text("---\ntitle: x\n---\n# x\n")
    (root / "raw" / "efsa-guidance" / "selection-policy.md").write_text(
        "---\ntitle: x\n---\n"
        "# Selection Skeleton Policy\n\n"
        "## Policy Block\n\n"
        "```yaml\n"
        "skeleton_version: 1\n"
        "required_roles:\n"
        "  base_term:\n"
        "    members:\n"
        "      - base-term-selection.md\n"
        "    default: base-term-selection.md\n"
        "drop_pages:\n"
        "  - \"maintenance-*\"\n"
        "```\n"
    )
    store = WikiStore(root)
    with pytest.raises(ValueError, match="Selector Guidance"):
        load_selector_guidance(store)
