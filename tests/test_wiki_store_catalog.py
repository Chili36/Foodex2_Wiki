from wiki_api.wiki_store import WikiStore


def test_read_page_parses_select_when(tmp_path):
    store = _make_store(tmp_path)
    page = store.read_page("annotated.md")
    assert page.select_when == "The case involves choosing between raw and derivative bases."


def test_read_page_select_when_absent_is_none(tmp_path):
    store = _make_store(tmp_path)
    assert store.read_page("plain.md").select_when is None


def test_selector_catalog_prefers_select_when_and_falls_back_to_summary(tmp_path):
    store = _make_store(tmp_path)
    catalog = store.selector_catalog()
    assert "- annotated.md — The case involves choosing between raw and derivative bases." in catalog
    assert "- plain.md — Summary line for plain page." in catalog


def test_selector_catalog_excludes_non_prompt_facing_pages(tmp_path):
    store = _make_store(tmp_path)
    catalog = store.selector_catalog()
    assert "README.md" not in catalog
    assert "maintenance-2024.md" not in catalog


def test_selector_catalog_falls_back_to_title_when_no_hint_or_summary(tmp_path):
    store = _make_store(tmp_path)
    catalog = store.selector_catalog()
    assert "- unsummarized.md — Unsummarized" in catalog


def test_read_page_non_string_select_when_is_none(tmp_path):
    store = _make_store(tmp_path)
    assert store.read_page("bad-select-when.md").select_when is None


def _make_store(tmp_path):
    root = tmp_path
    guidance = root / "raw" / "efsa-guidance"
    guidance.mkdir(parents=True)
    for name in ("README.md", "PROJECT_CONTEXT.md", "KNOWLEDGE_ARCHITECTURE.md",
                 "WIKI_ARCHITECTURE_FOR_MODELS.md", "INGEST_WORKFLOW.md",
                 "MAINTENANCE_WORKFLOW.md", "SCHEMA.md", "RUNTIME_RULES.md", "log.md"):
        (root / name).write_text("---\ntitle: x\n---\n# x\n")
    (guidance / "annotated.md").write_text(
        "---\ntitle: Annotated\nselect_when: >-\n  The case involves choosing between "
        "raw and derivative bases.\n---\n# Annotated\n"
    )
    (guidance / "plain.md").write_text("---\ntitle: Plain\n---\n# Plain\n")
    (guidance / "maintenance-2024.md").write_text("---\ntitle: M24\n---\n# M24\n")
    (guidance / "unsummarized.md").write_text(
        "---\ntitle: Unsummarized\n---\n# Unsummarized\n"
    )
    (guidance / "bad-select-when.md").write_text(
        "---\ntitle: Bad Select When\nselect_when: 42\n---\n# Bad Select When\n"
    )
    (root / "index.md").write_text(
        "---\ntitle: Index\n---\n# Index\n\n## Guidance\n\n"
        "- [annotated.md](raw/efsa-guidance/annotated.md): Summary for annotated page.\n"
        "- [plain.md](raw/efsa-guidance/plain.md): Summary line for plain page.\n"
        "- [maintenance-2024.md](raw/efsa-guidance/maintenance-2024.md): M24 summary.\n"
        "- [bad-select-when.md](raw/efsa-guidance/bad-select-when.md): Bad select_when summary.\n"
    )
    return WikiStore(root)
