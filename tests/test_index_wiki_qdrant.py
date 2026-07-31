from __future__ import annotations

from scripts import index_wiki_qdrant


def test_create_collection_reuses_existing_collection(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_http_json(*, method, url, **kwargs):
        calls.append((method, url))
        return {"result": {"status": "green"}}

    monkeypatch.setattr(index_wiki_qdrant, "_http_json", fake_http_json)

    index_wiki_qdrant._create_collection(
        qdrant_url="http://qdrant.test",
        collection="wiki",
        dimension=1024,
        recreate=False,
    )

    assert calls == [("GET", "http://qdrant.test/collections/wiki")]


def test_create_collection_creates_collection_when_missing(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_http_json(*, method, url, **kwargs):
        calls.append((method, url))
        if method == "GET":
            raise RuntimeError(f"GET {url} failed with 404: not found")
        return {"result": True}

    monkeypatch.setattr(index_wiki_qdrant, "_http_json", fake_http_json)

    index_wiki_qdrant._create_collection(
        qdrant_url="http://qdrant.test",
        collection="wiki",
        dimension=1024,
        recreate=False,
    )

    assert calls == [
        ("GET", "http://qdrant.test/collections/wiki"),
        ("PUT", "http://qdrant.test/collections/wiki"),
    ]
