from __future__ import annotations

from pathlib import Path

from wiki_api.doctor import run_doctor
from wiki_api.wiki_store import WikiStore


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_wiki_doctor_passes_with_no_errors() -> None:
    report = run_doctor(REPO_ROOT)

    assert report.errors == []


def test_maintenance_workflow_is_registered_as_orientation() -> None:
    store = WikiStore(REPO_ROOT)
    page = store.read_page("MAINTENANCE_WORKFLOW.md")

    assert store.page_category(page.name) == "orientation"
    assert page.summary.startswith("Deterministic and LLM-assisted maintenance workflow")
