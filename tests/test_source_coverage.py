from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from wiki_api.doctor import (
    DoctorIssue,
    DoctorReport,
    _render_github,
    _render_text,
    main,
)
from wiki_api.source_coverage import (
    audit_source_coverage,
    fingerprint,
    prepare_review,
    wiki_snapshot,
)
from wiki_api.wiki_store import WikiPage, WikiStore


class Store:
    def __init__(self, root):
        self.root = root
        self.root_docs = WikiStore(root).root_docs
        self.guidance_dir = root / "raw" / "efsa-guidance"
        self.page = WikiPage(
            "topic.md",
            "Topic",
            "",
            None,
            [],
            [],
            "# Topic\nExisting text.",
            "# Topic\nExisting text.",
        )

    def catalog(self):
        return [self.page]

    def read_page(self, name):
        return self.page

    def page_category(self, name):
        return "guidance"


@pytest.fixture
def corpus(tmp_path):
    source = tmp_path / "foodex2_docs" / "manual.md"
    source.parent.mkdir()
    source.write_text("Specific source rule missing from the wiki.")
    (source.parent / ".DS_Store").write_bytes(b"ignored")
    store = Store(tmp_path)
    data = {
        "version": 2,
        "reviewed_at": "2026-01-01",
        "reviewed_by": "Test reviewer",
        "scope": "Section 2 only.",
        "limitations": "Not exhaustive.",
        "report": "reports/audit.md",
        "source_snapshot": {"foodex2_docs/manual.md": fingerprint(source.read_bytes())},
        "wiki_snapshot": wiki_snapshot(store),
        "source_roles": {"foodex2_docs/manual.md": "Primary reference"},
        "findings": [
            {
                "id": "COV-001",
                "status": "open",
                "source": "foodex2_docs/manual.md",
                "title": "Specific omission",
                "locator": "Section 2, p. 3",
                "source_excerpt": "Specific source rule",
                "wiki_pages": ["topic.md"],
                "observation": "The wiki omits a specific exception.",
                "action": "Add the exception.",
            }
        ],
    }
    return store, source, data


def save(store, data):
    path = store.root / "docs" / "source-coverage.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data))


def test_no_review_or_citation_does_not_generate_warnings(corpus):
    store, _, _ = corpus
    report = audit_source_coverage(store)
    assert report["source_count"] == 1
    assert report["audit_status"] == "not_run"
    assert report["findings"] == []
    assert "not been semantically audited" in report["information"]
    store.page = replace(store.page, sources=["manual.md"])
    assert (
        audit_source_coverage(store)["findings"] == []
    )  # One-page citation is not a gap.


def test_only_specific_audited_gaps_are_warnings(corpus):
    store, _, data = corpus
    save(store, data)
    report = audit_source_coverage(store)
    assert report["audit_status"] == "current"
    assert report["open_finding_count"] == 1
    assert len(report["findings"]) == 1
    warning = report["findings"][0]
    assert warning["location"] == "raw/efsa-guidance/topic.md"
    assert all(
        t in warning["message"]
        for t in ["COV-001", "Section 2, p. 3", "Add the exception"]
    )


def test_root_page_finding_points_to_the_actual_file(corpus):
    store, _, data = corpus
    store.page = replace(store.page, name="RUNTIME_RULES.md")
    store.root_docs[store.page.name].write_text(store.page.content)
    data["wiki_snapshot"] = wiki_snapshot(store)
    data["findings"][0]["wiki_pages"] = [store.page.name]
    save(store, data)

    report = audit_source_coverage(store)
    assert report["audit_status"] == "current"
    warning = report["findings"][0]
    assert warning["location"] == "RUNTIME_RULES.md"
    assert (store.root / warning["location"]).is_file()
    rendered = _render_github(DoctorReport([DoctorIssue(**warning)], report))
    assert "file=RUNTIME_RULES.md" in rendered


@pytest.mark.parametrize("change", ["source", "wiki", "removed_source", "added_page"])
def test_changes_suppress_old_gap_claims_and_emit_one_stale_notice(corpus, change):
    store, source, data = corpus
    save(store, data)
    if change == "source":
        source.write_text("New source edition")
    elif change == "wiki":
        store.page = replace(store.page, content="The gap may now be fixed.")
    elif change == "removed_source":
        source.unlink()
    else:
        old_page = store.page
        store.catalog = lambda: [old_page, replace(old_page, name="new-topic.md")]
    report = audit_source_coverage(store)
    assert report["audit_status"] == "stale"
    assert len(report["findings"]) == 1
    assert report["findings"][0]["check"] == "source_coverage_audit"
    assert "stale" in report["findings"][0]["message"]
    assert report["recorded_findings"][0]["id"] == "COV-001"


def test_resolved_finding_does_not_warn(corpus):
    store, _, data = corpus
    data["findings"][0].update(
        status="resolved", resolution="Reviewed the added exception."
    )
    save(store, data)
    report = audit_source_coverage(store)
    assert report["audit_status"] == "current"
    assert report["open_finding_count"] == 0
    assert report["findings"] == []


def test_historical_training_does_not_require_ingestion(corpus):
    store, source, data = corpus
    training = source.with_name("training-2018.pdf")
    training.write_bytes(b"old slides")
    data["source_roles"]["foodex2_docs/training-2018.pdf"] = (
        "Historical supporting training"
    )
    data["findings"] = []
    save(store, data)
    report = audit_source_coverage(store)
    assert report["source_count"] == 2
    assert report["findings"] == []
    assert report["sources"][1]["role"] == "Historical supporting training"


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(version=1),
        lambda d: d.update(reviewed_at="bad"),
        lambda d: d["findings"].append(d["findings"][0].copy()),
        lambda d: d["findings"][0].update(source_excerpt=""),
        lambda d: d["findings"][0].update(wiki_pages=["unknown.md"]),
        lambda d: d["findings"][0].update(source="foodex2_docs/not-snapshotted.pdf"),
        lambda d: d["findings"][0].update(status="resolved"),
        lambda d: d.update(source_roles=[]),
    ],
)
def test_invalid_evidence_cannot_be_reported_as_a_gap(corpus, change):
    store, _, data = corpus
    change(data)
    save(store, data)
    report = audit_source_coverage(store)
    assert report["audit_status"] == "invalid"
    assert len(report["findings"]) == 1
    assert report["findings"][0]["check"] == "source_coverage_audit"


def test_malformed_json_does_not_crash(corpus):
    store, _, data = corpus
    save(store, data)
    (store.root / "docs/source-coverage.json").write_text("{")
    assert audit_source_coverage(store)["audit_status"] == "invalid"


def test_default_and_strict_exit_codes_follow_real_findings(
    corpus, monkeypatch, capsys
):
    store, _, data = corpus

    def report():
        coverage = audit_source_coverage(store)
        return DoctorReport(
            [DoctorIssue(**f) for f in coverage.pop("findings")], coverage
        )

    monkeypatch.setattr("wiki_api.doctor.run_doctor", lambda *a, **kw: report())
    assert main(["--strict-warnings"]) == 0  # No saved audit is information only.
    capsys.readouterr()
    save(store, data)
    assert main(["--format", "json"]) == 0
    assert (
        json.loads(capsys.readouterr().out)["source_coverage"]["open_finding_count"]
        == 1
    )
    assert main(["--strict-warnings"]) == 1
    assert "COV-001" in _render_text(report())
    assert "::warning title=source_coverage" in _render_github(report())


def test_prepare_is_explicit_and_does_not_invent_findings(
    corpus, tmp_path, monkeypatch
):
    store, source, _ = corpus
    monkeypatch.setattr("wiki_api.source_coverage.WikiStore", lambda root: store)
    source.with_name("slides.pdf").write_bytes(b"sparse pdf")
    monkeypatch.setattr(
        "wiki_api.source_coverage.subprocess.run",
        lambda *a, **kw: SimpleNamespace(stdout="Slide title\f\f"),
    )
    output = tmp_path / "review"
    prepare_review(tmp_path, output)
    inventory = json.loads((output / "inventory.json").read_text())
    pdf = next(s for s in inventory["sources"] if s["source"].endswith(".pdf"))
    assert pdf["pdf_pages"] == 2
    assert "Sparse text" in pdf["extraction_note"]
    assert (output / "wiki/topic.md").read_text() == store.page.content
    assert not (tmp_path / "docs/source-coverage.json").exists()
    with pytest.raises(FileExistsError):
        prepare_review(tmp_path, output)
    with pytest.raises(ValueError, match="outside"):
        prepare_review(tmp_path, source.parent / "review-output")


def test_checked_in_semantic_audit_is_valid_and_current():
    root = Path(__file__).resolve().parents[1]
    report = audit_source_coverage(WikiStore(root))
    assert report["audit_status"] == "current"
    assert report["recorded_findings"]
    assert (root / report["report"]).is_file()
    assert all(finding["check"] == "source_coverage" for finding in report["findings"])
