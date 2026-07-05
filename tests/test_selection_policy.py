from wiki_api.wiki_store import WikiStore


def test_selection_policy_page_is_served_as_orientation():
    store = WikiStore(".")
    assert "selection-policy.md" in store.allowed_page_names()
    assert store.page_category("selection-policy.md") == "orientation"
