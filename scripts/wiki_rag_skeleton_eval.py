"""Page-level before/after for the ask-rag skeleton across all wiki-rag eval cases (embedding calls only)."""
import json, sys
from fnmatch import fnmatch
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from dotenv import load_dotenv; load_dotenv(root / ".env")
from wiki_api.qdrant_ask import retrieve_qdrant_ask_context
from wiki_api.rag_skeleton import apply_rag_skeleton
from wiki_api.selection_policy import load_selection_policy
from wiki_api.wiki_store import WikiStore
store = WikiStore(root); policy = load_selection_policy(store)
files = ["dmt_end_to_end_cases.json", "ontology_exception_cases.json", "physical-division-cases.json"]
rows = []
for f in files:
    for c in json.loads((root / "evals/wiki-rag" / f).read_text())["cases"]:
        if not c.get("reviewed") or not c.get("reference_pages"):
            continue
        q = c.get("request_question") or c["question"]
        for strat in ("legacy_topk", "diverse_pages"):
            ctx = retrieve_qdrant_ask_context(question=q, retrieval_mode="wiki", limit=7, retrieval_strategy=strat)
            after, tr = apply_rag_skeleton(question=q, context=ctx, limit=7, store=store, policy=policy)
            def m(pages):
                ref = c["reference_pages"]
                rec = sum(p in pages for p in ref) / len(ref)
                leaks = [p for p in pages if any(fnmatch(p, pat) for pat in c.get("must_not_pages", []))]
                return rec, leaks
            rb, lb = m(ctx["pages_used"]); ra, la = m(after["pages_used"])
            rows.append(dict(case=c["id"], strat=strat, recall_before=rb, recall_after=ra, leaks_before=lb, leaks_after=la, added_chars=tr["added_chars"]))
for r in rows:
    print(f'{r["case"]:<22}{r["strat"]:<14}recall {r["recall_before"]:.2f}->{r["recall_after"]:.2f}  leaks {len(r["leaks_before"])}->{len(r["leaks_after"])} {r["leaks_after"]}  +{r["added_chars"]}ch')
for s in ("legacy_topk", "diverse_pages"):
    rs = [r for r in rows if r["strat"] == s]
    n = len(rs)
    print(s, "n", n, "mean recall %.3f -> %.3f" % (sum(r["recall_before"] for r in rs)/n, sum(r["recall_after"] for r in rs)/n),
          "leak-free %.2f -> %.2f" % (sum(not r["leaks_before"] for r in rs)/n, sum(not r["leaks_after"] for r in rs)/n),
          "mean added chars %d" % (sum(r["added_chars"] for r in rs)/n))
