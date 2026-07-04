from wiki_api.selection_scoring import aggregate, score_case

LABELS = {
    "must_have": ["base-term-selection.md", "term-type-facet-constraints.md"],
    "acceptable": ["facet-coding-rules.md"],
    "must_not": ["maintenance-*", "vmpr-foodex2.md"],
}


def test_perfect_selection():
    pages = ["index.md", "RUNTIME_RULES.md", "base-term-selection.md",
             "term-type-facet-constraints.md", "facet-coding-rules.md"]
    s = score_case(LABELS, pages)
    assert s["must_have_recall"] == 1.0
    assert s["precision"] == 1.0
    assert s["missing"] == [] and s["leaks"] == [] and s["unlabeled"] == []


def test_missing_must_have_and_glob_leak():
    pages = ["index.md", "base-term-selection.md", "maintenance-2024.md"]
    s = score_case(LABELS, pages)
    assert s["must_have_recall"] == 0.5
    assert s["missing"] == ["term-type-facet-constraints.md"]
    assert s["leaks"] == ["maintenance-2024.md"]


def test_unlabeled_page_reported_not_leaked():
    pages = ["base-term-selection.md", "term-type-facet-constraints.md", "process-facets.md"]
    s = score_case(LABELS, pages)
    assert s["unlabeled"] == ["process-facets.md"]
    assert s["leaks"] == []
    assert s["precision"] == 2 / 3


def test_aggregate():
    scores = [
        {"must_have_recall": 1.0, "precision": 1.0, "leaks": []},
        {"must_have_recall": 0.5, "precision": 0.75, "leaks": ["maintenance-2024.md"]},
    ]
    agg = aggregate(scores)
    assert agg["mean_must_have_recall"] == 0.75
    assert agg["mean_precision"] == 0.875
    assert agg["leak_free_rate"] == 0.5
    assert agg["case_count"] == 2
