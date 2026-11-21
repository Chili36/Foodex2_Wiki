"""Protect the evidence boundary between full pages and runtime projections.

These checks establish that the decision rule reaches consumers. Live answers
must also be reviewed against the source-backed evaluation cases.
"""
from pathlib import Path

import pytest

from scripts.index_wiki_qdrant import _chunk_page
from scripts.wiki_ragas_eval import load_cases
from wiki_api.wiki_store import WikiStore


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("surface", ["full", "context", "rag"])
def test_physical_division_rule_survives_each_evidence_surface(surface):
    store = WikiStore(ROOT)
    page = store.read_page("process-facets.md")
    if surface == "full":
        evidence = [store.clean_content_for_model(page)]
    elif surface == "context":
        evidence = [store.prompt_content_for_context_pack(page)]
        assert "## Appendix A2 Codes" not in evidence[0]
        assert "## Worked Examples" not in evidence[0]
    else:
        evidence = [chunk["chunk_text"] for chunk in _chunk_page(
            store=store, page=page, max_chars=2800
        )]

    # The usable rule and its derivative exception must travel together, not
    # just leave a process code somewhere in a stripped reference appendix.
    assert any(all(part in block for part in (
        "does not automatically require a derivative base",
        "F28.A07LA",
        "grain milling associated with separation",
        "suitable generic derivative",
    )) for block in evidence)


def test_br13_repair_boundary_is_available_without_worked_examples():
    store = WikiStore(ROOT)
    projected = store.prompt_content_for_context_pack(
        store.read_page("term-type-facet-constraints.md")
    )
    assert "## Worked Examples" not in projected
    assert "does not determine the correct base-term class" in projected
    assert "Do not infer grinding solely" in projected
    assert "F28.A07LA" in projected


def test_physical_division_eval_has_reviewable_semantic_expectations():
    cases = load_cases(
        ROOT / "evals/wiki-rag/physical-division-cases.json", only_reviewed=True
    )
    assert {case["id"] for case in cases} == {
        f"DIV-{number:03d}" for number in range(1, 9)
    }
    for case in cases:
        assert case["source"]
        assert case["reference_answer"]
        assert case["rubric"]["score5_description"]
