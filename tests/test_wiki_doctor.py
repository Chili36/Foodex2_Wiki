from __future__ import annotations

import re
import shutil
from pathlib import Path

from wiki_api.doctor import run_doctor
from wiki_api.wiki_store import WikiStore


REPO_ROOT = Path(__file__).resolve().parent.parent

# The subset of the real wiki root that WikiStore actually reads. Copying just
# this (rather than the whole repo, which includes .venv/foodex2_docs PDFs
# etc.) keeps the corruption tests fast while still exercising a real wiki.
_WIKI_ROOT_DOCS = (
    "README.md",
    "PROJECT_CONTEXT.md",
    "KNOWLEDGE_ARCHITECTURE.md",
    "WIKI_ARCHITECTURE_FOR_MODELS.md",
    "INGEST_WORKFLOW.md",
    "MAINTENANCE_WORKFLOW.md",
    "SCHEMA.md",
    "RUNTIME_RULES.md",
    "index.md",
    "log.md",
)


def _copy_wiki_root(tmp_path: Path) -> Path:
    """Copy the real wiki's pages into tmp_path so a test can corrupt one page
    in isolation without mutating the repo."""
    for name in _WIKI_ROOT_DOCS:
        shutil.copy2(REPO_ROOT / name, tmp_path / name)
    shutil.copytree(
        REPO_ROOT / "raw" / "efsa-guidance",
        tmp_path / "raw" / "efsa-guidance",
    )
    return tmp_path


def test_wiki_doctor_passes_with_no_errors() -> None:
    report = run_doctor(REPO_ROOT)

    assert report.errors == []


def test_maintenance_workflow_is_registered_as_orientation() -> None:
    store = WikiStore(REPO_ROOT)
    page = store.read_page("MAINTENANCE_WORKFLOW.md")

    assert store.page_category(page.name) == "orientation"
    assert page.summary.startswith("Deterministic and LLM-assisted maintenance workflow")


def test_doctor_flags_corrupted_selection_policy(tmp_path):
    root = _copy_wiki_root(tmp_path)
    policy_path = root / "raw" / "efsa-guidance" / "selection-policy.md"
    policy_path.write_text(
        "---\ntitle: \"Selection Skeleton Policy\"\nlast_updated: \"2026-07-05\"\n"
        "source_tier: \"local_policy\"\n---\n\n# Selection Skeleton Policy\n\nNo block.\n"
    )
    report = run_doctor(root)
    checks = {issue.check for issue in report.errors}
    assert "selection_policy" in checks


def test_doctor_passes_selection_policy_on_real_wiki():
    report = run_doctor(".")
    assert "selection_policy" not in {issue.check for issue in report.errors}


def test_doctor_flags_missing_select_when(tmp_path):
    root = _copy_wiki_root(tmp_path)
    page_path = root / "raw" / "efsa-guidance" / "base-term-selection.md"
    original = page_path.read_text(encoding="utf-8")
    stripped = re.sub(
        r"\nselect_when: >-\n(?:  .*\n)+",
        "\n",
        original,
        count=1,
    )
    assert stripped != original, "select_when frontmatter block was not found/stripped"
    page_path.write_text(stripped, encoding="utf-8")

    report = run_doctor(root)
    matching = [
        issue
        for issue in report.errors
        if issue.check == "selection_metadata" and issue.location == "base-term-selection.md"
    ]
    assert matching, report.errors


def test_doctor_passes_selection_metadata_on_real_wiki():
    report = run_doctor(".")
    assert "selection_metadata" not in {issue.check for issue in report.errors}


def test_doctor_flags_missing_selector_guidance(tmp_path):
    root = _copy_wiki_root(tmp_path)
    policy_path = root / "raw" / "efsa-guidance" / "selection-policy.md"
    policy_path.write_text(
        "---\ntitle: \"Selection Skeleton Policy\"\nlast_updated: \"2026-07-05\"\n"
        "source_tier: \"local_policy\"\n---\n\n# Selection Skeleton Policy\n\n"
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
    report = run_doctor(root)
    checks = {issue.check for issue in report.errors}
    assert "selection_policy" in checks
