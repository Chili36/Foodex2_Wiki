from wiki_api.selection_scoring import aggregate, miss_frequency, score_case

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


def test_duplicate_pages_do_not_skew_scores():
    pages = [
        "base-term-selection.md", "base-term-selection.md",
        "term-type-facet-constraints.md",
        "process-facets.md", "process-facets.md",
    ]
    s = score_case(LABELS, pages)
    assert s["precision"] == 2 / 3
    assert s["unlabeled"] == ["process-facets.md"]


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




def _row(case_id, missing):
    return {"id": case_id, "missing": missing}


def test_miss_frequency_counts_and_split():
    passes = [
        [_row("A", ["p1.md"]), _row("B", [])],
        [_row("A", ["p1.md"]), _row("B", ["p2.md"])],
        [_row("A", ["p1.md"]), _row("B", [])],
    ]
    result = miss_frequency(passes)
    assert result["counts"] == {"A": {"p1.md": 3}, "B": {"p2.md": 1}}
    assert result["systematic"] == [
        {"case_id": "A", "page": "p1.md", "missed": 3, "repeats": 3}
    ]
    assert result["stochastic"] == [
        {"case_id": "B", "page": "p2.md", "missed": 1, "repeats": 3}
    ]


def test_miss_frequency_threshold_is_ceil_two_thirds():
    # repeats=5 -> threshold ceil(10/3)=4
    passes = [
        [_row("A", ["p.md"])],
        [_row("A", ["p.md"])],
        [_row("A", ["p.md"])],
        [_row("A", [])],
        [_row("A", [])],
    ]
    assert miss_frequency(passes)["stochastic"][0]["missed"] == 3
    passes[3] = [_row("A", ["p.md"])]
    assert miss_frequency(passes)["systematic"][0]["missed"] == 4


def test_miss_frequency_empty():
    assert miss_frequency([]) == {"counts": {}, "systematic": [], "stochastic": []}
